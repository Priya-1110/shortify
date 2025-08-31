from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "Shortify"
    BASE_URL: str = "http://localhost:8000"
    DATABASE_URL: str = "postgresql+psycopg2://shortify:shortify@localhost:5432/shortify"
    REDIS_URL: str = "redis://localhost:6379/0"
    DEFAULT_CODE_LEN: int = 7
    ENV: str = "local"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
