-- Test migration that will fail to verify rollback functionality
-- This migration intentionally contains a syntax error

-- This will fail immediately: invalid SQL syntax
SELECT * FROM nonexistent_table_that_does_not_exist;
