from functools import lru_cache
from typing import Optional

from fastapi.templating import Jinja2Templates
from pydantic_settings import BaseSettings, SettingsConfigDict

templates = Jinja2Templates(directory="templates")

class Settings(BaseSettings):
    """
    Application settings.
    Settings are loaded from environment variables.
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int


@lru_cache()
def get_settings():
    return Settings()