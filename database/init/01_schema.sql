-- ============================================================================
-- Production-Ready To-Do List Application - Phase 1 Schema
-- Database: todo_app
-- PostgreSQL Version: 14+ (Tested on PostgreSQL 18)
-- ============================================================================

-- Enable required extension for UUID generation if needed
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Clean teardown if rebuilding schema cleanly
DROP TABLE IF EXISTS refresh_tokens CASCADE;
DROP TABLE IF EXISTS tasks CASCADE;
DROP TABLE IF EXISTS users CASCADE;

DROP TYPE IF EXISTS task_priority CASCADE;
DROP TYPE IF EXISTS task_status CASCADE;
DROP TYPE IF EXISTS user_role CASCADE;

-- ----------------------------------------------------------------------------
-- 1. Custom Enumerated Types
-- ----------------------------------------------------------------------------
CREATE TYPE user_role AS ENUM ('admin', 'user');
CREATE TYPE task_status AS ENUM ('pending', 'in_progress', 'completed');
CREATE TYPE task_priority AS ENUM ('low', 'medium', 'high');

-- ----------------------------------------------------------------------------
-- 2. Trigger Function: Automatically Maintain updated_at Timestamps
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION set_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ----------------------------------------------------------------------------
-- 3. Table: users
-- ----------------------------------------------------------------------------
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,  -- brute-force lockout counter
    locked_until TIMESTAMPTZ,
    reset_code_hash VARCHAR(64),  -- HMAC of the forgot-password code, never the code itself
    reset_code_expires_at TIMESTAMPTZ,
    reset_code_attempts INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT chk_users_full_name_not_empty CHECK (char_length(trim(full_name)) > 0),
    CONSTRAINT chk_users_email_format CHECK (
        email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
    )
);

-- Unique index ensuring case-insensitive email uniqueness
CREATE UNIQUE INDEX uq_users_email_lower ON users (LOWER(email));

-- Filtered index on active users for quick authentication lookups
CREATE INDEX idx_users_email_active ON users (LOWER(email)) WHERE is_active = TRUE;

-- Trigger to update updated_at on users
CREATE TRIGGER trg_users_set_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION set_updated_at_column();

-- ----------------------------------------------------------------------------
-- 4. Table: tasks
-- ----------------------------------------------------------------------------
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status task_status NOT NULL DEFAULT 'pending',
    priority task_priority NOT NULL DEFAULT 'medium',
    due_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMPTZ,

    -- Constraints
    CONSTRAINT fk_tasks_user_id 
        FOREIGN KEY (user_id) 
        REFERENCES users (id) 
        ON DELETE CASCADE,

    CONSTRAINT chk_tasks_title_not_empty 
        CHECK (char_length(trim(title)) > 0),

    -- Completed tasks must have completed_at timestamp; non-completed tasks must have NULL completed_at
    CONSTRAINT chk_tasks_status_completed_at 
        CHECK (
            (status = 'completed' AND completed_at IS NOT NULL) OR
            (status != 'completed' AND completed_at IS NULL)
        )
);

-- Indexes for tasks:
-- 1. Primary foreign key index for task listings per user
CREATE INDEX idx_tasks_user_id ON tasks (user_id);

-- 2. Compound index for filtered user dashboard listings ordered by creation date
CREATE INDEX idx_tasks_user_status_priority_created ON tasks (user_id, status, priority, created_at DESC);

-- 3. Composite index for user tasks filtered / sorted by due date
CREATE INDEX idx_tasks_user_due_date ON tasks (user_id, due_date ASC NULLS LAST);

-- Trigger to update updated_at on tasks
CREATE TRIGGER trg_tasks_set_updated_at
BEFORE UPDATE ON tasks
FOR EACH ROW
EXECUTE FUNCTION set_updated_at_column();

-- ----------------------------------------------------------------------------
-- 5. Table: refresh_tokens (Additional Table Justified by Phase 2 Security Architecture)
-- Justification: Stores cryptographically secure refresh token sessions to enable
-- token rotation, replay detection, and explicit user logout / session revocation.
-- ----------------------------------------------------------------------------
CREATE TABLE refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    token_hash VARCHAR(64) NOT NULL, -- SHA-256 hash of the refresh token secret
    revoked BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_refresh_tokens_user_id 
        FOREIGN KEY (user_id) 
        REFERENCES users (id) 
        ON DELETE CASCADE
);

-- Index for fast token validation and lookup
CREATE UNIQUE INDEX uq_refresh_tokens_token_hash ON refresh_tokens (token_hash);
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens (user_id);

-- ----------------------------------------------------------------------------
-- 6. Table: chat_conversations
-- ----------------------------------------------------------------------------
CREATE TABLE chat_conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    title VARCHAR(255) NOT NULL DEFAULT 'New Conversation',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_chat_conversations_user_id 
        FOREIGN KEY (user_id) 
        REFERENCES users (id) 
        ON DELETE CASCADE
);

CREATE INDEX idx_chat_conversations_user_id ON chat_conversations (user_id, updated_at DESC);

CREATE TRIGGER trg_chat_conversations_set_updated_at
BEFORE UPDATE ON chat_conversations
FOR EACH ROW
EXECUTE FUNCTION set_updated_at_column();

-- ----------------------------------------------------------------------------
-- 7. Table: chat_messages
-- ----------------------------------------------------------------------------
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL,
    sender VARCHAR(20) NOT NULL, -- 'user', 'assistant'
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_chat_messages_conversation_id 
        FOREIGN KEY (conversation_id) 
        REFERENCES chat_conversations (id) 
        ON DELETE CASCADE
);

CREATE INDEX idx_chat_messages_conversation_id ON chat_messages (conversation_id, created_at ASC);

-- ----------------------------------------------------------------------------
-- 8. Table: notifications
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    type VARCHAR(50) NOT NULL DEFAULT 'task_assigned',
    read BOOLEAN NOT NULL DEFAULT FALSE,
    delivered BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications (user_id, created_at DESC);



