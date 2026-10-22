# 🤖 AI Assistant Chatbot (Dedicated Microservice & Module)

This folder contains the complete, decoupled **Chatbot** solution, featuring its own dedicated backend service, modular frontend component, role-based RAG engine, and **Chatbot API Key Authentication**.

---

## 📁 Architecture & Directory Structure

```
d:\Todolist\chatbot\
├── backend\                      # Dedicated Python/FastAPI Chatbot Microservice
│   ├── app\
│   │   ├── api\                  # API Endpoints & Routes (/api/chat)
│   │   │   ├── endpoints\
│   │   │   │   ├── chat.py       # Message processing & conversation endpoints
│   │   │   │   └── health.py     # Microservice health probe
│   │   │   └── router.py         # Router aggregation
│   │   ├── core\
│   │   │   ├── config.py         # Chatbot microservice configuration
│   │   │   └── security.py       # API Key validator (X-Chatbot-API-Key) & JWT decoder
│   │   ├── db\
│   │   │   └── session.py        # Shared PostgreSQL connection (todo_app)
│   │   ├── models\               # SQLAlchemy models (User, Task, ChatMessage, Notification)
│   │   ├── schemas\              # Pydantic schemas for chat requests/responses
│   │   └── services\             # AI services (Grounded RAG, Planner, NotificationService)
│   │       ├── ai_service.py     # Multi-turn planning, table generator, user isolation
│   │       ├── ai_tools.py       # 11 controlled administrative tools
│   │       ├── notification_service.py # In-app notification dispatcher
│   │       ├── task_service.py   # Database task CRUD
│   │       └── admin_service.py  # User & system analytics
│   ├── .env                      # Microservice environment variables & API key
│   ├── requirements.txt          # Python dependencies
│   └── run.py                    # Service runner (Port 8001)
│
├── frontend\                     # Standalone/Modular Chatbot React Component
│   ├── src\
│   │   ├── api\
│   │   │   └── chatbotClient.ts  # Axios client with automatic X-Chatbot-API-Key header
│   │   ├── components\
│   │   │   └── ChatbotWidget.tsx # Floating responsive widget with tables & plan execution
│   │   └── index.ts              # Package entry exports
│
└── README.md                     # Architecture documentation (this file)
```

---

## 🔑 Chatbot API Key Authentication

Communication with the Chatbot microservice is secured using a dedicated API key:

```
CHATBOT_API_KEY=<set in chatbot/backend/.env, never commit it>
```

### How the API Key Connects the System:
1. **Frontend Connection:**
   The frontend Axios client ([`chatbotClient.ts`](file:///d:/Todolist/chatbot/frontend/src/api/chatbotClient.ts) or [`chat.ts`](file:///d:/Todolist/frontend/src/api/chat.ts)) automatically passes the key in every HTTP request:
   ```http
   POST /api/chat/message HTTP/1.1
   Host: 127.0.0.1:8001
   X-Chatbot-API-Key: <CHATBOT_API_KEY>
   Authorization: Bearer <user_jwt_token>
   Content-Type: application/json
   ```

2. **Backend Validation:**
   [`chatbot/backend/app/core/security.py`](file:///d:/Todolist/chatbot/backend/app/core/security.py) inspects the `X-Chatbot-API-Key` header on every request:
   * **Missing Key:** Returns `401 Unauthorized` (`"Chatbot API key is missing"`).
   * **Invalid Key:** Returns `403 Forbidden` (`"Invalid Chatbot API key"`).
   * **Valid Key:** Request proceeds to role authorization and RAG execution.

3. **Database Connection:**
   Both the Todolist application and the Chatbot microservice connect to the **same PostgreSQL database**:
   ```
   postgresql+psycopg://postgres:postgres@127.0.0.1:5432/todo_app
   ```
   * The chatbot reads tasks, users, and audit timestamps directly.
   * When an administrator converts a plan into tasks or creates assignments, tasks are committed to the same `tasks` and `notifications` tables.

---

## 🚀 Running the Services

### 1. Run the Chatbot Microservice (Port 8001)
```powershell
cd d:\Todolist\chatbot\backend
..\..\backend\venv\Scripts\python.exe run.py
```
Health Check: `http://127.0.0.1:8001/api/chat/health`

### 2. Run the Main Todolist Backend (Port 8000)
```powershell
cd d:\Todolist\backend
.\venv\Scripts\python.exe run.py
```

### 3. Run the Frontend (Port 5173)
```powershell
cd d:\Todolist\frontend
npm run dev
```

---

## 🛡️ Role-Based Capabilities

| Feature | Regular User | Administrator |
| :--- | :---: | :---: |
| **Personal Task Queries & Summary** | ✅ | ✅ |
| **Data Isolation (Other Users' Data)** | 🔒 Blocked | 🔓 Full Visibility |
| **Project Planning ("Can you create a plan for me?")** | Basic guidance | 4-Phase Executive Plan |
| **1-Click Plan Conversion to Tasks** | ❌ | ⚡ One-click DB Creation |
| **Task Assignment & Reassignment** | ❌ | ✅ (with notifications) |
| **System Overdue Report & Workload Tables** | ❌ | 📊 Live Markdown Tables |

