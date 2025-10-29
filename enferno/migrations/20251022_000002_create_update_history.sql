-- Create update_history table for system update audit log
-- Tracks completed system updates with version and timestamp

CREATE TABLE IF NOT EXISTS update_history (
    id SERIAL PRIMARY KEY,
    version_to VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE
);

-- Add index for faster queries on created_at for history sorting
CREATE INDEX IF NOT EXISTS idx_update_history_created_at ON update_history(created_at DESC);

