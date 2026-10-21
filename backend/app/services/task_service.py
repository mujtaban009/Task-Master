from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Task, TaskStatus, TaskPriority, User
from app.schemas import (
    TaskCreate,
    TaskUpdate,
    TaskListResponse,
    TaskResponse,
    TaskSummaryResponse,
)

class TaskService:
    @staticmethod
    async def create_task(db: AsyncSession, user_id: UUID, task_in: TaskCreate) -> Task:
        completed_at = None
        if task_in.status == TaskStatus.COMPLETED:
            completed_at = datetime.now(timezone.utc)

        task = Task(
            user_id=user_id,
            title=task_in.title,
            description=task_in.description,
            status=task_in.status,
            priority=task_in.priority,
            due_date=task_in.due_date,
            completed_at=completed_at,
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return task

    @staticmethod
    async def get_user_tasks(
        db: AsyncSession,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[TaskStatus] = None,
        priority_filter: Optional[TaskPriority] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> TaskListResponse:
        page = max(1, page)
        page_size = min(max(1, page_size), 100)
        offset = (page - 1) * page_size

        # Base filter: Only tasks owned by the authenticated user
        conditions = [Task.user_id == user_id]

        if status_filter:
            conditions.append(Task.status == status_filter)
        if priority_filter:
            conditions.append(Task.priority == priority_filter)
        if search and search.strip():
            conditions.append(Task.title.ilike(f"%{search.strip()}%"))

        # Count total matching rows
        count_query = select(func.count(Task.id)).where(and_(*conditions))
        total_result = await db.execute(count_query)
        total = total_result.scalar_one()

        # Sorting logic
        sort_column = Task.created_at
        if sort_by == "due_date":
            sort_column = Task.due_date
        elif sort_by == "priority":
            sort_column = Task.priority
        elif sort_by == "title":
            sort_column = Task.title

        order_expr = desc(sort_column) if sort_order.lower() == "desc" else asc(sort_column)

        # Execute paginated query
        query = (
            select(Task)
            .where(and_(*conditions))
            .order_by(order_expr)
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(query)
        tasks = result.scalars().all()

        total_pages = (total + page_size - 1) // page_size if total > 0 else 1

        return TaskListResponse(
            items=[TaskResponse.model_validate(t) for t in tasks],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    @staticmethod
    async def get_task_by_id(db: AsyncSession, user_id: UUID, task_id: UUID) -> Task:
        query = select(Task).where(Task.id == task_id, Task.user_id == user_id)
        result = await db.execute(query)
        task = result.scalar_one_or_none()
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found or access denied.",
            )
        return task

    @staticmethod
    async def update_task(db: AsyncSession, user_id: UUID, task_id: UUID, task_in: TaskUpdate) -> Task:
        task = await TaskService.get_task_by_id(db, user_id, task_id)

        update_data = task_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(task, field, value)

        # Handle completed_at timestamp compliance
        if "status" in update_data:
            if task.status == TaskStatus.COMPLETED:
                if not task.completed_at:
                    task.completed_at = datetime.now(timezone.utc)
            else:
                task.completed_at = None

        await db.commit()
        await db.refresh(task)
        return task

    @staticmethod
    async def delete_task(db: AsyncSession, user_id: UUID, task_id: UUID) -> None:
        task = await TaskService.get_task_by_id(db, user_id, task_id)
        await db.delete(task)
        await db.commit()

    @staticmethod
    async def get_user_task_summary(db: AsyncSession, user_id: UUID) -> TaskSummaryResponse:
        """Efficient database-side aggregation for user task statistics."""
        now = datetime.now(timezone.utc)
        query = select(
            func.count(Task.id).label("total"),
            func.count(Task.id).filter(Task.status == TaskStatus.PENDING).label("pending"),
            func.count(Task.id).filter(Task.status == TaskStatus.IN_PROGRESS).label("in_progress"),
            func.count(Task.id).filter(Task.status == TaskStatus.COMPLETED).label("completed"),
            func.count(Task.id).filter(Task.priority == TaskPriority.HIGH).label("high_priority"),
            func.count(Task.id).filter(and_(Task.due_date < now, Task.status != TaskStatus.COMPLETED)).label("overdue"),
        ).where(Task.user_id == user_id)

        result = await db.execute(query)
        row = result.one()

        return TaskSummaryResponse(
            total_tasks=row.total or 0,
            pending_tasks=row.pending or 0,
            in_progress_tasks=row.in_progress or 0,
            completed_tasks=row.completed or 0,
            high_priority_tasks=row.high_priority or 0,
            overdue_tasks=row.overdue or 0,
        )
