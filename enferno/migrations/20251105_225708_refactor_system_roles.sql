-- Migration: Refactor System Roles
-- Add new 'View' role, rename existing system roles, and assign View role to users without roles

-- 1. Rename existing roles
UPDATE role SET name = 'Moderator' WHERE name = 'Mod';
UPDATE role SET name = 'Analyst' WHERE name = 'DA';

-- 2. Add new 'View' role (read-only permissions)
INSERT INTO role (name, description, view_simple_history, view_bulletin, edit_bulletin, delete_bulletin)
VALUES ('View', 'System Role', true, true, false, false)
ON CONFLICT DO NOTHING;

-- 3. Assign View role to active users without any roles
INSERT INTO roles_users (user_id, role_id)
SELECT u.id, r.id
FROM "user" u
CROSS JOIN role r
WHERE r.name = 'View'
  AND u.active = true
  AND NOT EXISTS (
    SELECT 1 FROM roles_users ru WHERE ru.user_id = u.id
  );

-- Verify changes
SELECT id, name, description FROM role ORDER BY id;
SELECT u.id, u.username, u.active, COUNT(ru.role_id) as role_count
FROM "user" u
LEFT JOIN roles_users ru ON u.id = ru.user_id
GROUP BY u.id, u.username, u.active
ORDER BY role_count, u.id;

-- Rollback script:
/*
UPDATE role SET name = 'Mod' WHERE name = 'Moderator';
UPDATE role SET name = 'DA' WHERE name = 'Analyst';
DELETE FROM roles_users
WHERE role_id = (SELECT id FROM role WHERE name = 'View')
  AND user_id IN (
    SELECT u.id FROM "user" u
    WHERE u.active = true
    AND (SELECT COUNT(*) FROM roles_users WHERE user_id = u.id) = 1
  );
DELETE FROM role WHERE name = 'View';
*/
