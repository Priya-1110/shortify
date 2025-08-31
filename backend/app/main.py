from fastapi import FastAPI

app = FastAPI(title="Shortify")

@app.get("/healthz")
def health():
    return {"status": "ok"}
