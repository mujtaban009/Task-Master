import os
import sys
import asyncio
from typing import List, Optional
from pydantic_settings import BaseSettings

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

class ChatbotSettings(BaseSettings):
    SERVICE_NAME: str = "AI Assistant Chatbot Microservice"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api/chat"
    PORT: int = 8001
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Chatbot Dedicated API Key Authentication
    # Required for frontend and backend to communicate with this chatbot service
    CHATBOT_API_KEY: str  # required: set in .env, never a default

    # Shared PostgreSQL Database (Same database as Todolist)
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 5432
    DB_USER: str = "postgres"
    DB_PASSWORD: str = "postgres"
    DATABASE_API_KEY: Optional[str] = None
    DB_NAME: str = "todo_app"

    # Database Pool Settings
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # JWT Authentication (Compatible with Todolist token decoding)
    JWT_SECRET_KEY: str  # required: set in .env, never a default
    JWT_ALGORITHM: str = "HS256"

    # LLM Settings
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: Optional[str] = "https://openrouter.ai/api/v1"
    LLM_MODEL: str = "openai/gpt-4o-mini"

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]

    @property
    def async_database_url(self) -> str:
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

settings = ChatbotSettings()

