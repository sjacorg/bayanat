-- Create update_history table for system update audit log
-- Tracks all system update attempts with version, user, status, and timestamp
-- Both successful and failed updates are recorded for complete audit trail

CREATE TABLE IF NOT EXISTS update_history (
    id SERIAL PRIMARY KEY,
    version_from VARCHAR(50),
    version_to VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'success',
    user_id INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE
);

-- Add index for faster queries on created_at for history sorting
CREATE INDEX IF NOT EXISTS idx_update_history_created_at ON update_history(created_at DESC);

-- Add index on user_id for user-based queries
CREATE INDEX IF NOT EXISTS idx_update_history_user_id ON update_history(user_id);

