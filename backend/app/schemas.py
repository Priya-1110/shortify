from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional

class ShortenRequest(BaseModel):
    long_url: HttpUrl
    custom_alias: Optional[str] = None

class ShortenResponse(BaseModel):
    short_url: str
    short_code: str

class ExpandResponse(BaseModel):
    long_url: str

class StatsResponse(BaseModel):
    short_code: str
    long_url: str
    clicks: int
    last_accessed: Optional[str] = None

class Alias(BaseModel):
    alias: str
    @field_validator("alias")
    @classmethod
    def validate_alias(cls, v: str) -> str:
        assert v.isalnum(), "Alias must be alphanumeric."
        assert 3 <= len(v) <= 16, "Alias length must be 3–16."
        return v
