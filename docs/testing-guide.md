# PostgreSQL Terminal Setup & Verification Guide

This guide walks you through setting up and validating the PostgreSQL database for **Phase 1** from the VS Code terminal (PowerShell).

---

## 1. Prerequisites and Environment

- PostgreSQL 14+ installed (PostgreSQL 18 is running locally as Windows service `postgresql-x64-18`).
- `psql` path: `C:\Program Files\PostgreSQL\18\bin\psql.exe`.

### Add `psql` to your current PowerShell session (optional shortcut):
```powershell
$env:PATH += ";C:\Program Files\PostgreSQL\18\bin"
```

---

## 2. Step 1: Create Database and User

In your VS Code PowerShell terminal, run the following commands to create the `todo_app` database and a dedicated user `todo_user`:

```powershell
# Set your superuser postgres password if prompted:
$env:PGPASSWORD = "YOUR_POSTGRES_PASSWORD"

# Create the database:
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h localhost -c "CREATE DATABASE todo_app;"
```

*(Note: If `todo_app` already exists, you can proceed directly to applying the schema.)*

---

## 3. Step 2: Apply the Phase 1 Schema

Apply the schema file [01_schema.sql](file:///d:/Todolist/database/init/01_schema.sql):

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h localhost -d todo_app -f "d:\Todolist\database\init\01_schema.sql"
```

Expected output:
```text
CREATE EXTENSION
DROP TABLE / DROP TYPE (if re-running)
CREATE TYPE
CREATE FUNCTION
CREATE TABLE (users)
CREATE INDEX
CREATE TRIGGER
CREATE TABLE (tasks)
CREATE INDEX
CREATE TRIGGER
CREATE TABLE (refresh_tokens)
CREATE INDEX
```

---

## 4. Step 3: Populate Seed Data

Insert the test users and tasks from [02_seed.sql](file:///d:/Todolist/database/init/02_seed.sql):

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h localhost -d todo_app -f "d:\Todolist\database\init\02_seed.sql"
```

Expected output:
```text
INSERT 0 3
INSERT 0 3
INSERT 0 2
```

---

## 5. Step 4: Run the Complete Test Suite

Execute the full verification test suite [test_suite.sql](file:///d:/Todolist/database/tests/test_suite.sql):

```powershell
& "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h localhost -d todo_app -f "d:\Todolist\database\tests\test_suite.sql"
```

---

## 6. Test Cases, Expected Results & Pass/Fail Criteria

| # | Test Scenario | Expected Outcome | Pass/Fail Criterion |
|---|---|---|---|
| **1** | Retrieve all users | Returns 3 seed users: admin, alice, bob | Exactly 3 rows with correct roles |
| **2** | Insert new task | Returns inserted UUID and pending status | Row inserted successfully |
| **3** | Retrieve Alice's tasks | Returns tasks only for Alice's user UUID | Exactly Alice's tasks, Bob's tasks excluded |
| **4** | Update task | Title, priority, and `updated_at` change | Updated timestamp changes automatically via trigger |
| **5** | Mark completed | Status set to `completed` and `completed_at` populated | Complies with `chk_tasks_status_completed_at` |
| **6** | Filter status & priority | Tasks with `status='in_progress' AND priority='high'` returned | Correctly filtered subset |
| **7** | Filter due date | Returns upcoming tasks ordered ascending | Chronological order |
| **8** | Delete task | Task deleted cleanly | Row count decreased by 1 |
| **9** | Invalid Foreign Key | Insert task with non-existent `user_id` | **FAIL if accepted**; **PASS** on `foreign_key_violation` |
| **10** | Duplicate Email | Insert `ALICE@EXAMPLE.COM` | **FAIL if accepted**; **PASS** on `unique_violation` |
| **11** | Invalid Role / Check | Insert invalid enum role or `completed_at` without completed status | **FAIL if accepted**; **PASS** on constraint violation |
| **12** | Cascade Delete | Delete user and check if associated tasks cascade | Associated tasks count is 0 |
| **13** | Transaction Rollback | Insert task within `BEGIN ... ROLLBACK` | Row count for rolled back task is 0 |
| **14** | EXPLAIN ANALYZE | Execution plan shows index scan on `(user_id, ...)` | Uses `Index Scan` / `Bitmap Index Scan` |

