import os
import re
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "Production-Ready To-Do List API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # PostgreSQL Connection
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DB_NAME: str = "todo_app"
    # Set by the Neon integration on Vercel; when present it wins over the DB_* parts
    POSTGRES_URL: Optional[str] = None

    # Database Pool Settings
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # JWT Authentication
    JWT_SECRET_KEY: str  # required: set in .env, never a default
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Security & API Keys Architecture
    BACKEND_API_KEY: str = "bk_live_4d9f8a2e1c7b05e3a6f82c1b9d4e7a2c"
    DATABASE_API_KEY: Optional[str] = None

    # AI Assistant & Chatbot Settings
    CHATBOT_API_KEY: str = "cb_live_8f3a9e14c72b05d1e67a42b98f2316"
    CHATBOT_SERVICE_URL: str = "http://127.0.0.1:8001/api/chat"
    OPENAI_API_KEY: Optional[str] = None
    # Defaults target Google Gemini's free OpenAI-compatible API; only OPENAI_API_KEY must be set
    OPENAI_BASE_URL: Optional[str] = "https://generativelanguage.googleapis.com/v1beta/openai"
    LLM_MODEL: str = "gemini-3.5-flash-lite"  # fastest stable Gemini; 2.5-flash is closed to new keys

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]

    @property
    def async_database_url(self) -> str:
        if self.POSTGRES_URL:
            return re.sub(r"^postgres(ql)?://", "postgresql+psycopg://", self.POSTGRES_URL)
        db_pass = self.DATABASE_API_KEY or self.DB_PASSWORD
        return f"postgresql+psycopg://{self.DB_USER}:{db_pass}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def sync_database_url(self) -> str:
        db_pass = self.DATABASE_API_KEY or self.DB_PASSWORD
        return f"postgresql+psycopg://{self.DB_USER}:{db_pass}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"

settings = Settings()
