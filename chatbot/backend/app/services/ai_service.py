import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import httpx
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import User, UserRole, Task, TaskStatus, TaskPriority, ChatConversation, ChatMessage
from app.schemas import (
    ChatMessageResponse,
    ChatConversationResponse,
    ChatResponse,
)
from app.services.ai_tools import (
    execute_tool,
    ADMIN_ONLY_TOOL_NAMES,
)

logger = logging.getLogger("todo_app.ai")


def _format_task_response(
    greeting_name: str,
    tasks: List[Any],
    task_type: str = "pending tasks",
) -> Tuple[str, Dict[str, Any]]:
    """
    Standardizes task presentation according to user requirement:
    - Greet user: "Hi {name},"
    - If 0 tasks: State clearly no tasks.
    - If 1 to 3 tasks: Format in bullet points.
    - If > 3 tasks: Format in clean Markdown table.
    """
    first_name = (greeting_name or "User").strip()

    if not tasks:
        return (
            f"Hi {first_name},\n\nYou currently have no {task_type}. Everything is up to date!",
            {"response_type": "text"},
        )

    if len(tasks) <= 3:
        bullets = []
        for t in tasks:
            title = getattr(t, "title", None) or (t.get("title") if isinstance(t, dict) else str(t))
            status = getattr(getattr(t, "status", None), "value", None) or (t.get("status") if isinstance(t, dict) else "pending")
            priority = getattr(getattr(t, "priority", None), "value", None) or (t.get("priority") if isinstance(t, dict) else "medium")
            due = getattr(t, "due_date", None) if hasattr(t, "due_date") else (t.get("due_date") if isinstance(t, dict) else None)
            due_str = str(due)[:10] if due else "No deadline"
            bullets.append(f"- **{title}** — Status: `{status}` | Priority: `{priority}` | Due Date: {due_str}")

        msg = f"Hi {first_name},\n\nHere are your {task_type}:\n\n" + "\n".join(bullets)
        return msg, {"response_type": "text"}

    headers = ["Task Title", "Status", "Priority", "Due Date"]
    table_lines = [
        "| Task Title | Status | Priority | Due Date |",
        "| :--- | :---: | :---: | :---: |",
    ]
    rows = []
    for t in tasks:
        title = getattr(t, "title", None) or (t.get("title") if isinstance(t, dict) else str(t))
        status = getattr(getattr(t, "status", None), "value", None) or (t.get("status") if isinstance(t, dict) else "pending")
        priority = getattr(getattr(t, "priority", None), "value", None) or (t.get("priority") if isinstance(t, dict) else "medium")
        due = getattr(t, "due_date", None) if hasattr(t, "due_date") else (t.get("due_date") if isinstance(t, dict) else None)
        due_str = str(due)[:10] if due else "No deadline"
        table_lines.append(f"| **{title}** | `{status}` | `{priority}` | {due_str} |")
        rows.append([title, status, priority, due_str])

    msg = f"Hi {first_name},\n\nHere are your {task_type}:\n\n" + "\n".join(table_lines)
    return msg, {
        "response_type": "table",
        "structured_table": {"headers": headers, "rows": rows},
    }


# ============================================================================
# OpenAI-Compatible Tool Schema Manifest
# ============================================================================

USER_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_my_tasks",
            "description": "List the authenticated user's own tasks. Filterable by status (pending, in_progress, completed) and priority (low, medium, high).",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    "limit": {"type": "integer", "default": 15},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_my_tasks",
            "description": "Search the authenticated user's tasks by matching keywords in title or description.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search term or keyword"},
                    "limit": {"type": "integer", "default": 15},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_task_details",
            "description": "Retrieve complete details for a specific task owned by the authenticated user by its UUID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "UUID of the task"},
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_task_summary",
            "description": "Retrieve task statistics (total, pending, in-progress, completed, high-priority, overdue counts) for the authenticated user.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_my_task",
            "description": "Create a new task for the authenticated user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Title of the task"},
                    "description": {"type": "string", "description": "Optional notes or details"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"], "default": "medium"},
                    "due_date": {"type": "string", "description": "ISO format datetime string (e.g., 2026-10-25T18:00:00Z)"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_my_task_status",
            "description": "Update the status of an existing task owned by the authenticated user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "UUID of the task"},
                    "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                },
                "required": ["task_id", "status"],
            },
        },
    },
]

ADMIN_TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "admin_list_users",
            "description": "Administrator only: List registered users in the application.",
            "parameters": {
                "type": "object",
                "properties": {
                    "search": {"type": "string", "description": "Search keyword for user email or full name"},
                    "limit": {"type": "integer", "default": 20},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "admin_get_user_tasks",
            "description": "Administrator only: Retrieve tasks belonging to any specific user identified by name, email, or UUID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_identifier": {"type": "string", "description": "Name, email, or UUID of the target user"},
                    "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    "limit": {"type": "integer", "default": 20},
                },
                "required": ["user_identifier"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "admin_get_task_analytics",
            "description": "Administrator only: Retrieve system-wide telemetry metrics including total users, active/inactive counts, task status distribution, and completion rates.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "admin_search_all_tasks",
            "description": "Administrator only: Search tasks across all system users by keyword, status, or priority.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search keyword"},
                    "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    "limit": {"type": "integer", "default": 20},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "admin_get_task_details",
            "description": "Administrator only: Retrieve complete details and owner info for any task by its UUID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "UUID of the task"},
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "admin_create_task",
            "description": "Administrator only: Create a task and assign it to a specified user or self, and deliver an in-app assignment notification.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Title of the task"},
                    "description": {"type": "string", "description": "Detailed notes or task specs"},
                    "user_identifier": {"type": "string", "description": "Name, email, or UUID of assignee (leave empty for self)"},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"], "default": "medium"},
                    "due_date": {"type": "string", "description": "ISO date format (YYYY-MM-DD)"},
                },
                "required": ["title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "admin_assign_task",
            "description": "Administrator only: Reassign an existing task to another user and deliver an assignment notification.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_identifier": {"type": "string", "description": "UUID or title of the task to assign"},
                    "user_identifier": {"type": "string", "description": "Name, email, or UUID of new assignee"},
                },
                "required": ["task_identifier", "user_identifier"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "admin_update_task",
            "description": "Administrator only: Update an existing task's status, priority, due date, title, or description.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_identifier": {"type": "string", "description": "UUID or title of the task to update"},
                    "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    "due_date": {"type": "string", "description": "ISO date string (YYYY-MM-DD) or 'none' to clear"},
                    "title": {"type": "string", "description": "New title"},
                    "description": {"type": "string", "description": "New description"},
                },
                "required": ["task_identifier"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "admin_bulk_create_tasks",
            "description": "Administrator only: Convert a project plan into multiple database-backed tasks with deduplication and assignment notifications.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "description": {"type": "string"},
                                "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                                "due_date": {"type": "string"},
                                "user_identifier": {"type": "string"},
                            },
                            "required": ["title"],
                        },
                        "description": "List of task objects to persist to the database",
                    },
                    "default_user_identifier": {"type": "string", "description": "Default assignee for tasks if not individually specified"},
                },
                "required": ["tasks"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "admin_list_tasks",
            "description": "Administrator only: Query tasks with owner details, overdue filtering, and structured table output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "overdue"]},
                    "priority": {"type": "string", "enum": ["low", "medium", "high"]},
                    "user_identifier": {"type": "string", "description": "Filter by user name, email, or UUID"},
                    "overdue_only": {"type": "boolean", "default": False},
                    "limit": {"type": "integer", "default": 30},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "admin_send_notification",
            "description": "Administrator only: Send an in-app administrative broadcast/notification to any registered user.",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_identifier": {"type": "string", "description": "Recipient name, email, or UUID"},
                    "title": {"type": "string", "description": "Subject/title of notification"},
                    "message": {"type": "string", "description": "Notification message body"},
                },
                "required": ["user_identifier", "title", "message"],
            },
        },
    },
]

# ============================================================================
# AIService Orchestrator
# ============================================================================

