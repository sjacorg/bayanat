-- Migration: Refactor System Roles
-- Add new 'View' role and rename existing system roles

-- 1. Rename existing roles
UPDATE role SET name = 'Moderator' WHERE name = 'Mod';
UPDATE role SET name = 'Analyst' WHERE name = 'DA';

-- 2. Add new 'View' role (read-only permissions)
INSERT INTO role (name, description, view_simple_history, view_bulletin, edit_bulletin, delete_bulletin)
VALUES ('View', 'System Role', true, true, false, false)
ON CONFLICT DO NOTHING;

-- Verify changes and display the results
SELECT id, name, description FROM role ORDER BY id;

-- Rollback script:
/*
UPDATE role SET name = 'Mod' WHERE name = 'Moderator';
UPDATE role SET name = 'DA' WHERE name = 'Analyst';
DELETE FROM role WHERE name = 'View';
*/
