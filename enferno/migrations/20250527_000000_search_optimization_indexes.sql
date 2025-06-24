-- Migration: Comprehensive Search Optimization Indexes
-- Date: 2025-05-27
-- Description: Adds all missing indexes for search performance optimization
-- Combines multiple previous migrations:
--   - add_search_foreign_key_indexes.sql (bulletins)
--   - add_actor_search_foreign_key_indexes.sql
--   - add_incident_search_foreign_key_indexes.sql
--   - add_actor_tags_gin_index.sql
--   - add_missing_critical_indexes.sql

-- ===============================================
-- BULLETIN SEARCH INDEXES
-- ===============================================

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

-- Add index for bulletin status field (heavily used in search filters)
-- This is used for status filtering like q.statuses = ["Machine Created"]
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bulletin_status ON bulletin(status);

-- Add GIN index for tags array field (used for tag-based searches)
-- This supports both array operations and text search within tags
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bulletin_tags_gin ON bulletin USING gin(tags);

-- Add composite index for common filter combinations
-- This covers the common pattern: unassigned + status filtering
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bulletin_status_assigned 
ON bulletin(status, assigned_to_id);

-- ===============================================
-- ACTOR SEARCH INDEXES
-- ===============================================

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

-- Add GIN index for actor tags to improve search performance
-- This index uses array_ops operator class for efficient array operations
CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_actor_tags ON actor USING gin (tags array_ops);

-- ===============================================
-- INCIDENT SEARCH INDEXES
-- ===============================================

-- Add indexes for Incident search-related foreign keys
-- These are used for assigned user and reviewer searches (q.assigned, q.reviewer)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_incident_assigned_to_id ON incident(assigned_to_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_incident_first_peer_reviewer_id ON incident(first_peer_reviewer_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_incident_second_peer_reviewer_id ON incident(second_peer_reviewer_id);

-- Add indexes for many-to-many junction tables used in incident searches
-- These tables are heavily queried when filtering incidents by labels, locations, events, etc.

-- Incident-Labels relationship (q.labels, q.exlabels searches)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_incident_labels_label_id ON incident_labels(label_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_incident_labels_incident_id ON incident_labels(incident_id);

-- Incident-Locations relationship (q.locations, q.exlocations searches)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_incident_locations_location_id ON incident_locations(location_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_incident_locations_incident_id ON incident_locations(incident_id);

-- Incident-Events relationship (q.etype, q.elocation searches via events)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_incident_events_event_id ON incident_events(event_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_incident_events_incident_id ON incident_events(incident_id);

-- Incident-Roles relationship (q.roles searches)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_incident_roles_role_id ON incident_roles(role_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_incident_roles_incident_id ON incident_roles(incident_id);

-- Incident-Potential Violations relationship (q.potentialVCats searches)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_incident_potential_violations_potentialviolation_id ON incident_potential_violations(potentialviolation_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_incident_potential_violations_incident_id ON incident_potential_violations(incident_id);

-- Incident-Claimed Violations relationship (q.claimedVCats searches)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_incident_claimed_violations_claimedviolation_id ON incident_claimed_violations(claimedviolation_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_incident_claimed_violations_incident_id ON incident_claimed_violations(incident_id);

-- Note: Using CREATE INDEX CONCURRENTLY to avoid table locking during index creation
-- This allows the application to continue running while indexes are being built