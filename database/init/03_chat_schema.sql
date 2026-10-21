-- ============================================================================
-- Production-Ready To-Do List Application - Chat & RAG Schema
-- Database: todo_app
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. Table: chat_conversations
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_conversations (
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

CREATE INDEX IF NOT EXISTS idx_chat_conversations_user_id ON chat_conversations (user_id, updated_at DESC);

-- Trigger to update updated_at on chat_conversations
DROP TRIGGER IF EXISTS trg_chat_conversations_set_updated_at ON chat_conversations;
CREATE TRIGGER trg_chat_conversations_set_updated_at
BEFORE UPDATE ON chat_conversations
FOR EACH ROW
EXECUTE FUNCTION set_updated_at_column();

-- ----------------------------------------------------------------------------
-- 2. Table: chat_messages
-- ----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS chat_messages (
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

CREATE INDEX IF NOT EXISTS idx_chat_messages_conversation_id ON chat_messages (conversation_id, created_at ASC);

