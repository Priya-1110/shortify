from fastapi import FastAPI, Depends, Request, Response, HTTPException
from fastapi.responses import RedirectResponse, PlainTextResponse
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text, select

from .config import settings
from .db import engine, get_db
from .models import Base, Link
from .routers import links as links_router

from prometheus_client import Counter, Histogram, REGISTRY, generate_latest, CONTENT_TYPE_LATEST

REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("http_request_latency_seconds", "Latency of HTTP requests", ["method", "path"])

def instrument(app: FastAPI):
    @app.middleware("http")
    async def _metrics_mw(request: Request, call_next):
        path, method = request.url.path, request.method
        with REQUEST_LATENCY.labels(method, path).time():
            try:
                resp: Response = await call_next(request)
                REQUEST_COUNT.labels(method, path, str(resp.status_code)).inc()
                return resp
            except HTTPException as e:
                REQUEST_COUNT.labels(method, path, str(e.status_code)).inc()
                raise
            except Exception:
                REQUEST_COUNT.labels(method, path, "500").inc()
                raise

app = FastAPI(title=settings.APP_NAME)
instrument(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# Create tables (simple dev path; use Alembic later)
Base.metadata.create_all(bind=engine)

# Root → docs
@app.get("/")
def root():
    return RedirectResponse(url="/docs")

# Health
@app.get("/healthz")
def healthz(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "env": settings.ENV}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# Metrics
@app.get("/metrics")
def metrics():
    return PlainTextResponse(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)

# API routes
app.include_router(links_router.router)

# Redirect handler
@app.get("/r/{code}")
def redirect(code: str, db: Session = Depends(get_db)):
    # try cache first
    from .routers.links import cache_get
    url = cache_get(code)
    if not url:
        link = db.query(Link).filter(Link.short_code == code).first()
        if not link:
            raise HTTPException(status_code=404, detail="Code not found.")
        url = link.long_url
        # increment stats
        link.clicks += 1
        link.last_accessed = __import__("datetime").datetime.utcnow()
        db.add(link); db.commit()
    else:
        # increment stats if present in DB
        link = db.query(Link).filter(Link.short_code == code).first()
        if link:
            link.clicks += 1
            link.last_accessed = __import__("datetime").datetime.utcnow()
            db.add(link); db.commit()
    return RedirectResponse(url)
