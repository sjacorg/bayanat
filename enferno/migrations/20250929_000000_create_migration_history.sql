-- Create migration_history table for automatic update system
-- This migration should be applied manually during the automatic update feature deployment

CREATE TABLE IF NOT EXISTS migration_history (
    id SERIAL PRIMARY KEY,
    migration_file VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE
);

-- Add index for faster lookups
CREATE INDEX IF NOT EXISTS idx_migration_history_file ON migration_history(migration_file);

-- Add comment for documentation
COMMENT ON TABLE migration_history IS 'Tracks applied SQL migrations for automatic update system';
COMMENT ON COLUMN migration_history.migration_file IS 'Filename of the applied migration (must be unique)';
COMMENT ON COLUMN migration_history.created_at IS 'When this migration was applied';
COMMENT ON COLUMN migration_history.deleted IS 'Soft delete flag (for rollback tracking in future)';