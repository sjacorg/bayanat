-- Migration: Add missing foreign key indexes for Incident search performance
-- Date: 2025-05-27
-- Description: Adds indexes for foreign keys that are heavily used in Incident search functionality
-- Based on analysis of IncidentSearchBox.js search patterns

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
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_incident_potential_violations_potential_violation_id ON incident_potential_violations(potential_violation_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_incident_potential_violations_incident_id ON incident_potential_violations(incident_id);

-- Incident-Claimed Violations relationship (q.claimedVCats searches)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_incident_claimed_violations_claimed_violation_id ON incident_claimed_violations(claimed_violation_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_incident_claimed_violations_incident_id ON incident_claimed_violations(incident_id);

-- Note: Using CREATE INDEX CONCURRENTLY to avoid table locking during index creation
-- This allows the application to continue running while indexes are being built 