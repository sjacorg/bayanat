-- Add GIN index for actor tags to improve search performance
-- This index uses array_ops operator class for efficient array operations

CREATE INDEX CONCURRENTLY ix_actor_tags ON actor USING gin (tags array_ops);

-- Rollback script:
/*
-- Drop the GIN index for actor tags
DROP INDEX IF EXISTS ix_actor_tags;
*/ 