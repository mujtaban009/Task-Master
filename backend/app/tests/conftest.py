import os
import sys
import asyncio
from pathlib import Path

# Tests get their own database and never call the external LLM; set before app settings load
os.environ["DB_NAME"] = "todo_app_test"
os.environ.pop("POSTGRES_URL", None)  # never let tests reach a hosted database
os.environ["OPENAI_API_KEY"] = ""

import psycopg
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.core.config import settings
from app.db.session import get_db

INIT_SQL_DIR = Path(__file__).resolve().parents[3] / "database" / "init"

def _rebuild_test_database() -> None:
    """Recreate todo_app_test from the init SQL files (schema + seed) once per test run."""
    db_pass = settings.DATABASE_API_KEY or settings.DB_PASSWORD
    server = f"host={settings.DB_HOST} port={settings.DB_PORT} user={settings.DB_USER} password={db_pass}"
    with psycopg.connect(f"{server} dbname=postgres", autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{settings.DB_NAME}" WITH (FORCE)')
        conn.execute(f'CREATE DATABASE "{settings.DB_NAME}"')
    with psycopg.connect(f"{server} dbname={settings.DB_NAME}", autocommit=True) as conn:
        for sql_file in sorted(INIT_SQL_DIR.glob("*.sql")):
            conn.execute(sql_file.read_text(encoding="utf-8"))

assert settings.DB_NAME == "todo_app_test", "Refusing to run tests against a non-test database"
_rebuild_test_database()

TEST_DB_URL = settings.async_database_url

engine_test = create_async_engine(TEST_DB_URL, future=True)
TestingSessionLocal = async_sessionmaker(bind=engine_test, class_=AsyncSession, expire_on_commit=False)

@pytest_asyncio.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest_asyncio.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()

@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"X-API-Key": settings.BACKEND_API_KEY} if settings.BACKEND_API_KEY else {},
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
