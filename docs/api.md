# FastAPI Backend API Documentation

## 1. Overview
The backend is built with **FastAPI**, **SQLAlchemy 2.x (async)**, and **Psycopg** on top of **PostgreSQL 18**.
Base URL: `http://localhost:8000/api/v1`
Interactive Swagger Docs: `http://localhost:8000/docs`

---

## 2. Authentication Flow
- **Access Tokens**: Short-lived JWT (15 minutes). Sent in `Authorization: Bearer <token>` header.
- **Refresh Tokens**: Long-lived (7 days). Stored hashed (SHA-256) in the database for rotation and revocation.
- **Logout**: Invalidates the refresh token session in the database immediately.

### Endpoints:
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Register new user | No |
| `POST` | `/api/v1/auth/login` | Login with username/password | No |
| `POST` | `/api/v1/auth/refresh` | Refresh access token | No |
| `POST` | `/api/v1/auth/logout` | Revoke token session | Yes (Bearer) |

---

## 3. Tasks Endpoints
All task queries strictly filter on `user_id = current_user.id`. A user can never access, edit, or delete another user's task.

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/tasks` | List tasks (pagination, filter, sort) | Yes (User/Admin) |
| `POST` | `/api/v1/tasks` | Create a task | Yes (User/Admin) |
| `GET` | `/api/v1/tasks/summary` | Aggregate task statistics | Yes (User/Admin) |
| `GET` | `/api/v1/tasks/{task_id}` | Get task by UUID | Yes (User/Admin) |
| `PATCH` | `/api/v1/tasks/{task_id}` | Partial task update | Yes (User/Admin) |
| `DELETE` | `/api/v1/tasks/{task_id}` | Delete task | Yes (User/Admin) |

### Query Parameters for `GET /api/v1/tasks`:
- `page`: Integer (default 1, $\ge 1$)
- `page_size`: Integer (default 20, max 100)
- `status`: Optional enum (`pending`, `in_progress`, `completed`)
- `priority`: Optional enum (`low`, `medium`, `high`)
- `search`: Search substring for task title
- `sort_by`: `created_at` (default), `due_date`, `priority`, `title`
- `sort_order`: `desc` (default), `asc`

---

## 4. User Endpoints
| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/users/me` | Current user profile | Yes (User/Admin) |
| `PATCH` | `/api/v1/users/me` | Update name or password (password change needs `current_password` and logs out all sessions) | Yes (User/Admin) |

---

## 5. Admin Endpoints
Protected strictly by `get_current_admin` dependency. Returns `403 Forbidden` for standard users.

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `GET` | `/api/v1/admin/dashboard` | Cross-system aggregated metrics | Yes (Admin only) |
| `GET` | `/api/v1/admin/users` | List users with pagination/search | Yes (Admin only) |
| `PATCH` | `/api/v1/admin/users/{user_id}/status` | Activate/Deactivate user | Yes (Admin only) |

---

## 6. AI Assistant & RAG Chat Endpoints
Protected by `get_current_user`. Server enforces role-based authorization: standard users can strictly query and manage their own tasks, while administrators have access to cross-user analytics and user task workloads.

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| `POST` | `/api/v1/chat/message` | Send message to AI Assistant (Dual-mode LLM/RAG) | Yes (User/Admin) |
| `GET` | `/api/v1/chat/conversations` | List user's conversations | Yes (User/Admin) |
| `GET` | `/api/v1/chat/conversations/{id}` | Get conversation history with messages | Yes (User/Admin) |
| `DELETE` | `/api/v1/chat/conversations/{id}` | Delete conversation | Yes (User/Admin) |

### Request Payload for `POST /api/v1/chat/message`:
```json
{
  "content": "Which tasks are still pending?",
  "conversation_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6" // Optional
}
```

### AI Configuration & Dual-Mode Engine:
- **Environment Variables**:
  - `OPENAI_API_KEY`: API key for OpenAI or any OpenAI-compatible provider (Groq, Together, Ollama, LM Studio, etc.).
  - `OPENAI_BASE_URL`: API base URL (defaults to `https://api.openai.com/v1`).
  - `LLM_MODEL`: Model name (defaults to `gpt-4o-mini`).
- **Deterministic RAG Fallback**:
  - When `OPENAI_API_KEY` is not configured, the assistant automatically operates in deterministic grounded RAG mode, executing authorized database tools and synthesizing structured responses without external network dependencies.
- **Role Isolation**:
  - Regular users attempting to query other users' tasks or access administrator commands are rejected at the server service layer. No unauthorized data is ever retrieved or passed into the prompt context.

---

## 7. How to Run Backend Locally

```powershell
# Navigate to backend directory
cd d:\Todolist\backend

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run development server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
