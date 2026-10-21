-- ============================================================================
-- Production-Ready To-Do List Application - Safe Seed Data for Testing
-- ============================================================================

-- Fixed UUIDs for predictable testing and verification
-- Passwords below are bcrypt / argon2 formatted fixtures (never plaintext)
-- Admin User: admin@example.com (Fixed UUID: a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11)
-- Standard User 1: alice@example.com (Fixed UUID: b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22)
-- Standard User 2: bob@example.com (Fixed UUID: c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a33)

INSERT INTO users (id, full_name, email, password_hash, role, is_active)
VALUES
    ('a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', 'System Administrator', 'admin@example.com', '$2b$12$PHoE0c9rs8rFHgc2nhXYsepOI93/BzIAGb7bhYWH28sBy5PkzjOT6', 'admin', TRUE),
    ('b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 'Alice Engineer', 'alice@example.com', '$2b$12$PHoE0c9rs8rFHgc2nhXYsepOI93/BzIAGb7bhYWH28sBy5PkzjOT6', 'user', TRUE),
    ('c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a33', 'Bob Developer', 'bob@example.com', '$2b$12$PHoE0c9rs8rFHgc2nhXYsepOI93/BzIAGb7bhYWH28sBy5PkzjOT6', 'user', TRUE);

-- Tasks for Alice
INSERT INTO tasks (id, user_id, title, description, status, priority, due_date, completed_at)
VALUES
    ('11111111-1111-1111-1111-111111111111', 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 'Design PostgreSQL Schema', 'Formulate relational schema, keys, and indexes', 'completed', 'high', CURRENT_TIMESTAMP - INTERVAL '1 day', CURRENT_TIMESTAMP - INTERVAL '2 hours'),
    ('22222222-2222-2222-2222-222222222222', 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 'Build FastAPI Endpoints', 'Implement task CRUD and JWT authentication', 'in_progress', 'high', CURRENT_TIMESTAMP + INTERVAL '3 days', NULL),
    ('33333333-3333-3333-3333-333333333333', 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 'Write Unit Tests', 'Pytest test cases with HTTPX test client', 'pending', 'medium', CURRENT_TIMESTAMP + INTERVAL '5 days', NULL);

-- Tasks for Bob
INSERT INTO tasks (id, user_id, title, description, status, priority, due_date, completed_at)
VALUES
    ('44444444-4444-4444-4444-444444444444', 'c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a33', 'Setup React Vite Project', 'Initialize TypeScript project with Tailwind CSS', 'pending', 'low', CURRENT_TIMESTAMP + INTERVAL '7 days', NULL),
    ('55555555-5555-5555-5555-555555555555', 'c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a33', 'Configure Docker Compose', 'Define multi-container setup for local dev', 'in_progress', 'medium', CURRENT_TIMESTAMP + INTERVAL '2 days', NULL);

