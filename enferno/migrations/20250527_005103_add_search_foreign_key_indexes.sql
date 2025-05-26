-- Migration: Add missing foreign key indexes for search performance
-- Date: 2025-05-27
-- Description: Adds indexes for foreign keys that are heavily used in search functionality
-- Based on analysis of BulletinSearchBox.js search patterns

-- Add indexes for Bulletin search-related foreign keys
-- These are used for assigned user and reviewer searches (q.assigned, q.reviewer)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bulletin_assigned_to_id ON bulletin(assigned_to_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bulletin_first_peer_reviewer_id ON bulletin(first_peer_reviewer_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bulletin_second_peer_reviewer_id ON bulletin(second_peer_reviewer_id);

-- Add indexes for Event search-related foreign keys  
-- These are used for event type and event location searches
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_event_location_id ON event(location_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_event_eventtype_id ON event(eventtype_id);

-- Add indexes for many-to-many junction tables used in bulletin searches
-- These tables are heavily queried when filtering bulletins by sources, labels, locations, etc.

-- Bulletin-Sources relationship (q.sources, q.exsources searches)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bulletin_sources_source_id ON bulletin_sources(source_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bulletin_sources_bulletin_id ON bulletin_sources(bulletin_id);

-- Bulletin-Labels relationship (q.labels, q.exlabels searches)  
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bulletin_labels_label_id ON bulletin_labels(label_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bulletin_labels_bulletin_id ON bulletin_labels(bulletin_id);

-- Bulletin-Verified Labels relationship (q.vlabels, q.exvlabels searches)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bulletin_verlabels_label_id ON bulletin_verlabels(label_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bulletin_verlabels_bulletin_id ON bulletin_verlabels(bulletin_id);

-- Bulletin-Locations relationship (q.locations, q.exlocations searches)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bulletin_locations_location_id ON bulletin_locations(location_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bulletin_locations_bulletin_id ON bulletin_locations(bulletin_id);

-- Bulletin-Roles relationship (q.roles searches)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bulletin_roles_role_id ON bulletin_roles(role_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bulletin_roles_bulletin_id ON bulletin_roles(bulletin_id);

-- Bulletin-Events relationship (used for event-based searches)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bulletin_events_event_id ON bulletin_events(event_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bulletin_events_bulletin_id ON bulletin_events(bulletin_id);

-- Note: Using CREATE INDEX CONCURRENTLY to avoid table locking during index creation
-- This allows the application to continue running while indexes are being built 