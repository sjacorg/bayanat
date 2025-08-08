-- Migration: Create notification table

-- Create notification table
CREATE TABLE IF NOT EXISTS notification (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title VARCHAR NOT NULL,
    message TEXT NOT NULL,
    category VARCHAR NOT NULL DEFAULT 'Update',
    read_status BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,
    is_urgent BOOLEAN DEFAULT FALSE,
    
    -- Email delivery tracking fields
    email_enabled BOOLEAN DEFAULT FALSE,
    email_sent BOOLEAN DEFAULT FALSE,
    email_sent_at TIMESTAMP,
    
    -- Base columns from BaseMixin
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS ix_notification_user_id ON notification (user_id);
CREATE INDEX IF NOT EXISTS ix_notification_user_read ON notification (user_id, read_status);
CREATE INDEX IF NOT EXISTS ix_notification_user_type ON notification (user_id, category);

-- Add foreign key constraint
ALTER TABLE notification 
ADD CONSTRAINT fk_notification_user_id 
FOREIGN KEY (user_id) REFERENCES "user"(id);

-- Rollback script:
/*
DROP TABLE notification;
*/
