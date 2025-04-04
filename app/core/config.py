from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    APP_NAME: str = "Fictional Character Creator"
    OPENAI_API_KEY: str
    STATIC_FILES_DIR: str = "static"
    IMAGE_STORAGE_PATH: str = os.path.join(STATIC_FILES_DIR, "images")
    API_KEY: str = "default-secret-key-please-change"  # Default that should be overridden in .env

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

@lru_cache()
def get_settings():
    # Ensure IMAGE_STORAGE_PATH exists when settings are loaded
    settings = Settings()
    os.makedirs(settings.IMAGE_STORAGE_PATH, exist_ok=True)
    return settings 