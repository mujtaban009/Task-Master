import logging
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Notification, User

logger = logging.getLogger("chatbot.notifications")

class NotificationService:
    @staticmethod
    async def create_and_send(
        db: AsyncSession,
        recipient_id: UUID,
        title: str,
        message: str,
        notification_type: str = "task_assigned",
    ) -> Notification:
        """Create and persist an in-app notification for a registered user."""
        notif = Notification(
            user_id=recipient_id,
            title=title,
            message=message,
            type=notification_type,
            read=False,
            delivered=True,
        )
        db.add(notif)
        await db.commit()
        await db.refresh(notif)
        logger.info(f"Notification {notif.id} dispatched to user {recipient_id}: {title}")
        return notif

    @staticmethod
    async def notify_task_assignment(
        db: AsyncSession,
        assignee_id: UUID,
        task_title: str,
        assigner_name: str,
        priority: str = "medium",
    ) -> Notification:
        """Helper to create standard task assignment notification."""
        title = f"New Task Assigned: {task_title}"
        message = (
            f"Administrator {assigner_name} assigned you a new task: "
            f"'{task_title}' with [{priority.upper()}] priority."
        )
        return await NotificationService.create_and_send(
            db=db,
            recipient_id=assignee_id,
            title=title,
            message=message,
            notification_type="task_assigned",
        )

