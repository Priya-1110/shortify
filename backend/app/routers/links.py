from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
import redis

from ..db import get_db
from ..models import Link
from ..schemas import ShortenRequest, ShortenResponse, ExpandResponse, StatsResponse
from ..config import settings
from ..utils import generate_code

router = APIRouter(prefix="/api", tags=["links"])
_redis = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

def cache_put(code: str, url: str): _redis.set(f"code:{code}", url)
def cache_get(code: str): return _redis.get(f"code:{code}")

@router.post("/shorten", response_model=ShortenResponse)
def shorten(payload: ShortenRequest, db: Session = Depends(get_db)):
    code = payload.custom_alias or generate_code(settings.DEFAULT_CODE_LEN)
    if payload.custom_alias:
        if db.scalar(select(Link).where(Link.short_code == code)):
            raise HTTPException(status_code=409, detail="Custom alias already taken.")
    link = Link(short_code=code, long_url=str(payload.long_url))
    db.add(link)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Alias collision. Retry.")
    cache_put(code, link.long_url)
    return ShortenResponse(short_url=f"{settings.BASE_URL}/r/{code}", short_code=code)

@router.get("/expand/{code}", response_model=ExpandResponse)
def expand(code: str, db: Session = Depends(get_db)):
    url = cache_get(code)
    if url: return ExpandResponse(long_url=url)
    link = db.scalar(select(Link).where(Link.short_code == code))
    if not link: raise HTTPException(status_code=404, detail="Code not found.")
    cache_put(code, link.long_url)
    return ExpandResponse(long_url=link.long_url)

@router.get("/stats/{code}", response_model=StatsResponse)
def stats(code: str, db: Session = Depends(get_db)):
    link = db.scalar(select(Link).where(Link.short_code == code))
    if not link: raise HTTPException(status_code=404, detail="Code not found.")
    return StatsResponse(
        short_code=code,
        long_url=link.long_url,
        clicks=link.clicks,
        last_accessed=link.last_accessed.isoformat() if link.last_accessed else None
    )
