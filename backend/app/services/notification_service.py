import logging
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification, User, Task

logger = logging.getLogger("todo_app.notifications")

class NotificationService:
    @staticmethod
    async def create_and_send(
        db: AsyncSession,
        user_id: UUID,
        title: str,
        message: str,
        notification_type: str = "task_assigned",
    ) -> Notification:
        """
        Creates and immediately records a verified in-app notification for the target user.
        """
        notif = Notification(
            user_id=user_id,
            title=title.strip(),
            message=message.strip(),
            type=notification_type,
            read=False,
            delivered=True,
        )
        db.add(notif)
        await db.flush()
        logger.info(f"Notification '{title}' created for user {user_id} (ID: {notif.id})")
        return notif

    @staticmethod
    async def notify_task_assignment(
        db: AsyncSession,
        task: Task,
        assignee: User,
        assigned_by: User,
    ) -> Notification:
        """
        Standardized notification for task assignment / reassignment by an administrator.
        """
        title = f"New Task Assigned: {task.title}"
        pri_str = task.priority.value.upper()
        due_str = f" due on {task.due_date.strftime('%Y-%m-%d')}" if task.due_date else ""
        msg = (
            f"Administrator {assigned_by.full_name} assigned you a new task: '{task.title}' "
            f"with [{pri_str}] priority{due_str}."
        )
        return await NotificationService.create_and_send(
            db=db,
            user_id=assignee.id,
            title=title,
            message=msg,
            notification_type="task_assigned",
        )

    @staticmethod
    async def get_user_notifications(
        db: AsyncSession,
        user_id: UUID,
        limit: int = 20,
    ) -> List[Notification]:
        """Fetch latest notifications for a specific user."""
        q = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(desc(Notification.created_at))
            .limit(limit)
        )
        res = await db.execute(q)
        return list(res.scalars().all())

    @staticmethod
    async def get_unread_count(db: AsyncSession, user_id: UUID) -> int:
        """Count unread notifications for a user."""
        q = (
            select(func.count(Notification.id))
            .where(and_(Notification.user_id == user_id, Notification.read == False))
        )
        res = await db.execute(q)
        return res.scalar() or 0
