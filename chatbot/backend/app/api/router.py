from fastapi import APIRouter
from app.api.endpoints import chat, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(chat.router, tags=["AI Assistant Chatbot"])

