from typing import List, Optional
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Task, TaskStatus, UserRole
from app.schemas import AdminDashboardStats, UserResponse, UserStatusUpdate

class AdminService:
    @staticmethod
    async def get_dashboard_stats(db: AsyncSession) -> AdminDashboardStats:
        """Aggregate cross-system metrics directly on the database engine."""
        # User counts
        user_query = select(
            func.count(User.id).label("total_users"),
            func.count(User.id).filter(User.is_active == True).label("active_users"),
            func.count(User.id).filter(User.is_active == False).label("inactive_users"),
        )
        user_res = await db.execute(user_query)
        user_row = user_res.one()

        # Task counts
        task_query = select(
            func.count(Task.id).label("total_tasks"),
            func.count(Task.id).filter(Task.status == TaskStatus.PENDING).label("pending"),
            func.count(Task.id).filter(Task.status == TaskStatus.IN_PROGRESS).label("in_progress"),
            func.count(Task.id).filter(Task.status == TaskStatus.COMPLETED).label("completed"),
        )
        task_res = await db.execute(task_query)
        task_row = task_res.one()

        total_tasks = task_row.total_tasks or 0
        completed = task_row.completed or 0
        completion_rate = round((completed / total_tasks * 100), 2) if total_tasks > 0 else 0.0

        return AdminDashboardStats(
            total_users=user_row.total_users or 0,
            active_users=user_row.active_users or 0,
            inactive_users=user_row.inactive_users or 0,
            total_tasks=total_tasks,
            pending_tasks=task_row.pending or 0,
            in_progress_tasks=task_row.in_progress or 0,
            completed_tasks=completed,
            completion_rate_percentage=completion_rate,
        )

    @staticmethod
    async def list_users(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        search: Optional[str] = None,
    ) -> List[User]:
        query = select(User).order_by(desc(User.created_at)).offset(skip).limit(limit)
        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.where(func.lower(User.email).like(term) | func.lower(User.full_name).like(term))

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: UUID) -> User:
        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        return user

    @staticmethod
    async def update_user_status(
        db: AsyncSession,
        user_id: UUID,
        status_update: UserStatusUpdate,
        current_admin: User,
    ) -> User:
        if user_id == current_admin.id and not status_update.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Administrators cannot deactivate their own account.",
            )

        query = select(User).where(User.id == user_id)
        result = await db.execute(query)
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        user.is_active = status_update.is_active
        await db.commit()
        await db.refresh(user)
        return user
