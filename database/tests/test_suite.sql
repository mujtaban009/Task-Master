-- ============================================================================
-- Phase 1: Database Test Suite (Direct PostgreSQL Terminal Execution)
-- Target Database: todo_app
-- ============================================================================

\echo '----------------------------------------------------------------------'
\echo 'TEST 1: Retrieve All Users'
\echo '----------------------------------------------------------------------'
SELECT id, full_name, email, role, is_active FROM users ORDER BY created_at ASC;

\echo '----------------------------------------------------------------------'
\echo 'TEST 2: Insert Multiple Tasks for Different Users'
\echo '----------------------------------------------------------------------'
INSERT INTO tasks (title, description, user_id, priority, status)
VALUES ('Ad-hoc Task for Alice', 'Quick reminder task', 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 'low', 'pending')
RETURNING id, title, user_id, status, priority;

\echo '----------------------------------------------------------------------'
\echo 'TEST 3: Retrieve Tasks Belonging Exclusively to a Specific User (Alice)'
\echo '----------------------------------------------------------------------'
SELECT id, title, status, priority, due_date
FROM tasks
WHERE user_id = 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22'
ORDER BY created_at DESC;

\echo '----------------------------------------------------------------------'
\echo 'TEST 4: Update Task Title, Priority, and Status'
\echo '----------------------------------------------------------------------'
UPDATE tasks
SET title = 'Write Exhaustive Pytest Tests',
    priority = 'high',
    status = 'in_progress'
WHERE id = '33333333-3333-3333-3333-333333333333'
RETURNING id, title, priority, status, updated_at;

\echo '----------------------------------------------------------------------'
\echo 'TEST 5: Mark Task as Completed (Testing completed_at constraint compliance)'
\echo '----------------------------------------------------------------------'
UPDATE tasks
SET status = 'completed',
    completed_at = CURRENT_TIMESTAMP
WHERE id = '33333333-3333-3333-3333-333333333333'
RETURNING id, title, status, completed_at, updated_at;

\echo '----------------------------------------------------------------------'
\echo 'TEST 6: Filter Tasks by Status and Priority'
\echo '----------------------------------------------------------------------'
SELECT id, user_id, title, status, priority
FROM tasks
WHERE status = 'in_progress' AND priority = 'high';

\echo '----------------------------------------------------------------------'
\echo 'TEST 7: Retrieve Tasks by Due Date Range'
\echo '----------------------------------------------------------------------'
SELECT id, title, due_date, status
FROM tasks
WHERE due_date >= CURRENT_TIMESTAMP
ORDER BY due_date ASC;

\echo '----------------------------------------------------------------------'
\echo 'TEST 8: Delete a Specific Task'
\echo '----------------------------------------------------------------------'
DELETE FROM tasks
WHERE title = 'Ad-hoc Task for Alice'
RETURNING id, title;

\echo '----------------------------------------------------------------------'
\echo 'TEST 9: Negative Test - Reject Invalid Foreign Key'
\echo 'Expected: Foreign key violation error (fk_tasks_user_id)'
\echo '----------------------------------------------------------------------'
DO $$
BEGIN
    INSERT INTO tasks (user_id, title, status)
    VALUES ('ffffffff-ffff-ffff-ffff-ffffffffffff', 'Ghost Task', 'pending');
    RAISE EXCEPTION 'UNEXPECTED: Foreign key constraint did not trigger!';
EXCEPTION
    WHEN foreign_key_violation THEN
        RAISE NOTICE 'SUCCESS: Invalid foreign key was rejected as expected. (%)', SQLERRM;
END $$;

\echo '----------------------------------------------------------------------'
\echo 'TEST 10: Negative Test - Reject Duplicate Email (Case-Insensitive)'
\echo 'Expected: Unique constraint violation (uq_users_email_lower)'
\echo '----------------------------------------------------------------------'
DO $$
BEGIN
    INSERT INTO users (full_name, email, password_hash, role)
    VALUES ('Alice Impersonator', 'ALICE@EXAMPLE.COM', '$2b$12$e8kVO7zM02rZ9E7X9qH39OS3Dvh1.iS43jT9.Q8yL2XGz67F/V71m', 'user');
    RAISE EXCEPTION 'UNEXPECTED: Duplicate email was permitted!';
EXCEPTION
    WHEN unique_violation THEN
        RAISE NOTICE 'SUCCESS: Duplicate case-insensitive email was rejected as expected. (%)', SQLERRM;
END $$;

\echo '----------------------------------------------------------------------'
\echo 'TEST 11: Negative Test - Reject Invalid Role and Invalid Task Status'
\echo '----------------------------------------------------------------------'
DO $$
BEGIN
    INSERT INTO users (full_name, email, password_hash, role)
    VALUES ('Invalid Role User', 'badrole@example.com', 'dummy_hash', 'superuser'::user_role);
    RAISE EXCEPTION 'UNEXPECTED: Invalid enum role was accepted!';
EXCEPTION
    WHEN invalid_text_representation THEN
        RAISE NOTICE 'SUCCESS: Invalid role enum was rejected as expected. (%)', SQLERRM;
END $$;

DO $$
BEGIN
    INSERT INTO tasks (user_id, title, status, completed_at)
    VALUES ('b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 'Incomplete Task Claiming Completed Date', 'pending', CURRENT_TIMESTAMP);
    RAISE EXCEPTION 'UNEXPECTED: Invalid status/completed_at combination was accepted!';
EXCEPTION
    WHEN check_violation THEN
        RAISE NOTICE 'SUCCESS: Invalid status/completed_at check constraint was rejected as expected. (%)', SQLERRM;
END $$;

\echo '----------------------------------------------------------------------'
\echo 'TEST 12: Foreign-Key Cascade Deletion Behavior'
\echo 'Verify that deleting Bob also cascades and deletes Bob tasks'
\echo '----------------------------------------------------------------------'
BEGIN;
    DELETE FROM users WHERE email = 'bob@example.com';
    SELECT count(*) AS remaining_tasks_for_bob FROM tasks WHERE user_id = 'c0eebc99-9c0b-4ef8-bb6d-6bb9bd380a33';
ROLLBACK;
\echo 'Rollback executed. Bob and Bob tasks preserved.'

\echo '----------------------------------------------------------------------'
\echo 'TEST 13: Transaction Atomicity & Rollback'
\echo '----------------------------------------------------------------------'
BEGIN;
    INSERT INTO tasks (user_id, title, status)
    VALUES ('b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22', 'Temporary Task in Aborted Tx', 'pending');
ROLLBACK;

SELECT count(*) AS should_be_zero 
FROM tasks 
WHERE title = 'Temporary Task in Aborted Tx';

\echo '----------------------------------------------------------------------'
\echo 'TEST 14: Inspect Index Usage with EXPLAIN ANALYZE'
\echo '----------------------------------------------------------------------'
EXPLAIN ANALYZE
SELECT id, title, status, priority, created_at
FROM tasks
WHERE user_id = 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a22'
  AND status = 'in_progress'
ORDER BY created_at DESC;

EXPLAIN ANALYZE
SELECT id, full_name, email
FROM users
WHERE LOWER(email) = 'alice@example.com' AND is_active = TRUE;

