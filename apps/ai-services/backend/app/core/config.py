import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Visulara Meditation API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # CORS
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:5501",
        "http://127.0.0.1:5501",
    ]

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./db.sqlite3"

    # Services
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"  # Update from gpt-5
    
    ELEVEN_API_KEY: str = ""
    ELEVEN_TTS_MODEL: str = "eleven_multilingual_v2"

    MEDITATION_AUDIO_FOLDER: str = "meditations/audio"

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
