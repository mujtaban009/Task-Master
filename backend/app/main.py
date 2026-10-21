import sys
import asyncio
import logging

# Set event loop policy on Windows before uvicorn or any async tasks start
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.deps import verify_backend_api_key
from app.db.session import engine

# Logging configuration
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("todo_app")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup validation: verify database connectivity
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1;"))
            logger.info("Successfully established connection to PostgreSQL database.")
    except Exception as e:
        logger.error(f"Failed to connect to PostgreSQL database on startup: {e}")
    yield
    # Teardown: gracefully close database connection pool
    await engine.dispose()
    logger.info("Database connection pool disposed gracefully.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from starlette.exceptions import HTTPException as StarletteHTTPException

# Global Exception Handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=getattr(exc, "headers", None),
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception during {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please try again later."},
    )

# Health & Readiness Check Endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Service health and database connectivity probe."""
    db_status = "healthy"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1;"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "online" if db_status == "healthy" else "degraded",
        "database": db_status,
        "environment": settings.ENVIRONMENT,
        "version": settings.VERSION,
    }

# Mount API v1 routes enforcing Backend API Key from frontend client
app.include_router(api_router, prefix=settings.API_V1_STR, dependencies=[Depends(verify_backend_api_key)])
