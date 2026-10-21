from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models import User, TaskStatus, TaskPriority
from app.schemas import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskListResponse,
    TaskSummaryResponse,
)
from app.services.task_service import TaskService

router = APIRouter()

@router.get("/summary", response_model=TaskSummaryResponse)
async def get_task_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve statistical summary for the authenticated user's tasks."""
    return await TaskService.get_user_task_summary(db, current_user.id)

@router.get("", response_model=TaskListResponse)
async def list_tasks(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    priority: Optional[TaskPriority] = Query(None, description="Filter by priority"),
    search: Optional[str] = Query(None, description="Search term for task title"),
    sort_by: str = Query("created_at", pattern="^(created_at|due_date|priority|title)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List authenticated user's tasks with database-side filtering, sorting, and pagination."""
    return await TaskService.get_user_tasks(
        db=db,
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        status_filter=status,
        priority_filter=priority,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_in: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new task owned by the authenticated user."""
    return await TaskService.create_task(db, current_user.id, task_in)

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve an individual task ensuring strict ownership validation."""
    return await TaskService.get_task_by_id(db, current_user.id, task_id)

@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: UUID,
    task_in: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Partially update a task owned by the authenticated user."""
    return await TaskService.update_task(db, current_user.id, task_id, task_in)

@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a task owned by the authenticated user."""
    await TaskService.delete_task(db, current_user.id, task_id)
    return None
