from fastapi import APIRouter
from sqlalchemy import text
from app.core.config import settings
from app.db.session import engine
from app.schemas import ChatbotHealthResponse

router = APIRouter()

@router.get("/health", response_model=ChatbotHealthResponse, tags=["Health"])
async def chatbot_health_check():
    """Health & database probe for the Chatbot microservice."""
    db_status = "connected"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1;"))
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return ChatbotHealthResponse(
        status="online" if db_status == "connected" else "degraded",
        service=settings.SERVICE_NAME,
        database=db_status,
        api_key_configured=bool(settings.CHATBOT_API_KEY),
        version=settings.VERSION,
    )

