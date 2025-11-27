-- Migration: Add User Status Field
-- Add status enum to replace the active boolean

-- 1. Add status column
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS status VARCHAR(20);

-- 2. Migrate data from active boolean to status
-- On main branch: active=true means active, active=false means suspended
UPDATE "user" SET status = CASE
    WHEN active = true THEN 'active'
    ELSE 'suspended'
END
WHERE status IS NULL;

-- 3. Set NOT NULL constraint and default
ALTER TABLE "user" ALTER COLUMN status SET NOT NULL;
ALTER TABLE "user" ALTER COLUMN status SET DEFAULT 'active';

-- 4. Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_user_status ON "user"(status);

-- Verify migration
SELECT status, COUNT(*) as count FROM "user" GROUP BY status;

-- Rollback script:
/*
DROP INDEX IF EXISTS idx_user_status;
ALTER TABLE "user" DROP COLUMN IF EXISTS status;
*/
