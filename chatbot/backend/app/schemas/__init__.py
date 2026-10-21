from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.models import UserRole, TaskStatus, TaskPriority

# ---------------------------------------------------------
# User Schemas
# ---------------------------------------------------------
class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=120)

    @field_validator("full_name")
    @classmethod
    def full_name_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Full name cannot be empty or blank")
        return v.strip()

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)

class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=120)
    password: Optional[str] = Field(None, min_length=8, max_length=128)

    @field_validator("full_name")
    @classmethod
    def full_name_must_not_be_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Full name cannot be empty or blank")
        return v.strip() if v else None

class UserResponse(UserBase):
    id: UUID
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UserStatusUpdate(BaseModel):
    is_active: bool

# ---------------------------------------------------------
# Token Schemas
# ---------------------------------------------------------
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

class TokenRefreshRequest(BaseModel):
    refresh_token: str

class TokenRefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

# ---------------------------------------------------------
# Task Schemas
# ---------------------------------------------------------
class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Task title cannot be empty or blank")
        return v.strip()

class TaskCreate(TaskBase):
    status: TaskStatus = TaskStatus.PENDING

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Task title cannot be empty or blank")
        return v.strip() if v else None

class TaskResponse(TaskBase):
    id: UUID
    user_id: UUID
    status: TaskStatus
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TaskListResponse(BaseModel):
    items: List[TaskResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

class TaskSummaryResponse(BaseModel):
    total_tasks: int
    pending_tasks: int
    in_progress_tasks: int
    completed_tasks: int
    high_priority_tasks: int
    overdue_tasks: int

# ---------------------------------------------------------
# Admin Dashboard Schemas
# ---------------------------------------------------------
class AdminDashboardStats(BaseModel):
    total_users: int
    active_users: int
    inactive_users: int
    total_tasks: int
    pending_tasks: int
    in_progress_tasks: int
    completed_tasks: int
    completion_rate_percentage: float

# ---------------------------------------------------------
# Chat & AI Assistant Schemas
# ---------------------------------------------------------
class ChatMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
    conversation_id: Optional[UUID] = None

class ChatMessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    sender: str
    content: str
    metadata: Optional[dict] = Field(default_factory=dict, alias="metadata_")
    created_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True

class ChatConversationSummaryResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ChatConversationResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: Optional[List[ChatMessageResponse]] = None

    class Config:
        from_attributes = True

class ChatResponse(BaseModel):
    conversation_id: UUID
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
    tools_executed: Optional[List[str]] = None

# ---------------------------------------------------------
# Notification Schemas
# ---------------------------------------------------------
class NotificationResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    message: str
    type: str
    read: bool
    delivered: bool
    created_at: datetime

    class Config:
        from_attributes = True

class NotificationListResponse(BaseModel):
    items: List[NotificationResponse]
    total: int
    unread_count: int

class ChatbotHealthResponse(BaseModel):
    status: str
    service: str
    database: str
    api_key_configured: bool
    version: str

