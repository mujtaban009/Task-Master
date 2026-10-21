from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, Task, TaskStatus, TaskPriority, UserRole
from app.schemas import TaskCreate, TaskUpdate
from app.services.task_service import TaskService
from app.services.admin_service import AdminService
from app.services.notification_service import NotificationService

# ============================================================================
# Controlled Tool Definitions & Dispatcher
# All executions strictly enforce server-side role and resource authorization
# ============================================================================

ADMIN_ONLY_TOOL_NAMES = {
    "admin_list_users",
    "admin_get_user_tasks",
    "admin_get_task_analytics",
    "admin_search_all_tasks",
    "admin_get_task_details",
    "admin_create_task",
    "admin_assign_task",
    "admin_update_task",
    "admin_bulk_create_tasks",
    "admin_list_tasks",
    "admin_send_notification",
}

# ----------------------------------------------------------------------------
# User-Scoped Tools (Always bound to current_user.id)
# ----------------------------------------------------------------------------
async def tool_list_my_tasks(
    db: AsyncSession,
    current_user: User,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 15,
) -> Dict[str, Any]:
    """Retrieve tasks belonging exclusively to the authenticated user."""
    status_enum = None
    if status:
        try:
            status_enum = TaskStatus(status.lower())
        except ValueError:
            pass

    priority_enum = None
    if priority:
        try:
            priority_enum = TaskPriority(priority.lower())
        except ValueError:
            pass

    res = await TaskService.get_user_tasks(
        db=db,
        user_id=current_user.id,
        page=1,
        page_size=min(max(1, limit), 50),
        status_filter=status_enum,
        priority_filter=priority_enum,
    )
    return {
        "total_tasks": res.total,
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "description": t.description,
                "status": t.status.value,
                "priority": t.priority.value,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            }
            for t in res.items
        ],
    }

async def tool_search_my_tasks(
    db: AsyncSession,
    current_user: User,
    query: str,
    limit: int = 15,
) -> Dict[str, Any]:
    """Search title and description of tasks belonging to the current user."""
    clean_q = query.strip()
    if not clean_q:
        return {"total_tasks": 0, "tasks": []}

    res = await TaskService.get_user_tasks(
        db=db,
        user_id=current_user.id,
        page=1,
        page_size=min(max(1, limit), 50),
        search=clean_q,
    )
    return {
        "search_query": clean_q,
        "total_found": res.total,
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "description": t.description,
                "status": t.status.value,
                "priority": t.priority.value,
                "due_date": t.due_date.isoformat() if t.due_date else None,
            }
            for t in res.items
        ],
    }

async def tool_get_my_task_details(
    db: AsyncSession,
    current_user: User,
    task_id: str,
) -> Dict[str, Any]:
    """Retrieve full details of a specific task owned by the authenticated user."""
    try:
        t_uuid = UUID(task_id.strip())
    except ValueError:
        return {"error": "Invalid task ID format. Must be a valid UUID."}

    try:
        t = await TaskService.get_task_by_id(db, user_id=current_user.id, task_id=t_uuid)
        return {
            "id": str(t.id),
            "title": t.title,
            "description": t.description,
            "status": t.status.value,
            "priority": t.priority.value,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        }
    except Exception:
        return {"error": "Task not found or you do not have permission to access it."}

async def tool_get_my_task_summary(
    db: AsyncSession,
    current_user: User,
) -> Dict[str, Any]:
    """Retrieve task statistics and status counts for the current user."""
    summary = await TaskService.get_user_task_summary(db, current_user.id)
    return {
        "total_tasks": summary.total_tasks,
        "pending_tasks": summary.pending_tasks,
        "in_progress_tasks": summary.in_progress_tasks,
        "completed_tasks": summary.completed_tasks,
        "high_priority_tasks": summary.high_priority_tasks,
        "overdue_tasks": summary.overdue_tasks,
    }

