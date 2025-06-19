-- Migration: Add missing foreign key indexes for Actor search performance
-- Date: 2025-05-27
-- Description: Adds indexes for foreign keys that are heavily used in Actor search functionality
-- Based on analysis of ActorSearchBox.js search patterns

-- Add indexes for Actor search-related foreign keys
-- These are used for assigned user and reviewer searches (q.assigned, q.reviewer)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_actor_assigned_to_id ON actor(assigned_to_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_actor_first_peer_reviewer_id ON actor(first_peer_reviewer_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_actor_second_peer_reviewer_id ON actor(second_peer_reviewer_id);

-- Add index for Actor origin location search (q.originLocations)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_actor_origin_place_id ON actor(origin_place_id);

-- Add indexes for many-to-many junction tables used in actor searches
-- These tables are heavily queried when filtering actors by sources, labels, events, etc.

-- Actor-Sources relationship (q.sources, q.exsources searches)
-- Note: actor_sources uses actor_profile_id, not actor_id
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_actor_sources_source_id ON actor_sources(source_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_actor_sources_actor_profile_id ON actor_sources(actor_profile_id);

-- Actor-Labels relationship (q.labels, q.exlabels searches)  
-- Note: actor_labels uses actor_profile_id, not actor_id
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_actor_labels_label_id ON actor_labels(label_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_actor_labels_actor_profile_id ON actor_labels(actor_profile_id);

-- Actor-Verified Labels relationship (q.vlabels, q.exvlabels searches)
-- Note: actor_verlabels uses actor_profile_id, not actor_id
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_actor_verlabels_label_id ON actor_verlabels(label_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_actor_verlabels_actor_profile_id ON actor_verlabels(actor_profile_id);

-- Actor-Events relationship (q.etype, q.elocation searches via events)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_actor_events_event_id ON actor_events(event_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_actor_events_actor_id ON actor_events(actor_id);

-- Actor-Roles relationship (if roles are searched)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_actor_roles_role_id ON actor_roles(role_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_actor_roles_actor_id ON actor_roles(actor_id);

-- Note: Using CREATE INDEX CONCURRENTLY to avoid table locking during index creation
-- This allows the application to continue running while indexes are being built 