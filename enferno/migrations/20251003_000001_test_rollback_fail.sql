-- Test migration that will fail to verify rollback functionality
-- This migration intentionally contains an error to test automatic rollback

BEGIN;

-- This will fail: trying to add NOT NULL column without default value to existing table
ALTER TABLE "user" ADD COLUMN test_rollback_column VARCHAR(255) NOT NULL;

-- Record migration (will never reach here due to failure above)
INSERT INTO migration_history (version, applied_at, success, error_message)
VALUES ('20251003_000001_test_rollback_fail', CURRENT_TIMESTAMP, true, NULL);

COMMIT;
