-- Migration: Add missing critical indexes for query performance
-- Date: 2025-06-20
-- Description: Adds missing status and tags indexes that were not included in previous foreign key migrations
-- These indexes are critical for Query 346 and other bulletin search operations

-- Add index for bulletin status field (heavily used in search filters)
-- This is used for status filtering like q.statuses = ["Machine Created"]
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bulletin_status ON bulletin(status);

-- Add GIN index for tags array field (used for tag-based searches)
-- This supports both array operations and text search within tags
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bulletin_tags_gin ON bulletin USING gin(tags);

-- Add composite index for common filter combinations to speed up Query 346 type searches
-- This covers the common pattern: unassigned + specific status
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bulletin_unassigned_machine_created 
ON bulletin(status, assigned_to_id) 
WHERE assigned_to_id IS NULL AND status = 'Machine Created';

-- Note: Using CREATE INDEX CONCURRENTLY to avoid table locking during index creation
-- This allows the application to continue running while indexes are being built