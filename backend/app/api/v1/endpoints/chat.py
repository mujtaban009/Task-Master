from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas import (
    ChatMessageCreate,
    ChatResponse,
    ChatConversationResponse,
    ChatConversationSummaryResponse,
)
from app.services.ai_service import AIService

router = APIRouter()

def verify_chatbot_key(x_chatbot_api_key: Optional[str] = Header(None, alias="X-Chatbot-API-Key")):
    """Validates X-Chatbot-API-Key when supplied by the client."""
    if settings.CHATBOT_API_KEY and x_chatbot_api_key and x_chatbot_api_key.strip() != settings.CHATBOT_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Chatbot API key. Access denied.",
        )
    return x_chatbot_api_key

@router.post("/message", response_model=ChatResponse)
async def send_chat_message(
    chat_in: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _api_key: Optional[str] = Depends(verify_chatbot_key),
):
    """
    Send a message to the AI Assistant.
    Enforces server-side authentication, role authorization, and grounded RAG data retrieval.
    """
    return await AIService.process_chat_message(
        db=db,
        current_user=current_user,
        content=chat_in.content,
        conversation_id=chat_in.conversation_id,
    )

@router.get("/conversations", response_model=List[ChatConversationSummaryResponse])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _api_key: Optional[str] = Depends(verify_chatbot_key),
):
    """
    List conversations belonging strictly to the authenticated user.
    """
    conversations = await AIService.list_conversations(db, current_user)
    return [ChatConversationSummaryResponse.model_validate(c) for c in conversations]

@router.get("/conversations/{conversation_id}", response_model=ChatConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _api_key: Optional[str] = Depends(verify_chatbot_key),
):
    """
    Retrieve full conversation history with strict server-side ownership verification.
    """
    conv = await AIService.get_conversation_history(db, current_user, conversation_id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied.",
        )
    return ChatConversationResponse.model_validate(conv)

@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _api_key: Optional[str] = Depends(verify_chatbot_key),
):
    """
    Delete a conversation owned by the authenticated user.
    """
    success = await AIService.delete_conversation(db, current_user, conversation_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found or access denied.",
        )
    return None
