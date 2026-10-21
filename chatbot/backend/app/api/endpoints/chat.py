from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_chatbot_api_key, get_current_user
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

@router.post("/message", response_model=ChatResponse)
async def send_chat_message(
    chat_in: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_chatbot_api_key),
):
    """
    Send a message to the AI Assistant Chatbot microservice.
    Enforces X-Chatbot-API-Key authentication, user identification, and grounded RAG data retrieval.
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
    _api_key: str = Depends(verify_chatbot_api_key),
):
    """
    List past conversations belonging strictly to the authenticated user.
    """
    conversations = await AIService.list_conversations(db, current_user)
    return [ChatConversationSummaryResponse.model_validate(c) for c in conversations]

@router.get("/conversations/{conversation_id}", response_model=ChatConversationResponse)
async def get_conversation(
    conversation_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_chatbot_api_key),
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
    _api_key: str = Depends(verify_chatbot_api_key),
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

