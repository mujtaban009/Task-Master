# TaskMaster: Production-Ready To-Do Application

A full-stack, enterprise-grade To-Do List Application with Role-Based Access Control (Admin and Standard Users), JWT Token Rotation, Database-Side Pagination & Filtering, and an interactive React dashboard.

---

## Tech Stack
- **Database**: PostgreSQL 18 with UUID primary keys, ENUMs, triggers, and compound indexes.
- **Backend**: Python 3.11, FastAPI, SQLAlchemy 2.x async ORM, Psycopg 3, Passlib (bcrypt), PyJWT.
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons, Axios, React Router v6.
- **Deployment**: Docker & Docker Compose with PostgreSQL health checks.

---

## 1. Quick Start (Local Development)

### A. Run Database
PostgreSQL is running on `127.0.0.1:5432` with database `todo_app`.
Schema files and seed data are in [`database/init/`](file:///d:/Todolist/database/init).

### B. Run FastAPI Backend
```powershell
cd d:\Todolist\backend
.\venv\Scripts\python.exe run.py
```
- API Root: `http://127.0.0.1:8000/api/v1`
- Swagger Interactive Documentation: `http://127.0.0.1:8000/docs`
- Health Probe: `http://127.0.0.1:8000/health`

### C. Run React Frontend
```powershell
cd d:\Todolist\frontend
& "C:\Program Files\nodejs\npm.cmd" run dev
```
- Open your browser at: `http://localhost:5173`

---

## 2. Seed User Credentials for Testing

| Role | Email | Password | Permissions |
|---|---|---|---|
| **Admin** | `admin@example.com` | `password` | Accesses `/admin`, system statistics, user moderation |
| **Standard User** | `alice@example.com` | `password` | Manages own tasks, isolated from other users |
| **Standard User** | `bob@example.com` | `password` | Manages own tasks, isolated from other users |

*(You can also use the registration form to create brand new accounts at `/register`)*

---

## 3. Role-Based AI Assistant Chatbot (LLM & Grounded RAG)

Both the Admin Panel and User Panel feature an interactive floating **“AI Assistant”** widget powered by Retrieval-Augmented Generation (RAG).

### Key Features:
- **Floating Widget**: Present in the bottom-right corner of all authenticated views. Preserves conversation context across panel navigation and session switches.
- **Strict Data Isolation for Standard Users**: Users can only retrieve, search, or summarize their own tasks. Queries inquiring about other users or attempting prompt injections are strictly intercepted and rejected at the server level.
- **Privileged Access for Administrators**: Admins can run cross-user queries (e.g., workload distribution, task counts per user, overdue tasks across the entire system, and user moderation).
- **Dual-Mode LLM / Grounded Engine**:
  - **With API Key**: Connects to OpenAI or any compatible LLM endpoint (`OPENAI_API_KEY`, `OPENAI_BASE_URL`, `LLM_MODEL`) with function/tool calling.
  - **Deterministic RAG Fallback**: If no API key is configured, an internal deterministic RAG engine safely executes authorized database tools and synthesizes grounded responses.
- **Conversation Management**: Full multi-turn conversation support, session persistence, conversation history drawer, and new-chat initiation.

---

## 4. Running Backend Tests
```powershell
cd d:\Todolist\backend
.\venv\Scripts\pytest.exe -v
```
All 11 unit, integration, RAG role-isolation, and E2E security lifecycle tests pass with 100% success.
---

## 5. Deploy on Vercel (free)

One Vercel project serves both parts: `vercel.json` builds `frontend/` as static files and runs the FastAPI app through `api/index.py` as a Python function.

1. Import the GitHub repo in Vercel (no settings to change; `vercel.json` has them).
2. **Storage → Create → Neon (Postgres)** and connect it to the project. This adds `POSTGRES_URL`, which the backend uses automatically.
3. In Neon's SQL editor, run `database/init/01_schema.sql`, `03_chat_schema.sql` and `04_notifications_schema.sql`. Skip `02_seed.sql`: its demo accounts use the password `password`.
4. **Settings → Environment Variables:** add `JWT_SECRET_KEY` (generate with `python -c "import secrets; print(secrets.token_hex(32))"`) and `ENVIRONMENT=production`. Redeploy.
   Optional: `OPENAI_API_KEY` (free Gemini key from aistudio.google.com) for the AI assistant, and `SMTP_USER` (a Gmail address) + `SMTP_PASSWORD` (a Gmail App password) so forgot-password codes are emailed.
5. Register on the live site, then make yourself admin in Neon's SQL editor:
   `UPDATE users SET role = 'admin' WHERE email = 'you@example.com';`
