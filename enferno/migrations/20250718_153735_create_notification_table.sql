-- Migration: Create notification table

-- Create notification table
CREATE TABLE IF NOT EXISTS notification (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title VARCHAR NOT NULL,
    message TEXT NOT NULL,
    notification_type VARCHAR NOT NULL DEFAULT 'general',
    read_status BOOLEAN DEFAULT FALSE,
    delivery_method VARCHAR NOT NULL DEFAULT 'internal',
    read_at TIMESTAMP,
    is_urgent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS ix_notification_user_id ON notification (user_id);
CREATE INDEX IF NOT EXISTS ix_notification_user_read ON notification (user_id, read_status);
CREATE INDEX IF NOT EXISTS ix_notification_user_type ON notification (user_id, notification_type);

-- Add foreign key constraint
ALTER TABLE notification 
ADD CONSTRAINT fk_notification_user_id 
FOREIGN KEY (user_id) REFERENCES "user"(id);

-- Rollback script:
/*
DROP TABLE notification;
*/