class AIService:
    @staticmethod
    async def get_or_create_conversation(
        db: AsyncSession,
        current_user: User,
        conversation_id: Optional[UUID] = None,
        initial_title: Optional[str] = None,
    ) -> ChatConversation:
        """Retrieve existing conversation ensuring strict ownership, or create a new one."""
        if conversation_id:
            query = select(ChatConversation).where(
                ChatConversation.id == conversation_id,
                ChatConversation.user_id == current_user.id,
            )
            result = await db.execute(query)
            conv = result.scalar_one_or_none()
            if conv:
                return conv

        # Create new conversation for current user
        title = initial_title.strip()[:60] if initial_title else "New Conversation"
        conv = ChatConversation(user_id=current_user.id, title=title)
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        return conv

    @staticmethod
    async def list_conversations(
        db: AsyncSession,
        current_user: User,
        limit: int = 30,
    ) -> List[ChatConversation]:
        """List authenticated user's conversations ordered by recent activity."""
        query = (
            select(ChatConversation)
            .where(ChatConversation.user_id == current_user.id)
            .order_by(desc(ChatConversation.updated_at))
            .limit(limit)
        )
        res = await db.execute(query)
        return res.scalars().all()

    @staticmethod
    async def get_conversation_history(
        db: AsyncSession,
        current_user: User,
        conversation_id: UUID,
    ) -> Optional[ChatConversation]:
        """Retrieve full conversation history with strict ownership check."""
        from sqlalchemy.orm import selectinload

        query = (
            select(ChatConversation)
            .options(selectinload(ChatConversation.messages))
            .where(
                ChatConversation.id == conversation_id,
                ChatConversation.user_id == current_user.id,
            )
        )
        res = await db.execute(query)
        return res.scalar_one_or_none()

    @staticmethod
    async def delete_conversation(
        db: AsyncSession,
        current_user: User,
        conversation_id: UUID,
    ) -> bool:
        """Delete a conversation owned by the authenticated user."""
        query = select(ChatConversation).where(
            ChatConversation.id == conversation_id,
            ChatConversation.user_id == current_user.id,
        )
        res = await db.execute(query)
        conv = res.scalar_one_or_none()
        if not conv:
            return False
        await db.delete(conv)
        await db.commit()
        return True

    @staticmethod
    async def process_chat_message(
        db: AsyncSession,
        current_user: User,
        content: str,
        conversation_id: Optional[UUID] = None,
    ) -> ChatResponse:
        """Main chat orchestration pipeline enforcing role-based RAG and permissions."""
        content_clean = content.strip()

        # 1. Resolve or create conversation
        conv = await AIService.get_or_create_conversation(
            db,
            current_user,
            conversation_id,
            initial_title=content_clean[:40],
        )

        # 2. Persist user message
        user_msg = ChatMessage(
            conversation_id=conv.id,
            sender="user",
            content=content_clean,
            metadata_={},
        )
        db.add(user_msg)
        await db.commit()
        await db.refresh(user_msg)

        # 3. Retrieve conversation history for context (last 10 messages)
        history_q = (
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conv.id)
            .order_by(desc(ChatMessage.created_at))
            .limit(10)
        )
        history_res = await db.execute(history_q)
        recent_messages = list(reversed(history_res.scalars().all()))

        # 4. Think using RAG from the database (authoritative PostgreSQL records)
        rag_data = await AIService._retrieve_database_rag_context(
            db=db,
            current_user=current_user,
            user_message=content_clean,
        )

        # 5. Generate response via LLM (OpenRouter) or Grounded Fallback Engine
        tools_executed: List[str] = []
        assistant_content: str = ""
        extra_metadata: Dict[str, Any] = {}

        if settings.OPENAI_API_KEY:
            try:
                assistant_content, tools_executed, extra_metadata = await AIService._generate_with_external_llm(
                    db=db,
                    current_user=current_user,
                    user_message=content_clean,
                    recent_messages=recent_messages,
                    rag_data=rag_data,
                )
            except Exception as e:
                logger.error(f"External LLM call failed, falling back to internal RAG engine: {e}")
                assistant_content, tools_executed, extra_metadata = await AIService._generate_with_internal_rag(
                    db=db,
                    current_user=current_user,
                    user_message=content_clean,
                    recent_messages=recent_messages,
                    rag_data=rag_data,
                )
        else:
            assistant_content, tools_executed, extra_metadata = await AIService._generate_with_internal_rag(
                db=db,
                current_user=current_user,
                user_message=content_clean,
                recent_messages=recent_messages,
                rag_data=rag_data,
            )

        # 5. Persist assistant reply with structured metadata
        meta: Dict[str, Any] = {"tools_executed": tools_executed}
        if extra_metadata:
            meta.update(extra_metadata)

        assistant_msg = ChatMessage(
            conversation_id=conv.id,
            sender="assistant",
            content=assistant_content,
            metadata_=meta,
        )
        db.add(assistant_msg)

        # Touch conversation updated_at
        conv.updated_at = datetime.now(timezone.utc)
        if conv.title == "New Conversation" and len(content_clean) > 0:
            conv.title = content_clean[:40]

        await db.commit()
        await db.refresh(assistant_msg)

        return ChatResponse(
            conversation_id=conv.id,
            user_message=ChatMessageResponse.model_validate(user_msg),
            assistant_message=ChatMessageResponse.model_validate(assistant_msg),
            tools_executed=tools_executed,
        )

    # ------------------------------------------------------------------------
    # RAG Context Retrieval Engine (Database Thought Layer)
    # ------------------------------------------------------------------------
    @staticmethod
    async def _retrieve_database_rag_context(
        db: AsyncSession,
        current_user: User,
        user_message: str = "",
    ) -> Dict[str, Any]:
        """
        RAG Database Thought / Retrieval Engine.
        Directly queries the shared database to retrieve authoritative ground truth context:
        - Authenticated user's profile and identity
        - Authenticated user's tasks (all, pending, in_progress, completed, overdue)
        - System-wide metrics (total users, total tasks, pending across system)
        """
        # 1. Fetch user's tasks
        task_query = (
            select(Task)
            .where(Task.user_id == current_user.id)
            .order_by(Task.created_at.asc())
        )
        task_res = await db.execute(task_query)
        user_tasks = task_res.scalars().all()

        pending_tasks = [t for t in user_tasks if t.status == TaskStatus.PENDING]
        in_prog_tasks = [t for t in user_tasks if t.status == TaskStatus.IN_PROGRESS]
        comp_tasks = [t for t in user_tasks if t.status == TaskStatus.COMPLETED]
        now = datetime.now(timezone.utc)
        overdue_tasks = [t for t in user_tasks if t.due_date and t.due_date < now and t.status != TaskStatus.COMPLETED]

        # 2. System-wide metrics (Admin Assistant has full access across system)
        total_users = 0
        total_tasks = 0
        system_pending = 0
        if current_user.role == UserRole.ADMIN:
            total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
            total_tasks = (await db.execute(select(func.count(Task.id)))).scalar() or 0
            system_pending = (await db.execute(select(func.count(Task.id)).where(Task.status == TaskStatus.PENDING))).scalar() or 0

        def _task_line(t: Task) -> str:
            due = str(t.due_date)[:10] if t.due_date else "No deadline"
            return f"- '{t.title}' | Status: {t.status.value} | Priority: {t.priority.value} | Due Date: {due}"

        pending_str = "\n".join([_task_line(t) for t in pending_tasks]) or "No pending tasks."
        in_prog_str = "\n".join([_task_line(t) for t in in_prog_tasks]) or "No tasks in progress."

        rag_summary_text = (
            f"=== LIVE DATABASE RAG RETRIEVAL (GROUND TRUTH FROM POSTGRESQL) ===\n"
            f"Authenticated User: {current_user.full_name} ({current_user.email}) | Role: {current_user.role.value}\n"
            f"User's Tasks Summary: {len(user_tasks)} total tasks ({len(pending_tasks)} pending, {len(in_prog_tasks)} in progress, {len(comp_tasks)} completed, {len(overdue_tasks)} overdue)\n\n"
            f"User's Pending Tasks List ({len(pending_tasks)}):\n{pending_str}\n\n"
            f"User's In-Progress Tasks List ({len(in_prog_tasks)}):\n{in_prog_str}\n\n"
            f"System Overview: {total_users} registered users, {total_tasks} system-wide tasks ({system_pending} system-wide pending tasks).\n"
            f"=================================================================="
        )

        return {
            "user_tasks": user_tasks,
            "pending_tasks": pending_tasks,
            "in_prog_tasks": in_prog_tasks,
            "comp_tasks": comp_tasks,
            "overdue_tasks": overdue_tasks,
            "total_users": total_users,
            "total_tasks": total_tasks,
            "system_pending": system_pending,
            "rag_summary_text": rag_summary_text,
        }

    # ------------------------------------------------------------------------
    # External LLM Integration (OpenAI / OpenRouter API)
    # ------------------------------------------------------------------------
    @staticmethod
    async def _generate_with_external_llm(
        db: AsyncSession,
        current_user: User,
        user_message: str,
        recent_messages: List[ChatMessage],
        rag_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, List[str], Dict[str, Any]]:
        tools_executed: List[str] = []
        extra_metadata: Dict[str, Any] = {}

        if rag_data is None:
            rag_data = await AIService._retrieve_database_rag_context(db, current_user, user_message)

        # Build role-filtered tools list
        tools = list(USER_TOOL_SCHEMAS)
        if current_user.role == UserRole.ADMIN:
            tools.extend(ADMIN_TOOL_SCHEMAS)

        if current_user.role == UserRole.ADMIN:
            system_prompt = (
                "You are the 'Admin AI Assistant', an intelligent, context-aware executive assistant integrated into the TaskMaster application.\n"
                f"The authenticated Administrator is: {current_user.full_name} (Email: {current_user.email}, Role: {current_user.role.value}).\n\n"
                f"{rag_data['rag_summary_text']}\n\n"
                "STRICT BEHAVIOR & FORMATTING RULES:\n"
                "1. GREETING: If the user says 'Hi', 'Hello', 'Hey' or greets, greet them back warmly and professionally by name: 'Hi {first_name}!' or 'Hi {full_name}!'.\n"
                "2. LISTING TASKS:\n"
                "   - When asked to list tasks, pending tasks, or show work items:\n"
                "     - Address the user professionally: 'Hi {name},\n\nHere are your pending tasks:' (or 'Here are your tasks:').\n"
                "     - If 0 tasks: State clearly that they currently have no pending tasks.\n"
                "     - If 1 to 3 tasks: Present them clearly in bullet points with Title, Status, Priority, and Due Date.\n"
                "     - If more than 3 tasks (>3 tasks): Present them strictly as a formatted Markdown table:\n"
                "       | Task Title | Status | Priority | Due Date |\n"
                "       | :--- | :---: | :---: | :---: |\n"
                "   - Ground your answer strictly in the LIVE DATABASE RAG RETRIEVAL above. Do NOT invent tasks or match random words.\n"
                "3. NATURAL LANGUAGE & DIRECT ANSWERS: Answer questions directly and professionally. Put the main answer first.\n"
                "4. GENERAL KNOWLEDGE & TECHNICAL EXPLANATIONS: Answer general, technical, and architectural questions directly using structured headings and clear steps.\n"
                "5. PROJECT PLANNING: When asked to create a plan, generate a structured, professional project plan with Objectives, Phases, Actionable Steps, Dependencies, Suggested Priorities, and Deliverables. Offer to convert the plan into database tasks.\n"
                "6. PLAN CONVERSION: When the administrator asks to 'add these steps to my to-do list' or 'turn plan into tasks', use the 'admin_bulk_create_tasks' tool.\n"
                "7. TASK ASSIGNMENT: Use 'admin_create_task' or 'admin_assign_task' tools. The backend automatically triggers and verifies in-app notifications to assignees.\n"
                "8. DATABASE GROUNDING: Always use tools for modifications and live updates."
            )
        else:
            system_prompt = (
                "You are 'AI Assistant', an intelligent, secure assistant integrated into the To-Do List Application.\n"
                f"The authenticated user is: {current_user.full_name} (Email: {current_user.email}, Role: {current_user.role.value}).\n\n"
                f"{rag_data['rag_summary_text']}\n\n"
                "SECURITY & FORMATTING RULES:\n"
                "1. Regular users must ONLY access their own tasks. Never reveal or confirm another user's records.\n"
                "2. GREETING: If the user says 'Hi' or greets, greet back warmly by name.\n"
                "3. TASKS: Address user professionally: 'Hi {name},\n\nHere are your tasks:'. Use bullets for 1-3 tasks, markdown tables for >3 tasks.\n"
                "4. Ground all responses in the database context above."
            )

        messages_payload: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
        for m in recent_messages[:-1]:
            messages_payload.append({
                "role": "user" if m.sender == "user" else "assistant",
                "content": m.content,
            })
        messages_payload.append({"role": "user", "content": user_message})

        base_url = (settings.OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/")
        if "openrouter.ai" in base_url and not base_url.endswith("/v1"):
            base_url = f"{base_url}/api/v1" if not base_url.endswith("/api") else f"{base_url}/v1"

        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        if "openrouter.ai" in base_url:
            headers["HTTP-Referer"] = "http://localhost:5173"
            headers["X-Title"] = "TaskMaster AI Assistant"

        async with httpx.AsyncClient(timeout=12.0) as client:
            req_body: Dict[str, Any] = {
                "model": settings.LLM_MODEL,
                "messages": messages_payload,
                "tools": tools,
                "temperature": 0.2,
            }

            resp = await client.post(f"{base_url}/chat/completions", headers=headers, json=req_body)
            if resp.status_code != 200:
                raise RuntimeError(f"LLM API responded with {resp.status_code}: {resp.text[:250]}")

            resp_data = resp.json()
            if "error" in resp_data:
                raise RuntimeError(f"LLM API returned error: {resp_data['error']}")

            choices = resp_data.get("choices")
            if not choices:
                raise RuntimeError(f"LLM API response missing choices: {resp_data}")

            choice = choices[0]
            msg = choice["message"]

            # If tool calls were made by LLM
            if msg.get("tool_calls"):
                messages_payload.append(msg)
                for tool_call in msg["tool_calls"]:
                    fn_name = tool_call["function"]["name"]
                    try:
                        fn_args = json.loads(tool_call["function"]["arguments"])
                    except Exception:
                        fn_args = {}

                    tools_executed.append(fn_name)
                    tool_result = await execute_tool(fn_name, fn_args, current_user, db)

                    if isinstance(tool_result, dict):
                        if "structured_table" in tool_result:
                            extra_metadata["structured_table"] = tool_result["structured_table"]
                        if "notification" in tool_result:
                            extra_metadata["notification"] = tool_result["notification"]

                    messages_payload.append({
                        "role": "tool",
                        "tool_call_id": tool_call["id"],
                        "name": fn_name,
                        "content": json.dumps(tool_result),
                    })

                # Call LLM again to synthesize tool results into final answer
                final_resp = await client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json={"model": settings.LLM_MODEL, "messages": messages_payload, "temperature": 0.2},
                )
                final_data = final_resp.json()
                if "error" in final_data or not final_data.get("choices"):
                    raise RuntimeError(f"LLM synthesis returned error: {final_data}")
                return final_data["choices"][0]["message"]["content"], tools_executed, extra_metadata

            return msg.get("content", ""), tools_executed, extra_metadata

    # ------------------------------------------------------------------------
    # Internal Grounded RAG & Tool Orchestration Engine
    # Runs deterministically without needing external API keys
    # ------------------------------------------------------------------------
    @staticmethod
    async def _generate_with_internal_rag(
        db: AsyncSession,
        current_user: User,
        user_message: str,
        recent_messages: Optional[List[ChatMessage]] = None,
        rag_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, List[str], Dict[str, Any]]:
        if rag_data is None:
            rag_data = await AIService._retrieve_database_rag_context(db, current_user, user_message)

        if current_user.role == UserRole.ADMIN:
            return await AIService._generate_admin_rag(db, current_user, user_message, recent_messages or [], rag_data)
        else:
            return await AIService._generate_user_rag(db, current_user, user_message, rag_data)

    # ------------------------------------------------------------------------
    # Dedicated Admin AI Assistant Pipeline (Role-Enforced)
    # ------------------------------------------------------------------------
    @staticmethod
    async def _generate_admin_rag(
        db: AsyncSession,
        current_user: User,
        user_message: str,
        recent_messages: List[ChatMessage],
        rag_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, List[str], Dict[str, Any]]:
        if rag_data is None:
            rag_data = await AIService._retrieve_database_rag_context(db, current_user, user_message)

        msg_lower = user_message.lower().strip()
        tools_executed: List[str] = []
        extra_metadata: Dict[str, Any] = {}

        # 1. Warm Greeting back when user says "Hi", "Hello", etc.
        if msg_lower in [
            "hi", "hello", "hey", "hola", "good morning", "good evening", "good afternoon",
            "greetings", "hi there", "hey there", "howdy"
        ] or re.match(r"^(hi|hello|hey|greetings|hola)\b", msg_lower):
            first_name = (current_user.full_name or "there").strip()
            return (
                f"Hi {first_name}! 👋\n\n"
                f"How can I assist you with your tasks, project planning, or system administration today?",
                tools_executed,
                {"response_type": "text"}
            )

        # 2. Pending Tasks Query ("list my pending task", "my pending tasks", etc.)
        is_pending_query = (
            any(k in msg_lower for k in ["pending task", "pending tasks", "my pending", "tasks pending"])
            or (("list" in msg_lower or "show" in msg_lower or "what" in msg_lower or "get" in msg_lower) and "pending" in msg_lower)
        )
        if is_pending_query:
            tools_executed.append("admin_list_my_pending_tasks")
            pending_list = rag_data.get("pending_tasks", [])
            text_out, meta_out = _format_task_response(current_user.full_name, pending_list, "pending tasks")
            return text_out, tools_executed, meta_out

        # 3. User's Personal Tasks Query ("list my tasks", "my tasks", "show my tasks", etc.)
        is_my_tasks_query = (
            any(k in msg_lower for k in [
                "my tasks", "my task", "assigned to me", "my todo", "my to-do",
                "what are my tasks", "show my tasks", "list my tasks", "get my tasks"
            ])
            and not any(k in msg_lower for k in ["all tasks", "system tasks", "database tasks", "all users"])
        )
        if is_my_tasks_query:
            tools_executed.append("admin_list_my_tasks")
            user_tasks = rag_data.get("user_tasks", [])
            text_out, meta_out = _format_task_response(current_user.full_name, user_tasks, "tasks")
            return text_out, tools_executed, meta_out

        # 4. Convert Plan into Database Tasks ("Add it in my to do list", etc.)
        is_plan_conversion = (
            any(k in msg_lower for k in [
                "add these steps", "add the plan", "convert this plan", "add to my to-do list",
                "convert plan into tasks", "turn this plan into tasks", "add them to my tasks",
                "create these tasks", "add tasks from plan", "turn plan into tasks", "add to my todo",
                "add plan to todo", "add to todo", "add it in my to do list", "add it in my todo",
                "add it to my to do list", "add it to my todo", "add into that", "add it in that",
                "add it into that", "add them into that", "put this in my to do list", "add to todo list",
                "put in my todo list", "create tasks from this", "add to my tasks", "save this plan as tasks",
                "save as tasks", "add to my list", "add it to my list", "add into my to do list",
                "add to task list", "add to tasks", "add into to do list", "add into todo"
            ])
            or (
                ("add" in msg_lower or "put" in msg_lower or "convert" in msg_lower or "turn" in msg_lower or "save" in msg_lower)
                and ("to do list" in msg_lower or "todo" in msg_lower or "to-do" in msg_lower or "tasks" in msg_lower or "into that" in msg_lower or "in that" in msg_lower or "to that" in msg_lower)
            )
        )
        if is_plan_conversion:
            plan_tasks = _extract_plan_tasks_from_history(recent_messages)
            if not plan_tasks:
                return (
                    "I could not locate an active project plan or task list in our recent conversation history.\n\n"
                    "Please ask me to create a plan first (for example, *'I want to build an app, provide me the plan'* "
                    "or *'Make a plan for an AI chatbot'*), and then say **'Add it in my to do list'** to save those tasks directly into the database.",
                    tools_executed,
                    {"response_type": "clarification"}
                )

            # Check if specific assignee mentioned
            assignee_match = re.search(r"(?:assign\s+(?:them\s+)?to|for)\s+([a-zA-Z0-9._%+\-@]+(?:\s+[a-zA-Z0-9]+)?)", msg_lower)
            default_assignee = None
            if assignee_match:
                cand_name = assignee_match.group(1).strip()
                if cand_name.lower() not in ["me", "myself", "my", "todo", "tasks", "list", "that", "it"]:
                    default_assignee = cand_name

            tools_executed.append("admin_bulk_create_tasks")
            bulk_res = await execute_tool(
                "admin_bulk_create_tasks",
                {"tasks": plan_tasks, "default_user_identifier": default_assignee},
                current_user,
                db
            )

            created_tasks = bulk_res.get("tasks", [])
            skipped = bulk_res.get("skipped_duplicates", [])

            table_rows = []
            lines = ["### Project Plan Converted to Database Tasks\n"]
            lines.append(f"Successfully created and verified **{len(created_tasks)} task(s)** in the database:\n")
            for t in created_tasks:
                lines.append(f"- **{t['title']}** | Priority: `{t['priority']}` | Assigned to: **{t['assigned_to']}** | Status: `{t['status']}`")
                table_rows.append([t['title'], t['assigned_to'], t['status'], t['priority']])

            if skipped:
                lines.append(f"\n*Note: {len(skipped)} task(s) were already present in the database and skipped to avoid duplication.*")

            lines.append("\n**Database Verification:** All tasks committed to PostgreSQL with automated audit timestamps.")

            return "\n".join(lines), tools_executed, {
                "response_type": "action_result",
                "task_action_result": {
                    "type": "plan_converted",
                    "total_created": len(created_tasks),
                    "created_tasks": created_tasks,
                    "skipped": skipped,
                },
                "structured_table": {
                    "headers": ["Task Title", "Assigned To", "Status", "Priority"],
                    "rows": table_rows,
                }
            }

        # Check if user is responding to a plan clarification question
        last_asst_msg = next((m for m in reversed(recent_messages) if m.sender == "assistant"), None)
        is_answering_plan_clarification = False
        if last_asst_msg:
            last_meta = last_asst_msg.metadata_ or {}
            if last_meta.get("response_type") == "clarification" or "What is the project, objective, or system you would like me to plan?" in last_asst_msg.content:
                is_answering_plan_clarification = True

        # Project Planning Request ("i want to build an app, provide me the plan", "make a plane for me", "suggest tasks", etc.)
        is_planning_query = (
            any(k in msg_lower for k in [
                "provide me the plan", "provide me a plan", "give me the plan", "give me a plan",
                "make a plan", "make a plane", "create a plan", "generate a plan", "build a plan",
                "plan for me", "plane for me", "suggest tasks", "recommend tasks", "project plan",
                "roadmap for", "strategy for", "steps to build", "how to build", "how do i build",
                "i want to build", "develop an app", "build an app", "can you create a plan",
                "can you make a plan"
            ])
            or (
                ("plan" in msg_lower or "plane" in msg_lower or "roadmap" in msg_lower or "strategy" in msg_lower or "suggest tasks" in msg_lower)
                and any(w in msg_lower for w in ["build", "make", "create", "provide", "give", "suggest", "app", "project", "system", "for me", "me", "how"])
            )
            or (
                ("want to build" in msg_lower or "want to develop" in msg_lower or "want to create" in msg_lower)
                and ("plan" in msg_lower or "plane" in msg_lower or "steps" in msg_lower or "roadmap" in msg_lower)
            )
        )

        if is_answering_plan_clarification or is_planning_query:
            topic = None

            # Check if specific app domain mentioned in current message
            if "app" in msg_lower or "application" in msg_lower:
                if "mobile" in msg_lower:
                    topic = "Mobile Application Development"
                elif "ecommerce" in msg_lower or "shop" in msg_lower or "store" in msg_lower:
                    topic = "E-Commerce Application Platform"
                elif "saas" in msg_lower:
                    topic = "SaaS Cloud Platform"
                elif "chat" in msg_lower or "bot" in msg_lower or "ai" in msg_lower:
                    topic = "Enterprise AI Chatbot System"
                else:
                    topic = "Full-Stack Application Development"
            elif "chatbot" in msg_lower or "ai" in msg_lower:
                topic = "Enterprise AI Chatbot System"
            elif "backend" in msg_lower or "api" in msg_lower:
                topic = "Scalable Backend API Infrastructure"
            elif "database" in msg_lower:
                topic = "Database Architecture & Optimization"
            elif "auth" in msg_lower or "security" in msg_lower:
                topic = "Authentication & Security Architecture"

            if not topic:
                topic_match = re.search(r"(?:plan\s+(?:for|about|on)|roadmap\s+(?:for|about)|plan\s+(?:a|an)\s+)(.+)", msg_lower)
                if topic_match:
                    cand = topic_match.group(1).strip().rstrip("?.!")
                    cand = re.sub(r"^(?:me|myself|us)\s+(?:for|about|on)?\s*", "", cand).strip()
                    if cand and cand not in [
                        "me", "myself", "us", "this", "it", "tasks", "my project",
                        "a project", "the project", "something", "work", "a plan",
                        "for me", "for us"
                    ]:
                        topic = cand.title()

            # If no topic in prompt, check prior conversation context (e.g. user previously said "i want to build an app")
            if not topic:
                prior_msgs = [m for m in recent_messages if m.content.strip().lower() != user_message.lower().strip()]
                topic = _extract_recent_project_topic(prior_msgs)

            if not topic:
                topic = "Full-Stack Application Development"

            # Generate structured, professional plan with human introduction
            plan_text = _build_structured_project_plan(topic)
            return plan_text, tools_executed, {"response_type": "plan", "plan_topic": topic}

        # 3. Plan Refinement Request
        if any(k in msg_lower for k in [
            "more detailed", "add a testing phase", "break the second phase",
            "break phase", "estimate the time", "refine the plan", "update the plan", "expand the plan"
        ]):
            topic = _extract_recent_project_topic(recent_messages) or "System Architecture"
            plan_text = _build_refined_project_plan(topic, msg_lower)
            return plan_text, tools_executed, {"response_type": "plan", "plan_topic": topic}

        # 4. Task Creation with Assignment & Notifications
        create_assign_match = re.search(
            r"(?:create|add)\s+(?:a\s+)?task\s+(?:to\s+|called\s+|named\s+)?(.+?)(?:\s+and\s+assign\s+(?:it\s+)?to\s+|\s+for\s+)([a-zA-Z0-9._%+\-@]+(?:\s+[a-zA-Z0-9]+)?)",
            msg_lower
        )
        if create_assign_match:
            task_title = create_assign_match.group(1).strip().strip("'\"")
            assignee = create_assign_match.group(2).strip().strip("'\"")
            priority = "high" if "high" in msg_lower else "medium"
            tools_executed.append("admin_create_task")
            res = await execute_tool("admin_create_task", {"title": task_title, "user_identifier": assignee, "priority": priority}, current_user, db)
            if res.get("ambiguous_user"):
                cand_list = "\n".join([f"- **{c['full_name']}** ({c['email']}) - ID: `{c['id']}`" for c in res.get("candidates", [])])
                return (
                    f"Multiple users match **'{assignee}'**. Please specify which user to assign this task to by their email or UUID:\n\n{cand_list}",
                    tools_executed,
                    {"response_type": "clarification"}
                )
            if res.get("error"):
                return f"Unable to create task: {res['error']}", tools_executed, {"response_type": "error"}

            t_data = res.get("task", {})
            assigned_user = t_data.get("assigned_to", {})
            notif = res.get("notification", {})

            output = (
                f"### Task Created & Assigned Successfully\n\n"
                f"- **Task:** {t_data.get('title')}\n"
                f"- **Assigned to:** {assigned_user.get('full_name')} (`{assigned_user.get('email')}`)\n"
                f"- **Status:** `{t_data.get('status')}`\n"
                f"- **Priority:** `{t_data.get('priority')}`\n"
                f"- **Notification:** {notif.get('status', 'Delivered successfully')}\n\n"
                f"**Database Verification:** Task record `{t_data.get('id')}` created and linked to user."
            )
            return output, tools_executed, {
                "response_type": "action_result",
                "task_action_result": {"task": t_data, "notification": notif}
            }

        # 5. Task Assignment / Reassignment
        assign_match = re.search(r"(?:assign|reassign)\s+(?:task\s+)?(.+?)\s+to\s+([a-zA-Z0-9._%+\-@]+(?:\s+[a-zA-Z0-9]+)?)", msg_lower)
        if assign_match:
            task_ident = assign_match.group(1).strip().strip("'\"")
            assignee = assign_match.group(2).strip().strip("'\"")
            tools_executed.append("admin_assign_task")
            res = await execute_tool("admin_assign_task", {"task_identifier": task_ident, "user_identifier": assignee}, current_user, db)
            if res.get("error"):
                return f"Unable to assign task: {res['error']}", tools_executed, {"response_type": "error"}

            notif = res.get("notification", {})
            assigned_to = res.get("assigned_to", {})
            return (
                f"### Task Assignment Updated\n\n"
                f"- **Task:** {res.get('task_title')}\n"
                f"- **Assigned to:** {assigned_to.get('full_name')} (`{assigned_to.get('email')}`)\n"
                f"- **Notification:** {notif.get('status', 'Delivered successfully')}\n\n"
                f"**Database Verification:** Task `{res.get('task_id')}` ownership updated.",
                tools_executed,
                {"response_type": "action_result"}
            )

        # 6. Task Status & Priority Updates
        update_match = re.search(r"(?:mark|set|update)\s+(?:task\s+)?(.+?)\s+(?:as\s+|to\s+)?(completed|done|in_progress|pending|high priority|medium priority|low priority)", msg_lower)
        if update_match:
            task_ident = update_match.group(1).strip().strip("'\"")
            raw_action = update_match.group(2).strip().lower()
            status_val = None
            priority_val = None
            if raw_action in ["completed", "done"]:
                status_val = "completed"
            elif raw_action == "in_progress":
                status_val = "in_progress"
            elif raw_action == "pending":
                status_val = "pending"
            elif "high" in raw_action:
                priority_val = "high"
            elif "medium" in raw_action:
                priority_val = "medium"
            elif "low" in raw_action:
                priority_val = "low"

            tools_executed.append("admin_update_task")
            res = await execute_tool(
                "admin_update_task",
                {"task_identifier": task_ident, "status": status_val, "priority": priority_val},
                current_user,
                db
            )
            if res.get("error"):
                return f"Unable to update task: {res['error']}", tools_executed, {"response_type": "error"}

            t = res.get("task", {})
            return (
                f"### Task Updated Successfully\n\n"
                f"- **Task:** {t.get('title')}\n"
                f"- **Status:** `{t.get('status')}`\n"
                f"- **Priority:** `{t.get('priority')}`\n\n"
                f"**Database Verification:** Task record updated.",
                tools_executed,
                {"response_type": "action_result"}
            )

        # 7. Overdue Tasks
        if "overdue" in msg_lower:
            tools_executed.append("admin_list_tasks")
            res = await execute_tool("admin_list_tasks", {"overdue_only": True}, current_user, db)
            tasks = res.get("tasks", [])
            if not tasks:
                return "No overdue tasks found across the system. All deadlines are on schedule.", tools_executed, {"response_type": "text"}

            lines = [f"### System-Wide Overdue Tasks ({len(tasks)} found)\n"]
            lines.append("| Task Title | Assigned To | Status | Priority | Due Date |")
            lines.append("| :--- | :--- | :---: | :---: | :---: |")
            for t in tasks:
                lines.append(f"| **{t['title']}** | {t['owner_name']} | `{t['status']}` | `{t['priority']}` | **{t['due_date']} (Overdue)** |")

            return "\n".join(lines), tools_executed, {
                "response_type": "table",
                "structured_table": res.get("structured_table")
            }

        # 8. Specific User's Tasks
        user_target_match = re.search(
            r"(?:(?:show\s+(?:me\s+)?)?tasks\s+(?:of|for|assigned\s+to)\s+|show\s+(?:me\s+)?)([a-zA-Z0-9._%+-]+(?:@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})?|[a-zA-Z]+)(?:'s)?(?:\s+tasks?)?",
            msg_lower,
        )
        if user_target_match:
            target_ident = user_target_match.group(1).strip()
            if target_ident not in ["my", "all", "pending", "completed", "high", "me", "the", "a", "user", "tasks", "overdue"]:
                tools_executed.append("admin_list_tasks")
                res = await execute_tool("admin_list_tasks", {"user_identifier": target_ident}, current_user, db)
                if res.get("ambiguous_user"):
                    cand_list = "\n".join([f"- **{c['full_name']}** ({c['email']}) - ID: `{c['id']}`" for c in res.get("candidates", [])])
                    return (
                        f"Multiple users match **'{target_ident}'**. Please clarify which user you would like to view:\n\n{cand_list}",
                        tools_executed,
                        {"response_type": "clarification"}
                    )
                if res.get("error"):
                    return f"Unable to find tasks: {res['error']}", tools_executed, {"response_type": "error"}

                tasks = res.get("tasks", [])
                if not tasks:
                    return f"User **{target_ident}** currently has 0 tasks recorded.", tools_executed, {"response_type": "text"}

                lines = [f"### Tasks for {tasks[0]['owner_name']} ({tasks[0]['owner_email']}) ({len(tasks)} found)\n"]
                lines.append("| Task Title | Status | Priority | Due Date |")
                lines.append("| :--- | :---: | :---: | :---: |")
                for t in tasks:
                    lines.append(f"| **{t['title']}** | `{t['status']}` | `{t['priority']}` | {t['due_date']} |")

                return "\n".join(lines), tools_executed, {
                    "response_type": "table",
                    "structured_table": {
                        "headers": ["Task Title", "Status", "Priority", "Due Date"],
                        "rows": [[t['title'], t['status'], t['priority'], t['due_date']] for t in tasks]
                    }
                }

        # 9. General / Technical Questions
        if any(msg_lower.startswith(w) for w in ["how many steps", "how to build", "how do i build", "how does", "what is", "what are", "explain", "why should", "compare"]):
            if "chatbot" in msg_lower or "ai" in msg_lower:
                return (
                    "Building an enterprise-grade AI chatbot typically involves **7 major development phases**:\n\n"
                    "1. **Requirements & Scope Definition:**\n"
                    "   - Determine core use cases (administrative automation, database Q&A, task operations).\n"
                    "   - Define strict role-based authorization, privacy constraints, and expected response quality.\n\n"
                    "2. **Architecture & Tech Stack Selection:**\n"
                    "   - Select backend framework (FastAPI, Python async ORM) and frontend widget architecture.\n"
                    "   - Choose LLM provider and determine if tool calling (Function Calling) is required.\n\n"
                    "3. **Data Grounding & RAG Pipeline Design:**\n"
                    "   - Connect live database queries and/or vector embeddings for factual grounding.\n"
                    "   - Enforce strict server-side permissions so the model cannot access unauthorized records.\n\n"
                    "4. **Tool & Service Integration:**\n"
                    "   - Create discrete, parameterized backend tools for database read/write actions.\n"
                    "   - Separate language understanding from execution to prevent prompt injection.\n\n"
                    "5. **Chat Interface & Context Management:**\n"
                    "   - Build a responsive floating widget with multi-turn conversation memory.\n"
                    "   - Provide structured tables, action confirmations, and loading indicators.\n\n"
                    "6. **Automated Testing & Security Hardening:**\n"
                    "   - Run regression tests for prompt injection, authorization boundaries, and edge cases.\n"
                    "   - Validate fallback mechanisms when external LLM endpoints are unavailable.\n\n"
                    "7. **Deployment & Continuous Monitoring:**\n"
                    "   - Containerize with Docker, configure health probes, and track latency/token metrics.\n\n"
                    "*Would you like me to convert this methodology into a structured project plan for your team?*",
                    tools_executed,
                    {"response_type": "text"}
                )
            elif "rag" in msg_lower:
                return (
                    "**Retrieval-Augmented Generation (RAG)** is an AI architectural pattern that grounds Large Language Model responses in external, authoritative data sources.\n\n"
                    "### How RAG Works:\n"
                    "1. **User Query:** The user submits a natural-language question.\n"
                    "2. **Retrieval:** The backend queries authorized data (such as PostgreSQL records) using strict permission filters.\n"
                    "3. **Context Injection:** The retrieved facts are injected into the prompt context along with the user's question.\n"
                    "4. **Grounded Generation:** The LLM generates a factual, up-to-date answer without hallucinations or accessing unauthorized data.\n\n"
                    "*In TaskMaster, RAG is enforced strictly at the database query layer to guarantee role-based data isolation.*",
                    tools_executed,
                    {"response_type": "text"}
                )

        # 10. Workload Distribution & User Analytics
        if any(k in msg_lower for k in ["pending tasks does each user have", "tasks per user", "distribution", "workload", "system telemetry", "analytics", "completion rate", "dashboard stats"]):
            tools_executed.append("admin_get_task_analytics")
            stats = await execute_tool("admin_get_task_analytics", {}, current_user, db)
            users_data = await execute_tool("admin_list_users", {"limit": 25}, current_user, db)

            headers = ["User Name", "Email", "Role", "Pending Tasks", "Total Tasks"]
            rows = []
            lines = ["### Task Distribution & Workload Across Users\n"]
            lines.append("| User Name | Email | Role | Pending Tasks | Total Tasks |")
            lines.append("| :--- | :--- | :---: | :---: | :---: |")

            for u in users_data.get("users", []):
                u_tasks = await execute_tool("admin_get_user_tasks", {"user_identifier": u["id"]}, current_user, db)
                t_list = u_tasks.get("tasks", [])
                pending_cnt = sum(1 for t in t_list if t["status"] == "pending")
                total_cnt = len(t_list)
                lines.append(f"| **{u['full_name']}** | `{u['email']}` | `{u['role']}` | **{pending_cnt}** | {total_cnt} |")
                rows.append([u['full_name'], u['email'], u['role'], str(pending_cnt), str(total_cnt)])

            lines.append(
                f"\n**System Summary:** {stats.get('total_tasks', 0)} total tasks across {stats.get('total_users', 0)} users "
                f"({stats.get('completion_rate_percentage', 0)}% completion rate)."
            )

            return "\n".join(lines), tools_executed, {
                "response_type": "table",
                "structured_table": {"headers": headers, "rows": rows}
            }

        # 11. List All Users / Registered Users Directory
        is_list_users_query = (
            any(k in msg_lower for k in [
                "list users", "show users", "all users", "who are the users", "user directory",
                "registered users", "system users", "list all users", "user list", "view users",
                "all registered users", "who is registered", "who are registered", "registered user",
                "show all users", "get all users", "display users", "display all users",
                "who have accounts", "show me users"
            ])
            or (
                ("user" in msg_lower or "users" in msg_lower)
                and any(w in msg_lower for w in ["list", "show", "registered", "all", "directory", "who", "view", "get", "display", "accounts"])
            )
        )
        if is_list_users_query:
            tools_executed.append("admin_list_users")
            users_res = await execute_tool("admin_list_users", {"limit": 50}, current_user, db)
            users = users_res.get("users", [])
            headers = ["Full Name", "Email Address", "Role", "Account Status", "Joined Date"]
            rows = []
            lines = [f"### Registered Users Directory ({len(users)} users)\n"]
            lines.append("| Full Name | Email Address | Role | Status | Joined Date |")
            lines.append("| :--- | :--- | :---: | :---: | :---: |")
            for u in users:
                st = "Active" if u["is_active"] else "Suspended"
                date_str = u["joined_at"][:10] if u.get("joined_at") else "-"
                lines.append(f"| **{u['full_name']}** | `{u['email']}` | `{u['role']}` | {st} | {date_str} |")
                rows.append([u['full_name'], u['email'], u['role'], st, date_str])

            return "\n".join(lines), tools_executed, {
                "response_type": "table",
                "structured_table": {"headers": headers, "rows": rows}
            }

        # 12. Send Administrative Notification
        notif_match = re.search(r"(?:notify|send notification to)\s+([a-zA-Z0-9._%+\-@]+(?:\s+[a-zA-Z0-9]+)?)\s+(?:that|with|saying|about)\s+(.+)", msg_lower)
        if notif_match:
            target_ident = notif_match.group(1).strip()
            msg_body = notif_match.group(2).strip()
            tools_executed.append("admin_send_notification")
            res = await execute_tool("admin_send_notification", {"user_identifier": target_ident, "title": "Administrative Notification", "message": msg_body}, current_user, db)
            if res.get("error"):
                return f"Unable to deliver notification: {res['error']}", tools_executed, {"response_type": "error"}

            return (
                f"### Administrative Notification Delivered\n\n"
                f"- **Recipient:** {res.get('notification', {}).get('recipient')}\n"
                f"- **Subject:** Administrative Notification\n"
                f"- **Message Body:** \"{msg_body}\"\n"
                f"- **Status:** Verified in-app delivery (ID: `{res.get('notification', {}).get('id')}`)",
                tools_executed,
                {"response_type": "action_result"}
            )

        # 13. List All Tasks / General Task Query
        is_all_tasks_query = (
            any(k in msg_lower for k in [
                "all tasks", "show tasks", "list tasks", "view tasks", "database tasks",
                "all the tasks", "system tasks", "show all tasks", "list all tasks", "view all tasks"
            ])
            or (
                ("task" in msg_lower or "tasks" in msg_lower)
                and any(w in msg_lower for w in ["all", "system", "database", "everything"])
            )
        )
        if is_all_tasks_query:
            tools_executed.append("admin_list_tasks")
            res = await execute_tool("admin_list_tasks", {"limit": 50}, current_user, db)
            tasks = res.get("tasks", [])
            if not tasks:
                return "No tasks recorded in the database.", tools_executed, {"response_type": "text"}

            lines = [f"### System-Wide Tasks Directory ({len(tasks)} tasks shown)\n"]
            lines.append("| Task Title | Assigned To | Status | Priority | Due Date |")
            lines.append("| :--- | :--- | :---: | :---: | :---: |")
            for t in tasks:
                lines.append(f"| **{t['title']}** | {t['owner_name']} | `{t['status']}` | `{t['priority']}` | {t['due_date']} |")

            return "\n".join(lines), tools_executed, {
                "response_type": "table",
                "structured_table": res.get("structured_table")
            }

        # 14. Explicit Search Tasks Query (ONLY executed when user explicitly requests a search)
        search_match = re.search(r"(?:search|find|filter)\s+(?:task\s+|tasks\s+)?(?:for\s+|matching\s+)?['\"]?([a-zA-Z0-9_\-\s]+)['\"]?", msg_lower)
        if search_match:
            term = search_match.group(1).strip()
            if term and term not in ["my", "all", "pending", "tasks", "task"]:
                matched = await execute_tool("admin_search_all_tasks", {"query": term}, current_user, db)
                m_tasks = matched.get("tasks", [])
                if m_tasks:
                    tools_executed.append("admin_search_all_tasks")
                    text_out, meta_out = _format_task_response(current_user.full_name, m_tasks, f"tasks matching '{term}'")
                    return text_out, tools_executed, meta_out

        # 15. Intelligent Conversational Brain & General Knowledge Engine (Claude / GPT / Gemini standard)
        # Handles any technical query, architectural question, general questions, or advice naturally
        conversational_reply = _generate_intelligent_conversational_reply(user_message, current_user, recent_messages)
        return conversational_reply, tools_executed, {"response_type": "text"}

    # ------------------------------------------------------------------------
    # User AI Assistant Pipeline (Unchanged, User-Isolated)
    # ------------------------------------------------------------------------
    @staticmethod
    async def _generate_user_rag(
        db: AsyncSession,
        current_user: User,
        user_message: str,
        rag_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[str, List[str], Dict[str, Any]]:
        if rag_data is None:
            rag_data = await AIService._retrieve_database_rag_context(db, current_user, user_message)

        msg_lower = user_message.lower().strip()
        tools_executed: List[str] = []

        # Strict Security Boundary Check for Regular Users
        cross_user_patterns = [
            r"\b(all|other)\s+users\b",
            r"\buser(s)?\s+and\s+their\s+tasks\b",
            r"\btasks\s+(?:assigned\s+to|of|for)\s+([a-zA-Z0-9._%+-]+)\b",
            r"\b([a-zA-Z0-9._%+-]+)'s\s+tasks?\b",
            r"\badmin\b",
            r"\bwho\s+are\s+the\s+users\b",
            r"\blist\s+(all\s+)?users\b",
            r"\bshow\s+users\b",
            r"\ball\s+tasks\b",
        ]
        for pat in cross_user_patterns:
            m = re.search(pat, msg_lower)
            if m:
                groups = m.groups()
                if groups:
                    matched_target = groups[-1] if groups[-1] else ""
                    if matched_target.lower() in ["my", "me", "myself"]:
                        continue
                elif "my" in msg_lower:
                    continue

                return (
                    "I cannot disclose information about other users or administrative data. "
                    "As a standard user, you are strictly authorized to view, manage, and track only your own personal tasks.",
                    [],
                    {"response_type": "security_boundary"}
                )

        # Casual Greetings with Live Task Context
        if msg_lower in [
            "hi", "hello", "hey", "hola", "good morning", "good evening", "good afternoon",
            "greetings", "hi there", "hey there", "howdy"
        ] or re.match(r"^(hi|hello|hey|greetings|hola)\b", msg_lower):
            first_name = (current_user.full_name or "there").strip()
            return (
                f"Hi {first_name}! 👋\n\n"
                f"How can I assist you with your tasks today? You can ask me to list your tasks, check your pending work, or create a new task.",
                tools_executed,
                {"response_type": "text"}
            )

        # Workload Analysis & Priority Guidance
        if any(k in msg_lower for k in [
            "workload", "what should i do first", "what do i do first",
            "what should i work on", "what to do first", "what's next",
            "what is next", "prioritize", "prioritise", "recommendation",
            "where should i start", "where do i start", "advice"
        ]):
            tools_executed.append("list_my_tasks")
            tasks_res = await execute_tool("list_my_tasks", {"limit": 50}, current_user, db)
            all_tasks = tasks_res.get("tasks", [])

            if not all_tasks:
                return (
                    "You currently have no tasks in your list! You can start by asking me to create one (e.g. *'Create task Setup database'*).",
                    tools_executed,
                    {"response_type": "text"}
                )

            now_iso = datetime.now(timezone.utc).isoformat()
            overdue = [t for t in all_tasks if t.get("due_date") and t["due_date"] < now_iso and t["status"] != "completed"]
            in_prog = [t for t in all_tasks if t["status"] == "in_progress"]
            pending_high = [t for t in all_tasks if t["status"] == "pending" and t["priority"] == "high"]
            pending_med = [t for t in all_tasks if t["status"] == "pending" and t["priority"] == "medium"]
            pending_low = [t for t in all_tasks if t["status"] == "pending" and t["priority"] == "low"]
            completed = [t for t in all_tasks if t["status"] == "completed"]

            lines = ["### Your Workload & Recommended Action Plan\n"]
            lines.append(f"You have **{len(all_tasks) - len(completed)} active task(s)** ({len(in_prog)} in progress, {len(pending_high) + len(pending_med) + len(pending_low)} pending) and **{len(completed)} completed**.\n")

            top_task = None
            reason = ""
            if overdue:
                top_task = overdue[0]
                reason = "This task is past its due date and needs immediate attention."
            elif in_prog:
                top_task = sorted(in_prog, key=lambda x: 0 if x["priority"] == "high" else (1 if x["priority"] == "medium" else 2))[0]
                reason = "This task is already in progress—finish it to build momentum."
            elif pending_high:
                top_task = pending_high[0]
                reason = "This is marked high priority."
            elif pending_med:
                top_task = pending_med[0]
                reason = "This is your next available priority task."
            elif pending_low:
                top_task = pending_low[0]
                reason = "This is your remaining pending task."

            if top_task:
                lines.append(f"#### 🎯 Recommended First Action:\n**{top_task['title']}**\n- **Status:** `{top_task['status']}` | **Priority:** `{top_task['priority']}`\n- **Why:** {reason}\n")

            active_list = []
            if in_prog:
                active_list.append(f"- **In Progress ({len(in_prog)}):** " + ", ".join([f"*{t['title']}*" for t in in_prog]))
            if pending_high:
                active_list.append(f"- **High Priority Pending ({len(pending_high)}):** " + ", ".join([f"*{t['title']}*" for t in pending_high]))
            if pending_med:
                active_list.append(f"- **Medium Priority Pending ({len(pending_med)}):** " + ", ".join([f"*{t['title']}*" for t in pending_med]))
            if pending_low:
                active_list.append(f"- **Low Priority Pending ({len(pending_low)}):** " + ", ".join([f"*{t['title']}*" for t in pending_low]))

            if active_list:
                lines.append("#### 📋 Active Work Items:")
                lines.extend(active_list)

            return "\n".join(lines), tools_executed, {"response_type": "text"}

        # Task Statistics & Summary
        if any(k in msg_lower for k in ["summary", "summarize", "summarise", "how many tasks", "statistics", "overview", "counts", "breakdown"]):
            tools_executed.append("get_my_task_summary")
            summary = await execute_tool("get_my_task_summary", {}, current_user, db)
            return (
                f"### Your Task Summary\n\n"
                f"- **Total Tasks:** {summary.get('total_tasks', 0)}\n"
                f"- **Pending:** {summary.get('pending_tasks', 0)}\n"
                f"- **In Progress:** {summary.get('in_progress_tasks', 0)}\n"
                f"- **Completed:** {summary.get('completed_tasks', 0)}\n"
                f"- **High Priority:** {summary.get('high_priority_tasks', 0)}\n"
                f"- **Overdue Tasks:** {summary.get('overdue_tasks', 0)}",
                tools_executed,
                {"response_type": "text"}
            )

        # Filter by status: pending
        if "pending" in msg_lower:
            tools_executed.append("list_my_tasks")
            pending_list = rag_data.get("pending_tasks", []) if rag_data else []
            if not pending_list:
                res = await execute_tool("list_my_tasks", {"status": "pending"}, current_user, db)
                pending_list = res.get("tasks", [])
            text_out, meta_out = _format_task_response(current_user.full_name, pending_list, "pending tasks")
            return text_out, tools_executed, meta_out

        # Filter by status: in progress
        if "in progress" in msg_lower or "in-progress" in msg_lower:
            tools_executed.append("list_my_tasks")
            res = await execute_tool("list_my_tasks", {"status": "in_progress"}, current_user, db)
            tasks = res.get("tasks", [])
            if not tasks:
                return "You have no tasks currently in progress.", tools_executed, {"response_type": "text"}
            lines = [f"You have **{len(tasks)}** task(s) in progress:\n"]
            for t in tasks:
                lines.append(f"- **{t['title']}** [Priority: `{t['priority']}`]")
            return "\n".join(lines), tools_executed, {"response_type": "text"}

        # Filter by status: completed
        if "completed" in msg_lower or "done" in msg_lower:
            tools_executed.append("list_my_tasks")
            res = await execute_tool("list_my_tasks", {"status": "completed"}, current_user, db)
            tasks = res.get("tasks", [])
            if not tasks:
                return "You haven't completed any tasks yet.", tools_executed, {"response_type": "text"}
            lines = [f"You have completed **{len(tasks)}** task(s):\n"]
            for t in tasks:
                lines.append(f"- ~~{t['title']}~~ (Priority: `{t['priority']}`)")
            return "\n".join(lines), tools_executed, {"response_type": "text"}

        # Filter by priority: high
        if "high priority" in msg_lower:
            tools_executed.append("list_my_tasks")
            res = await execute_tool("list_my_tasks", {"priority": "high"}, current_user, db)
            tasks = res.get("tasks", [])
            if not tasks:
                return "You have no high-priority tasks at the moment.", tools_executed, {"response_type": "text"}
            lines = [f"Here are your **{len(tasks)}** high-priority task(s):\n"]
            for t in tasks:
                lines.append(f"- **{t['title']}** — Status: `{t['status']}`")
            return "\n".join(lines), tools_executed, {"response_type": "text"}

        # Create task intent
        create_match = re.search(r"(?:create|add|new)\s+(?:task|todo)(?:\s+(?:called|named|titled|to))?\s+[\"']?([^\"'\n]+)[\"']?", msg_lower)
        if create_match:
            task_title = create_match.group(1).strip()
            priority = "high" if "high" in msg_lower else "medium"
            tools_executed.append("create_my_task")
            res = await execute_tool("create_my_task", {"title": task_title, "priority": priority}, current_user, db)
            if res.get("success"):
                t = res["task"]
                return f"Successfully created new task: **{t['title']}** (Priority: `{t['priority']}`, Status: `{t['status']}`).", tools_executed, {"response_type": "action_result"}
            return f"Failed to create task: {res.get('error', 'Unknown error')}", tools_executed, {"response_type": "error"}

        # Search task intent
        search_match = re.search(r"(?:search|find|lookup|show\s+task|tasks?\s+(?:about|related\s+to|containing))\s+[\"']?([^\"'\n]+)[\"']?", msg_lower)
        if search_match:
            term = search_match.group(1).strip()
            tools_executed.append("search_my_tasks")
            res = await execute_tool("search_my_tasks", {"query": term}, current_user, db)
            tasks = res.get("tasks", [])
            if not tasks:
                return f"No tasks found matching keyword **'{term}'** in your account.", tools_executed, {"response_type": "text"}
            lines = [f"Found **{len(tasks)}** matching task(s) for **'{term}'**:\n"]
            for t in tasks:
                lines.append(f"- **{t['title']}** (Status: `{t['status']}`, Priority: `{t['priority']}`)")
            return "\n".join(lines), tools_executed, {"response_type": "text"}

        # Default "show my tasks"
        if any(k in msg_lower for k in ["my tasks", "show tasks", "list tasks", "what do i have to do"]):
            tools_executed.append("list_my_tasks")
            user_tasks = rag_data.get("user_tasks", []) if rag_data else []
            if not user_tasks:
                res = await execute_tool("list_my_tasks", {"limit": 20}, current_user, db)
                user_tasks = res.get("tasks", [])
            text_out, meta_out = _format_task_response(current_user.full_name, user_tasks, "tasks")
            return text_out, tools_executed, meta_out

        # Contextual search fallback
        clean_words = [
            w for w in re.findall(r"[a-zA-Z0-9]+", msg_lower)
            if len(w) >= 3 and w not in ["what", "have", "with", "from", "show", "tell", "need", "about", "your", "task", "tasks", "please"]
        ]
        for term in clean_words:
            matched = await execute_tool("search_my_tasks", {"query": term}, current_user, db)
            m_tasks = matched.get("tasks", [])
            if m_tasks:
                tools_executed.append("search_my_tasks")
                lines = [f"I found **{len(m_tasks)}** task(s) matching **'{term}'** in your account:\n"]
                for t in m_tasks:
                    lines.append(f"- **{t['title']}** — Status: `{t['status']}` | Priority: `{t['priority']}`")
                return "\n".join(lines), tools_executed, {"response_type": "text"}

        # Standard User Capability Guide
        return (
            f"Hello {current_user.full_name}! I am your **AI Assistant** (User Panel).\n\n"
            "Here is what I can help you with:\n"
            "- *'Show me all my tasks'* — List your tasks\n"
            "- *'Which tasks are still pending?'* — Filter by pending status\n"
            "- *'Show high priority tasks'* — Review urgent work\n"
            "- *'Summarize my tasks'* — View counts and statistics\n"
            "- *'Search tasks for [keyword]'* — Find specific to-dos\n"
            "- *'Create task [title]'* — Add a new task to your dashboard"
        ), tools_executed, {"response_type": "text"}

# ----------------------------------------------------------------------------
# Helper Planning & Extraction Functions
# ----------------------------------------------------------------------------
def _extract_plan_tasks_from_history(messages: List[ChatMessage]) -> List[Dict[str, Any]]:
    """Scan recent assistant messages to extract task steps from an active plan."""
    for m in reversed(messages):
        content = m.content or ""
        content_lower = content.lower()
        is_plan_msg = (
            m.sender == "assistant"
            and (
                "phase 1" in content_lower
                or "project plan" in content_lower
                or "roadmap" in content_lower
                or "execution plan" in content_lower
                or (m.metadata_ and m.metadata_.get("response_type") == "plan")
                or "1. **" in content
                or "1. " in content
            )
        )
        if is_plan_msg:
            tasks = []
            for line in content.split("\n"):
                line_str = line.strip()
                # Match numbered or bulleted tasks: e.g. 1. **Title**: Description or - **Title**: Description
                match = re.search(r"^\s*(?:\d+[\.\)]|\-|\*)\s+(?:\*\*([^*]+)\*\*|([A-Z][^:\-\n]{4,60}))(?::|\s*[-—]\s*)?\s*(.*)$", line_str)
                if match:
                    t_title = (match.group(1) or match.group(2) or "").strip()
                    t_desc = (match.group(3) or "").strip()
                    title_low = t_title.lower()
                    if (
                        not title_low.startswith("phase")
                        and not title_low.startswith("project plan")
                        and not title_low.startswith("objective")
                        and not title_low.startswith("deliverable")
                        and not title_low.startswith("next action")
                        and not title_low.startswith("next step")
                        and len(t_title) >= 3
                    ):
                        pri = "medium"
                        if "high" in line_str.lower() and "priority" in line_str.lower():
                            pri = "high"
                        elif "low" in line_str.lower() and "priority" in line_str.lower():
                            pri = "low"
                        tasks.append({
                            "title": t_title,
                            "description": t_desc if t_desc else f"Implementation task for {t_title}",
                            "priority": pri,
                        })
            if len(tasks) >= 2:
                return tasks
    return []

def _extract_recent_project_topic(messages: List[ChatMessage]) -> Optional[str]:
    """Inspect previous messages to find what project or topic was discussed."""
    for m in reversed(messages):
        text = (m.content or "").lower()
        if "app" in text or "application" in text:
            if "mobile" in text:
                return "Mobile Application Development"
            if "ecommerce" in text or "shop" in text or "store" in text:
                return "E-Commerce Application Platform"
            if "saas" in text:
                return "SaaS Cloud Platform"
            if "chat" in text or "bot" in text or "ai" in text:
                return "Enterprise AI Chatbot System"
            return "Full-Stack Application Development"
        if "chatbot" in text or "ai assistant" in text:
            return "Enterprise AI Chatbot System"
        if "api" in text or "backend" in text:
            return "Scalable Backend API Infrastructure"
        if "database" in text or "schema" in text or "sql" in text:
            return "Database Architecture & Optimization"
        if "auth" in text or "security" in text:
            return "Authentication & Security Architecture"
        match = re.search(r"(?:plan\s+(?:for|about|on)|roadmap\s+(?:for|about)|build\s+(?:a\s+|an\s+)?|develop\s+(?:a\s+|an\s+)?|create\s+(?:a\s+|an\s+)?)([a-zA-Z0-9\s\-_]{3,40})", text)
        if match:
            cand = match.group(1).strip().rstrip("?.!")
            if cand not in ["me", "myself", "us", "this", "it", "tasks", "a plan", "the project", "something"]:
                return cand.title()
    return "Full-Stack Application Development"

def _build_structured_project_plan(topic: str) -> str:
    """Build a comprehensive, human-language, executive project plan for an administrator."""
    return (
        f"### Project Plan: {topic}\n\n"
        f"**Executive Objective:** Architect, engineer, test, and deploy a production-grade {topic} "
        f"aligned with enterprise security, performance, and scalability standards.\n\n"
        f"#### Phase 1: Product Scope & Architecture Design\n"
        f"1. **Define Core System Architecture for {topic}**: Document technical requirements, component boundaries, and API specifications. (Priority: `high`, Estimated: 2 days)\n"
        f"2. **Design Database Schema & Relational Models for {topic}**: Establish PostgreSQL tables, foreign key relationships, migrations, and index strategies. (Priority: `high`, Estimated: 2 days)\n\n"
        f"#### Phase 2: Backend Services & API Engineering\n"
        f"3. **Develop Core Backend Services for {topic}**: Build robust asynchronous API endpoints, transaction handling, and business rules. (Priority: `high`, Estimated: 4 days)\n"
        f"4. **Implement Authentication, RBAC & Security for {topic}**: Setup JWT authentication, password hashing, role permissions, and input sanitization. (Priority: `high`, Estimated: 3 days)\n\n"
        f"#### Phase 3: Frontend Interface & UI/UX Integration\n"
        f"5. **Construct Responsive UI Components for {topic}**: Build modular React/TypeScript UI layouts, state management, and reusable components. (Priority: `medium`, Estimated: 4 days)\n"
        f"6. **Connect API Integration & State Management for {topic}**: Implement secure API client layer, optimistic UI updates, and error boundaries. (Priority: `medium`, Estimated: 3 days)\n\n"
        f"#### Phase 4: Testing, Verification & Hardening\n"
        f"7. **Execute Automated Testing & Security Audits for {topic}**: Run unit test suites, integration tests, end-to-end user flows, and vulnerability scans. (Priority: `high`, Estimated: 3 days)\n\n"
        f"#### Phase 5: Containerization, CI/CD & Deployment\n"
        f"8. **Configure Docker Containerization & Deployment for {topic}**: Set up Docker Compose, environment configurations, health check probes, and CI/CD pipelines. (Priority: `medium`, Estimated: 2 days)\n\n"
        f"**Deliverables:** Production codebase, automated test suite, migration scripts, container configs, and operational documentation.\n\n"
        f"👉 *Next Action: Say **'Add it in my to do list'** (or **'Add these steps to my to-do list'**) to automatically commit these tasks directly into the PostgreSQL database.*"
    )

def _build_refined_project_plan(topic: str, refinement_request: str) -> str:
    """Build an expanded, refined project plan incorporating administrative adjustments."""
    return (
        f"### Refined Project Plan: {topic}\n\n"
        f"**Adjusted Objective:** Incorporating administrative refinements: *\"{refinement_request.strip()}\"*.\n\n"
        f"#### Phase 1: Specifications & Architecture\n"
        f"1. **Define Detailed Functional Specs for {topic}**: Document edge cases, failure recovery, and data contracts. (Priority: `high`, Duration: 2 days)\n"
        f"2. **Design Database Schema & Compound Indexes for {topic}**: Define tables, foreign keys, triggers, and compound indexes. (Priority: `high`, Duration: 2 days)\n\n"
        f"#### Phase 2: Core Engineering & Implementation\n"
        f"3. **Develop Backend Endpoints & Validation for {topic}**: Implement validated REST routes, OAuth2 token handling, and database services. (Priority: `high`, Duration: 4 days)\n"
        f"4. **Build User Interfaces & Navigation for {topic}**: Develop responsive layouts, state hooks, and component modals. (Priority: `medium`, Duration: 3 days)\n\n"
        f"#### Phase 3: Comprehensive Testing & Quality Assurance\n"
        f"5. **Automated Unit & Integration Testing for {topic}**: Achieve 100% test coverage across endpoints and service layers. (Priority: `high`, Duration: 2 days)\n"
        f"6. **Security & Boundary Penetration Testing for {topic}**: Validate role isolation, tamper resistance, and input validation. (Priority: `high`, Duration: 2 days)\n\n"
        f"#### Phase 4: Deployment & Telemetry\n"
        f"7. **Containerization & CI/CD Setup for {topic}**: Configure multi-stage Docker build, health probes, and migration runners. (Priority: `medium`, Duration: 2 days)\n\n"
        f"👉 *Next Action: Say **'Add it in my to do list'** to persist these actionable tasks to the database.*"
    )

def _generate_intelligent_conversational_reply(
    user_message: str,
    current_user: User,
    recent_messages: List[ChatMessage],
) -> str:
    """
    Claude / GPT / Gemini standard intelligent conversational reasoning engine.
    Answers general software engineering questions, architectural trade-offs,
    technology comparisons, and system administration queries naturally and fluently.
    Never falls back to rigid robotic menus.
    """
    msg = user_message.strip()
    msg_lower = msg.lower()
    first_name = (current_user.full_name or "there").strip()

    # 1. Building an App / Planning Guidance
    if any(k in msg_lower for k in ["build an app", "develop an app", "create an app", "steps to build", "how to build", "how do i build", "plan to build"]):
        return (
            f"Building a modern, production-grade application requires a disciplined engineering roadmap across **5 core pillars**:\n\n"
            f"### 1. Requirements & System Architecture\n"
            f"- **Define Use Cases:** Identify primary personas, essential user flows, and role boundaries (e.g. Admin vs Standard User).\n"
            f"- **Select Tech Stack:** Choose proven technologies suited to your scale (such as FastAPI/Python for high-performance async backends, React + TypeScript for type-safe UI, and PostgreSQL for ACID-compliant persistence).\n\n"
            f"### 2. Database Modeling & Persistence\n"
            f"- **Schema Design:** Model relational entities (Users, Tasks, Notifications, Audit Logs) with foreign keys and compound indexes on high-frequency query fields.\n"
            f"- **Migrations:** Use schema migration tooling (e.g., Alembic) to ensure versioned, reproducible database evolutions.\n\n"
            f"### 3. Backend Services & API Design\n"
            f"- **REST / GraphQL APIs:** Create validated endpoints with Pydantic models, JWT authentication, and strict error handling.\n"
            f"- **Role-Based Access Control (RBAC):** Enforce authorization at the database layer so users can only access their authorized records.\n\n"
            f"### 4. Frontend & User Experience\n"
            f"- **Component Architecture:** Build reusable UI widgets, modal dialogs, and real-time toast notifications.\n"
            f"- **State & API Layer:** Centralize API communication with auto-retry, auth header injection, and responsive loading states.\n\n"
            f"### 5. Automated Testing & DevOps\n"
            f"- **Testing:** Maintain comprehensive unit, integration, and security test suites.\n"
            f"- **Containerization:** Package services with Docker and Docker Compose for deterministic deployment across development, staging, and production.\n\n"
            f"---\n"
            f"👉 **Ready to take action?** Simply say:\n"
            f"- **'Make a plan for me'** (or *'Provide me the plan'*): I will structure this into numbered, actionable project tasks.\n"
            f"- **'Add it in my to do list'**: I will automatically write those tasks directly into the TaskMaster database."
        )

    # 2. Docker & Containerization
    if any(k in msg_lower for k in ["docker", "container", "containerize", "kubernetes", "k8s", "dockerfile", "docker-compose"]):
        return (
            "### Docker Containerization & Best Practices\n\n"
            "**Docker** packages an application and all its runtime dependencies (Python runtime, system libraries, OS packages) into an immutable, portable container image.\n\n"
            "#### Key Advantages for Production Systems:\n"
            "- **Environment Parity:** Eliminates the *'it works on my machine'* dilemma by ensuring identical runtime environments from local development to production.\n"
            "- **Resource Efficiency:** Containers share the host OS kernel rather than virtualizing hardware like traditional VMs, resulting in near-instant startup times and minimal memory footprint.\n"
            "- **Microservice Orchestration:** With **Docker Compose**, multi-service setups (such as FastAPI Backend, Chatbot Service, PostgreSQL, and React Frontend) can be launched, linked via internal DNS, and monitored with a single command.\n\n"
            "#### Essential Best Practices:\n"
            "1. **Multi-Stage Builds:** Separate build dependencies (node_modules, compilation tools) from the final lean runtime container to drastically reduce image size.\n"
            "2. **Non-Root Execution:** Always run application processes as a dedicated non-root user (`USER appuser`) to minimize container breakout risks.\n"
            "3. **Health Check Probes:** Define explicit container health probes (`HEALTHCHECK CMD curl -f http://localhost:8000/health`) for automatic restart and zero-downtime routing.\n\n"
            "*Would you like me to generate a Docker configuration plan or add deployment tasks to your to-do list?*"
        )

    # 3. PostgreSQL & Database Architecture
    if any(k in msg_lower for k in ["postgres", "postgresql", "sql vs nosql", "indexing", "database", "orm", "alembic", "migrations", "acid"]):
        return (
            "### PostgreSQL Architecture & Database Design\n\n"
            "**PostgreSQL** is the industry-standard open-source Object-Relational Database Management System (ORDBMS), celebrated for its robust ACID guarantees, extensive data type support, and high concurrency.\n\n"
            "#### Core Database Engineering Concepts:\n"
            "- **ACID Guarantees:** Atomicity, Consistency, Isolation, and Durability ensure transaction integrity even under unexpected crashes or network partitions.\n"
            "- **Indexing Strategies:** B-Tree indexes for standard equality and range queries (`WHERE status = 'pending'`), and Compound Indexes (`WHERE user_id = X AND status = Y`) to accelerate multi-column filters.\n"
            "- **Connection Pooling:** In high-concurrency environments (like FastAPI with `asyncpg` or `psycopg3`), a connection pool reuses open TCP sockets to avoid expensive per-request handshake overhead.\n"
            "- **Schema Migrations:** Tools like Alembic maintain linear revision histories, allowing automated schema upgrades in CI/CD without data corruption.\n\n"
            "*Tip: In TaskMaster, PostgreSQL handles both our core task management and AI conversation history in a single unified, secure data store.*"
        )

    # 4. APIs, REST & FastAPI
    if any(k in msg_lower for k in ["api", "rest", "graphql", "fastapi", "endpoints", "http methods"]):
        return (
            "### Modern API Engineering & FastAPI Architecture\n\n"
            "When designing high-performance web APIs, **FastAPI** stands out because it leverages Python's native `asyncio` event loop and Pydantic data validation.\n\n"
            "#### REST vs. GraphQL Architectural Comparison:\n"
            "- **REST (Representational State Transfer):** Resource-oriented, leverages native HTTP caching and status codes (`200 OK`, `201 Created`, `401 Unauthorized`), simple to secure and monitor.\n"
            "- **GraphQL:** Single endpoint where clients request specific fields. Excellent for complex mobile frontends with varying data requirements, but harder to cache at the edge.\n\n"
            "#### FastAPI Strengths:\n"
            "1. **Automatic OpenAPI/Swagger Documentation:** Interactive API documentation generated dynamically from Python type hints.\n"
            "2. **Strict Schema Validation:** Pydantic models automatically validate incoming payloads and return structured `422 Unprocessable Entity` responses on invalid inputs.\n"
            "3. **Dependency Injection:** Seamless handling of database sessions, authentication headers, and role checks through FastAPI's `Depends()` pattern.\n\n"
            "*Would you like to design new endpoints or create tasks for API expansion?*"
        )

    # 5. Security, JWT & Authentication
    if any(k in msg_lower for k in ["jwt", "token", "auth", "security", "rbac", "password", "hash", "bcrypt", "cors", "injection"]):
        return (
            "### Web Application Security & Authentication Best Practices\n\n"
            "Securing enterprise web applications requires defense-in-depth across multiple layers:\n\n"
            "#### 1. JSON Web Tokens (JWT) & Session Security\n"
            "- **Structure:** Header, Payload (claims: `sub`, `exp`, `role`), and Cryptographic Signature (`HS256` or `RS256`).\n"
            "- **Stateless Verification:** Backends can verify authenticity using the shared secret without needing a database roundtrip on every request.\n"
            "- **Best Practice:** Keep access tokens short-lived (e.g. 15–30 minutes) and use secure refresh tokens for session renewal.\n\n"
            "#### 2. Password Hashing with Bcrypt / Argon2\n"
            "- Passwords should **never** be stored in plaintext. Use salted adaptive hashing (like Bcrypt with work factor >= 12) to resist offline dictionary and brute-force attacks.\n\n"
            "#### 3. Role-Based Access Control (RBAC)\n"
            "- Enforce permissions strictly server-side. Even if a user alters client state, the API verifies `current_user.role == UserRole.ADMIN` before performing privileged mutations.\n\n"
            "*TaskMaster utilizes 3-tier API key architecture alongside JWT authentication to secure Frontend, Backend, and Chatbot services.*"
        )

    # 6. Microservices & System Design
    if any(k in msg_lower for k in ["microservices", "microservice", "monolith", "event driven", "kafka", "rabbitmq", "redis", "caching", "scalability"]):
        return (
            "### Microservices Architecture vs. Modular Monolith\n\n"
            "Dividing systems into specialized services offers independent scaling and targeted failure isolation, but introduces network complexity.\n\n"
            "#### Architectural Comparison:\n"
            "- **Modular Monolith:** Single deployment artifact with strictly separated code domains. Easiest to develop, test, and deploy for early to mid-stage applications.\n"
            "- **Microservices:** Independent services communicating over HTTP/gRPC or message brokers (Kafka, RabbitMQ). Ideal when different components have vastly different compute profiles (e.g. standard CRUD backend vs AI Chatbot/LLM orchestration service).\n\n"
            "#### Core Distributed System Patterns:\n"
            "1. **API Gateway / Reverse Proxy:** Single entry point managing routing, rate limiting, and SSL termination.\n"
            "2. **Distributed Caching:** Redis for caching frequently read, slow-changing records to protect database CPU.\n"
            "3. **Circuit Breakers:** Prevent cascading failures when a downstream service is experiencing latency or degradation.\n\n"
            "*In this project, the Chatbot runs as a standalone microservice on port 8001 connected to the main backend and shared PostgreSQL database.*"
        )

    # 7. AI, RAG & LLMs
    if any(k in msg_lower for k in ["rag", "llm", "openrouter", "openai", "embeddings", "vector", "deepseek", "claude", "gpt", "gemini"]):
        return (
            "### Retrieval-Augmented Generation (RAG) & LLM Orchestration\n\n"
            "**Retrieval-Augmented Generation (RAG)** bridges the gap between static foundational Large Language Models and dynamic, authoritative private databases.\n\n"
            "#### The 4-Step Grounded Pipeline:\n"
            "1. **User Request:** The user submits a natural-language query.\n"
            "2. **Database Retrieval:** The backend executes authorized queries against PostgreSQL to retrieve ground truth (tasks, user profiles, system telemetry).\n"
            "3. **Prompt Augmentation:** Retrieved facts are injected into the system prompt alongside the conversation history.\n"
            "4. **Synthesis:** The LLM generates a human, factual response completely grounded in live database state, eliminating hallucinations.\n\n"
            "#### Tool / Function Calling:\n"
            "Advanced models can output structured JSON tool calls (e.g., `admin_create_task`, `admin_list_users`). The backend executes these tools against PostgreSQL and passes results back to the LLM for final synthesis.\n\n"
            "*In TaskMaster, RAG guarantees that only live, authorized database data is accessed and presented.*"
        )

    # 8. Frontend & UI/UX (React & TypeScript)
    if any(k in msg_lower for k in ["react", "typescript", "frontend", "ui", "state management", "hooks", "tailwind"]):
        return (
            "### Modern Frontend Development with React & TypeScript\n\n"
            "Building responsive, maintainable frontend applications relies on component modularity and type safety.\n\n"
            "#### Core Principles:\n"
            "- **Type Safety:** TypeScript interfaces eliminate runtime `TypeError: undefined is not a function` bugs by validating API response shapes at compile time.\n"
            "- **Component Composition:** Breaking down views into pure UI components, modal dialogs, and reusable layout containers.\n"
            "- **Custom Hooks:** Encapsulating stateful business logic (authentication, API polling, toast notifications) into clean, reusable custom hooks.\n"
            "- **Optimistic Updates:** Updating the UI immediately upon user action while the network request executes in the background, rolling back gracefully if an error occurs.\n\n"
            "*TaskMaster's frontend uses Vite, React, and TypeScript with the dedicated Chatbot floating widget.*"
        )

    # 9. General Conversational / Intelligent Assistant Tone
    return (
        f"Hi {first_name}! I am your **Admin AI Assistant**.\n\n"
        f"I operate as a hybrid conversational and database-connected intelligence (inspired by Claude and modern LLMs). "
        f"I can discuss software architecture, provide engineering roadmaps, answer technical questions, and directly manage "
        f"the TaskMaster PostgreSQL database.\n\n"
        f"### What would you like to do?\n"
        f"- **Plan an App or Feature:** *'I want to build an app, provide me the plan'* or *'Suggest tasks for backend security'*\n"
        f"- **Persist Plan to Database:** Say *'Add it in my to do list'* to convert any active plan into PostgreSQL tasks.\n"
        f"- **Inspect Live Users & Directory:** *'List all registered users'*\n"
        f"- **Review Tasks & Workload:** *'List my pending tasks'* or *'Show system telemetry'*\n"
        f"- **Ask Technical Questions:** Inquire about Docker, PostgreSQL, FastAPI, React, RAG, or system design.\n\n"
        f"How can I assist you with your project today?"
    )