async def tool_create_my_task(
    db: AsyncSession,
    current_user: User,
    title: str,
    description: Optional[str] = None,
    priority: str = "medium",
    due_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new task owned by the current user."""
    if not title or not title.strip():
        return {"error": "Task title cannot be empty."}

    pri_enum = TaskPriority.MEDIUM
    try:
        pri_enum = TaskPriority(priority.lower())
    except ValueError:
        pass

    parsed_due = None
    if due_date:
        try:
            parsed_due = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
        except ValueError:
            pass

    task_in = TaskCreate(
        title=title.strip(),
        description=description.strip() if description else None,
        priority=pri_enum,
        due_date=parsed_due,
    )
    t = await TaskService.create_task(db, current_user.id, task_in)
    return {
        "success": True,
        "message": f"Task '{t.title}' created successfully.",
        "task": {
            "id": str(t.id),
            "title": t.title,
            "status": t.status.value,
            "priority": t.priority.value,
            "due_date": t.due_date.isoformat() if t.due_date else None,
        },
    }

async def tool_update_my_task_status(
    db: AsyncSession,
    current_user: User,
    task_id: str,
    status: str,
) -> Dict[str, Any]:
    """Update status of a task owned by the current user."""
    try:
        t_uuid = UUID(task_id.strip())
    except ValueError:
        return {"error": "Invalid task ID format."}

    try:
        status_enum = TaskStatus(status.lower())
    except ValueError:
        return {"error": f"Invalid status '{status}'. Valid options are: pending, in_progress, completed."}

    try:
        task_in = TaskUpdate(status=status_enum)
        t = await TaskService.update_task(db, current_user.id, t_uuid, task_in)
        return {
            "success": True,
            "message": f"Task '{t.title}' updated to '{t.status.value}'.",
            "task_id": str(t.id),
            "status": t.status.value,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        }
    except Exception:
        return {"error": "Task not found or access denied."}

# ----------------------------------------------------------------------------
# User Resolution Helpers
# ----------------------------------------------------------------------------
async def resolve_user_helper(
    db: AsyncSession,
    identifier: str,
) -> Tuple[Optional[User], Optional[List[Dict[str, str]]], Optional[str]]:
    """Helper to safely resolve a target user by UUID, exact email, or name substring."""
    clean = identifier.strip()
    if not clean:
        return None, None, "User identifier cannot be empty."

    # 1. UUID check
    try:
        t_uuid = UUID(clean)
        u_res = await db.execute(select(User).where(User.id == t_uuid))
        u = u_res.scalar_one_or_none()
        if u:
            return u, None, None
    except ValueError:
        pass

    # 2. Exact email (case-insensitive)
    u_res = await db.execute(select(User).where(func.lower(User.email) == clean.lower()))
    u = u_res.scalar_one_or_none()
    if u:
        return u, None, None

    # 3. Substring email or full_name
    q = select(User).where(
        or_(
            func.lower(User.email).like(f"%{clean.lower()}%"),
            func.lower(User.full_name).like(f"%{clean.lower()}%"),
        )
    )
    users = (await db.execute(q)).scalars().all()
    if len(users) == 1:
        return users[0], None, None
    elif len(users) > 1:
        candidates = [
            {"id": str(x.id), "full_name": x.full_name, "email": x.email}
            for x in users
        ]
        return None, candidates, f"Multiple users matched '{clean}'. Please clarify."

    return None, None, f"No registered user found matching '{clean}'."

async def resolve_task_helper(
    db: AsyncSession,
    identifier: str,
) -> Tuple[Optional[Task], Optional[List[Dict[str, str]]], Optional[str]]:
    """Helper to safely resolve a task by UUID, exact title, or title substring."""
    clean = identifier.strip()
    if not clean:
        return None, None, "Task identifier cannot be empty."

    try:
        t_uuid = UUID(clean)
        t_res = await db.execute(select(Task).where(Task.id == t_uuid))
        t = t_res.scalar_one_or_none()
        if t:
            return t, None, None
    except ValueError:
        pass

    # Search by title
    q = (
        select(Task, User)
        .join(User, Task.user_id == User.id)
        .where(func.lower(Task.title).like(f"%{clean.lower()}%"))
        .order_by(desc(Task.created_at))
        .limit(10)
    )
    rows = (await db.execute(q)).all()
    if len(rows) == 1:
        return rows[0][0], None, None
    elif len(rows) > 1:
        candidates = [
            {"id": str(r[0].id), "title": r[0].title, "status": r[0].status.value, "owner": r[1].full_name}
            for r in rows
        ]
        return None, candidates, f"Multiple tasks matched '{clean}'. Please specify task ID."

    return None, None, f"No task found matching '{clean}'."

# ----------------------------------------------------------------------------
# Administrative Tools (Strictly protected by current_user.role == 'admin')
# ----------------------------------------------------------------------------
async def tool_admin_list_users(
    db: AsyncSession,
    current_user: User,
    search: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """Admin-only: List registered users in the system."""
    if current_user.role != UserRole.ADMIN:
        return {"error": "Permission denied. Administrative role required."}

    users = await AdminService.list_users(db, skip=0, limit=min(max(1, limit), 50), search=search)
    return {
        "total_returned": len(users),
        "users": [
            {
                "id": str(u.id),
                "full_name": u.full_name,
                "email": u.email,
                "role": u.role.value,
                "is_active": u.is_active,
                "joined_at": u.created_at.isoformat() if u.created_at else None,
            }
            for u in users
        ],
    }

async def tool_admin_get_user_tasks(
    db: AsyncSession,
    current_user: User,
    user_identifier: str,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """Admin-only: Retrieve tasks of a specific user by name, email, or UUID."""
    if current_user.role != UserRole.ADMIN:
        return {"error": "Permission denied. Administrative role required."}

    ident = user_identifier.strip()
    target_user: Optional[User] = None

    # Check if UUID
    try:
        target_uuid = UUID(ident)
        u_res = await db.execute(select(User).where(User.id == target_uuid))
        target_user = u_res.scalar_one_or_none()
    except ValueError:
        pass

    # If not found by UUID, search by email or name
    if not target_user:
        # Check exact email
        u_res = await db.execute(select(User).where(func.lower(User.email) == ident.lower()))
        target_user = u_res.scalar_one_or_none()

    if not target_user:
        # Search by full name
        u_res = await db.execute(select(User).where(func.lower(User.full_name).like(f"%{ident.lower()}%")))
        matching_users = u_res.scalars().all()
        if len(matching_users) > 1:
            return {
                "ambiguous_user": True,
                "message": f"Multiple users found matching '{ident}'. Please specify by email or UUID.",
                "candidates": [
                    {"id": str(u.id), "full_name": u.full_name, "email": u.email}
                    for u in matching_users
                ],
            }
        elif len(matching_users) == 1:
            target_user = matching_users[0]

    if not target_user:
        return {"error": f"No user found matching identifier '{ident}'."}

    # Query tasks for target user
    conditions = [Task.user_id == target_user.id]
    if status:
        try:
            conditions.append(Task.status == TaskStatus(status.lower()))
        except ValueError:
            pass
    if priority:
        try:
            conditions.append(Task.priority == TaskPriority(priority.lower()))
        except ValueError:
            pass

    tasks_q = (
        select(Task)
        .where(and_(*conditions))
        .order_by(desc(Task.created_at))
        .limit(min(max(1, limit), 50))
    )
    res = await db.execute(tasks_q)
    tasks = res.scalars().all()

    return {
        "target_user": {
            "id": str(target_user.id),
            "full_name": target_user.full_name,
            "email": target_user.email,
        },
        "task_count": len(tasks),
        "tasks": [
            {
                "id": str(t.id),
                "title": t.title,
                "description": t.description,
                "status": t.status.value,
                "priority": t.priority.value,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            }
            for t in tasks
        ],
    }

async def tool_admin_get_task_analytics(
    db: AsyncSession,
    current_user: User,
) -> Dict[str, Any]:
    """Admin-only: Aggregate system telemetry and task metrics across all users."""
    if current_user.role != UserRole.ADMIN:
        return {"error": "Permission denied. Administrative role required."}

    stats = await AdminService.get_dashboard_stats(db)
    return {
        "total_users": stats.total_users,
        "active_users": stats.active_users,
        "inactive_users": stats.inactive_users,
        "total_tasks": stats.total_tasks,
        "pending_tasks": stats.pending_tasks,
        "in_progress_tasks": stats.in_progress_tasks,
        "completed_tasks": stats.completed_tasks,
        "completion_rate_percentage": stats.completion_rate_percentage,
    }

async def tool_admin_search_all_tasks(
    db: AsyncSession,
    current_user: User,
    query: str,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """Admin-only: Search tasks across all users by title or description."""
    if current_user.role != UserRole.ADMIN:
        return {"error": "Permission denied. Administrative role required."}

    conditions = []
    if query and query.strip():
        term = f"%{query.strip()}%"
        conditions.append(or_(Task.title.ilike(term), Task.description.ilike(term)))
    if status:
        try:
            conditions.append(Task.status == TaskStatus(status.lower()))
        except ValueError:
            pass
    if priority:
        try:
            conditions.append(Task.priority == TaskPriority(priority.lower()))
        except ValueError:
            pass

    tasks_q = (
        select(Task, User)
        .join(User, Task.user_id == User.id)
        .order_by(desc(Task.created_at))
        .limit(min(max(1, limit), 50))
    )
    if conditions:
        tasks_q = tasks_q.where(and_(*conditions))

    res = await db.execute(tasks_q)
    rows = res.all()

    return {
        "total_found": len(rows),
        "tasks": [
            {
                "id": str(task.id),
                "title": task.title,
                "description": task.description,
                "status": task.status.value,
                "priority": task.priority.value,
                "owner_name": user.full_name,
                "owner_email": user.email,
                "due_date": task.due_date.isoformat() if task.due_date else None,
            }
            for task, user in rows
        ],
    }

async def tool_admin_get_task_details(
    db: AsyncSession,
    current_user: User,
    task_id: str,
) -> Dict[str, Any]:
    """Admin-only: Retrieve details of any task along with owner info."""
    if current_user.role != UserRole.ADMIN:
        return {"error": "Permission denied. Administrative role required."}

    try:
        t_uuid = UUID(task_id.strip())
    except ValueError:
        return {"error": "Invalid task ID format."}

    res = await db.execute(
        select(Task, User).join(User, Task.user_id == User.id).where(Task.id == t_uuid)
    )
    row = res.first()
    if not row:
        return {"error": "Task not found."}

    task, user = row
    return {
        "id": str(task.id),
        "title": task.title,
        "description": task.description,
        "status": task.status.value,
        "priority": task.priority.value,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        "owner": {
            "id": str(user.id),
            "full_name": user.full_name,
            "email": user.email,
        },
    }

async def tool_admin_create_task(
    db: AsyncSession,
    current_user: User,
    title: str,
    description: Optional[str] = None,
    user_identifier: Optional[str] = None,
    priority: str = "medium",
    due_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Admin-only: Create a task and assign it to a specified user or self, and trigger notification."""
    if current_user.role != UserRole.ADMIN:
        return {"error": "Permission denied. Administrative role required."}

    if not title or not title.strip():
        return {"error": "Task title cannot be empty."}

    target_user = current_user
    if user_identifier and user_identifier.strip().lower() not in ["me", "myself", "admin", "self"]:
        u, candidates, err = await resolve_user_helper(db, user_identifier)
        if err:
            return {"error": err, "ambiguous_user": bool(candidates), "candidates": candidates or []}
        target_user = u

    pri_enum = TaskPriority.MEDIUM
    try:
        pri_enum = TaskPriority(priority.lower())
    except ValueError:
        pass

    parsed_due = None
    if due_date:
        try:
            parsed_due = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
        except ValueError:
            pass

    task = Task(
        user_id=target_user.id,
        title=title.strip(),
        description=description.strip() if description else None,
        priority=pri_enum,
        status=TaskStatus.PENDING,
        due_date=parsed_due,
    )
    db.add(task)
    await db.flush()

    notification_info = {"sent": False, "status": "Not required (assigned to self)"}
    if target_user.id != current_user.id:
        try:
            notif = await NotificationService.notify_task_assignment(db, task, target_user, current_user)
            notification_info = {
                "sent": True,
                "status": "Delivered successfully",
                "notification_id": str(notif.id),
                "recipient": target_user.email,
            }
        except Exception as e:
            notification_info = {
                "sent": False,
                "status": f"Notification delivery failed: {str(e)}",
            }

    await db.commit()
    await db.refresh(task)

    return {
        "success": True,
        "message": f"Task '{task.title}' created and assigned to {target_user.full_name}.",
        "task": {
            "id": str(task.id),
            "title": task.title,
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority.value,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "assigned_to": {
                "id": str(target_user.id),
                "full_name": target_user.full_name,
                "email": target_user.email,
            },
        },
        "notification": notification_info,
    }

async def tool_admin_assign_task(
    db: AsyncSession,
    current_user: User,
    task_identifier: str,
    user_identifier: str,
) -> Dict[str, Any]:
    """Admin-only: Reassign an existing task to another user and send assignment notification."""
    if current_user.role != UserRole.ADMIN:
        return {"error": "Permission denied. Administrative role required."}

    task, t_candidates, t_err = await resolve_task_helper(db, task_identifier)
    if t_err:
        return {"error": t_err, "candidates": t_candidates or []}

    target_user, u_candidates, u_err = await resolve_user_helper(db, user_identifier)
    if u_err:
        return {"error": u_err, "candidates": u_candidates or []}

    task.user_id = target_user.id
    db.add(task)

    notification_info = {"sent": False, "status": "Not required (assigned to self)"}
    if target_user.id != current_user.id:
        try:
            notif = await NotificationService.notify_task_assignment(db, task, target_user, current_user)
            notification_info = {
                "sent": True,
                "status": "Delivered successfully",
                "notification_id": str(notif.id),
                "recipient": target_user.email,
            }
        except Exception as e:
            notification_info = {
                "sent": False,
                "status": f"Notification delivery failed: {str(e)}",
            }

    await db.commit()
    await db.refresh(task)

    return {
        "success": True,
        "message": f"Task '{task.title}' successfully assigned to {target_user.full_name}.",
        "task_id": str(task.id),
        "task_title": task.title,
        "assigned_to": {
            "id": str(target_user.id),
            "full_name": target_user.full_name,
            "email": target_user.email,
        },
        "notification": notification_info,
    }

async def tool_admin_update_task(
    db: AsyncSession,
    current_user: User,
    task_identifier: str,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    due_date: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
) -> Dict[str, Any]:
    """Admin-only: Update task status, priority, due date, title, or description."""
    if current_user.role != UserRole.ADMIN:
        return {"error": "Permission denied. Administrative role required."}

    task, candidates, err = await resolve_task_helper(db, task_identifier)
    if err:
        return {"error": err, "candidates": candidates or []}

    if title and title.strip():
        task.title = title.strip()
    if description is not None:
        task.description = description.strip() if description else None

    if priority:
        try:
            task.priority = TaskPriority(priority.lower())
        except ValueError:
            return {"error": f"Invalid priority '{priority}'. Must be low, medium, or high."}

    if status:
        try:
            new_status = TaskStatus(status.lower())
            task.status = new_status
            if new_status == TaskStatus.COMPLETED:
                task.completed_at = datetime.now(timezone.utc)
            else:
                task.completed_at = None
        except ValueError:
            return {"error": f"Invalid status '{status}'. Must be pending, in_progress, or completed."}

    if due_date is not None:
        if due_date == "" or due_date.lower() == "none":
            task.due_date = None
        else:
            try:
                task.due_date = datetime.fromisoformat(due_date.replace("Z", "+00:00"))
            except ValueError:
                return {"error": f"Invalid date format '{due_date}'. Use ISO format (YYYY-MM-DD)."}

    task.updated_at = datetime.now(timezone.utc)
    db.add(task)
    await db.commit()
    await db.refresh(task)

    return {
        "success": True,
        "message": f"Task '{task.title}' updated successfully.",
        "task": {
            "id": str(task.id),
            "title": task.title,
            "status": task.status.value,
            "priority": task.priority.value,
            "due_date": task.due_date.isoformat() if task.due_date else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        },
    }

async def tool_admin_bulk_create_tasks(
    db: AsyncSession,
    current_user: User,
    tasks: List[Dict[str, Any]],
    default_user_identifier: Optional[str] = None,
) -> Dict[str, Any]:
    """Admin-only: Bulk create tasks from a project plan with idempotency/deduplication and assignment."""
    if current_user.role != UserRole.ADMIN:
        return {"error": "Permission denied. Administrative role required."}

    if not tasks:
        return {"error": "No tasks provided for creation."}

    default_user = current_user
    if default_user_identifier and default_user_identifier.strip().lower() not in ["me", "myself", "admin", "self"]:
        u, _, _ = await resolve_user_helper(db, default_user_identifier)
        if u:
            default_user = u

    # Deduplication map by user
    existing_titles_res = await db.execute(
        select(Task.user_id, func.lower(Task.title)).where(Task.status != TaskStatus.COMPLETED)
    )
    existing_pairs = set((row[0], row[1]) for row in existing_titles_res.all())

    created = []
    skipped_duplicates = []
    failed = []

    for item in tasks:
        raw_title = item.get("title", "").strip()
        if not raw_title:
            failed.append({"item": item, "reason": "Missing or empty title"})
            continue

        item_user = default_user
        if item.get("user_identifier"):
            u, _, _ = await resolve_user_helper(db, item["user_identifier"])
            if u:
                item_user = u

        if (item_user.id, raw_title.lower()) in existing_pairs:
            skipped_duplicates.append(raw_title)
            continue

        pri = TaskPriority.MEDIUM
        if item.get("priority"):
            try:
                pri = TaskPriority(item["priority"].lower())
            except ValueError:
                pass

        parsed_due = None
        if item.get("due_date"):
            try:
                parsed_due = datetime.fromisoformat(item["due_date"].replace("Z", "+00:00"))
            except ValueError:
                pass

        new_t = Task(
            user_id=item_user.id,
            title=raw_title,
            description=item.get("description", "").strip() or None,
            priority=pri,
            status=TaskStatus.PENDING,
            due_date=parsed_due,
        )
        db.add(new_t)
        await db.flush()

        if item_user.id != current_user.id:
            try:
                await NotificationService.notify_task_assignment(db, new_t, item_user, current_user)
            except Exception:
                pass

        existing_pairs.add((item_user.id, raw_title.lower()))
        created.append({
            "id": str(new_t.id),
            "title": new_t.title,
            "priority": new_t.priority.value,
            "status": new_t.status.value,
            "assigned_to": item_user.full_name,
        })

    await db.commit()

    return {
        "success": True,
        "total_created": len(created),
        "tasks": created,
        "skipped_duplicates": skipped_duplicates,
        "failed": failed,
    }

async def tool_admin_list_tasks(
    db: AsyncSession,
    current_user: User,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    user_identifier: Optional[str] = None,
    overdue_only: bool = False,
    limit: int = 30,
) -> Dict[str, Any]:
    """Admin-only: Retrieve tasks with complete owner details, overdue filtering, and structured table data."""
    if current_user.role != UserRole.ADMIN:
        return {"error": "Permission denied. Administrative role required."}

    conditions = []
    target_user = None
    if user_identifier and user_identifier.strip():
        target_user, _, err = await resolve_user_helper(db, user_identifier)
        if target_user:
            conditions.append(Task.user_id == target_user.id)
        elif err:
            return {"error": err, "total": 0, "tasks": []}

    now_utc = datetime.now(timezone.utc)
    if overdue_only:
        conditions.append(and_(Task.due_date < now_utc, Task.status != TaskStatus.COMPLETED))
    elif status:
        if status.lower() == "overdue":
            conditions.append(and_(Task.due_date < now_utc, Task.status != TaskStatus.COMPLETED))
        else:
            try:
                conditions.append(Task.status == TaskStatus(status.lower()))
            except ValueError:
                pass

    if priority:
        try:
            conditions.append(Task.priority == TaskPriority(priority.lower()))
        except ValueError:
            pass

    q = (
        select(Task, User)
        .join(User, Task.user_id == User.id)
        .order_by(desc(Task.created_at))
        .limit(min(max(1, limit), 100))
    )
    if conditions:
        q = q.where(and_(*conditions))

    rows = (await db.execute(q)).all()

    tasks_out = []
    table_rows = []
    for task, user in rows:
        due_str = task.due_date.strftime("%Y-%m-%d") if task.due_date else "-"
        is_overdue = bool(task.due_date and task.due_date < now_utc and task.status != TaskStatus.COMPLETED)
        tasks_out.append({
            "id": str(task.id),
            "title": task.title,
            "description": task.description,
            "status": task.status.value,
            "priority": task.priority.value,
            "due_date": due_str,
            "is_overdue": is_overdue,
            "owner_name": user.full_name,
            "owner_email": user.email,
            "owner_id": str(user.id),
        })
        table_rows.append([
            task.title,
            user.full_name,
            task.status.value,
            task.priority.value,
            due_str + (" (Overdue)" if is_overdue else ""),
        ])

    return {
        "total": len(tasks_out),
        "tasks": tasks_out,
        "structured_table": {
            "headers": ["Task Title", "Assigned To", "Status", "Priority", "Due Date"],
            "rows": table_rows,
        },
    }

async def tool_admin_send_notification(
    db: AsyncSession,
    current_user: User,
    user_identifier: str,
    title: str,
    message: str,
) -> Dict[str, Any]:
    """Admin-only: Dispatch an administrative notification to any user."""
    if current_user.role != UserRole.ADMIN:
        return {"error": "Permission denied. Administrative role required."}

    target_user, candidates, err = await resolve_user_helper(db, user_identifier)
    if err:
        return {"error": err, "candidates": candidates or []}

    notif = await NotificationService.create_and_send(
        db=db,
        user_id=target_user.id,
        title=title,
        message=message,
        notification_type="admin_broadcast",
    )
    await db.commit()

    return {
        "success": True,
        "message": f"Notification successfully delivered to {target_user.full_name} ({target_user.email}).",
        "notification": {
            "id": str(notif.id),
            "recipient": target_user.email,
            "title": notif.title,
            "delivered": True,
        },
    }

# ----------------------------------------------------------------------------
# Master Tool Registry & Dispatcher
# ----------------------------------------------------------------------------
TOOL_HANDLERS = {
    "list_my_tasks": tool_list_my_tasks,
    "search_my_tasks": tool_search_my_tasks,
    "get_my_task_details": tool_get_my_task_details,
    "get_my_task_summary": tool_get_my_task_summary,
    "create_my_task": tool_create_my_task,
    "update_my_task_status": tool_update_my_task_status,
    "admin_list_users": tool_admin_list_users,
    "admin_get_user_tasks": tool_admin_get_user_tasks,
    "admin_get_task_analytics": tool_admin_get_task_analytics,
    "admin_search_all_tasks": tool_admin_search_all_tasks,
    "admin_get_task_details": tool_admin_get_task_details,
    "admin_create_task": tool_admin_create_task,
    "admin_assign_task": tool_admin_assign_task,
    "admin_update_task": tool_admin_update_task,
    "admin_bulk_create_tasks": tool_admin_bulk_create_tasks,
    "admin_list_tasks": tool_admin_list_tasks,
    "admin_send_notification": tool_admin_send_notification,
}

async def execute_tool(
    tool_name: str,
    args: Dict[str, Any],
    current_user: User,
    db: AsyncSession,
) -> Dict[str, Any]:
    """Central authorized tool executor."""
    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        return {"error": f"Unknown tool '{tool_name}'."}

    # Strict server-side security check: reject admin tools for non-admins
    if tool_name in ADMIN_ONLY_TOOL_NAMES and current_user.role != UserRole.ADMIN:
        return {
            "error": "Permission denied. You do not have administrative privileges to access this information or perform this operation."
        }

    try:
        return await handler(db=db, current_user=current_user, **args)
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"}

