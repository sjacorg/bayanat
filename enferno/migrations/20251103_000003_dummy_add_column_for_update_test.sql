-- Dummy migration to test the automatic update system
-- Safely adds a nullable column to an existing table and annotates it

-- Choose a low-risk internal table (not exposed to users)                                                                                                                                                                                                                                                                                                                                                                                                                                              
-- Add a nullable column so it won't affect inserts/updates
ALTER TABLE IF EXISTS migration_history
    ADD COLUMN IF NOT EXISTS dummy_update_test_note VARCHAR(255);

COMMENT ON COLUMN migration_history.dummy_update_test_note IS 'Temporary column added by dummy migration for update pipeline testing';

-- Rollback (manual):                                                       
-- ALTER TABLE IF EXISTS migration_history DROP COLUMN IF EXISTS dummy_update_test_note;


