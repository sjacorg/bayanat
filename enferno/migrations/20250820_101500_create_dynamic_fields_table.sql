-- Migration: Create dynamic_fields and dynamic_form_history tables, seed core fields, create initial snapshots
-- Creates tables for dynamic form builder, seeds core fields for bulletin, incident, and actor entities.
-- Initial snapshots provide baseline "factory settings" for comparison and revert functionality.

BEGIN;

CREATE TABLE IF NOT EXISTS dynamic_fields (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    title VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    field_type VARCHAR(20) NOT NULL,
    searchable BOOLEAN NOT NULL DEFAULT FALSE,
    ui_component VARCHAR(20),
    schema_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    ui_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    validation_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    options JSONB NOT NULL DEFAULT '[]'::jsonb,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    core BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_field_name_entity UNIQUE (name, entity_type)
);

CREATE INDEX IF NOT EXISTS ix_dynamic_fields_entity_type ON dynamic_fields (entity_type);
CREATE INDEX IF NOT EXISTS ix_dynamic_fields_entity_active ON dynamic_fields (entity_type, active);
CREATE INDEX IF NOT EXISTS ix_dynamic_fields_entity_core ON dynamic_fields (entity_type, core);
CREATE INDEX IF NOT EXISTS ix_dynamic_fields_entity_sort ON dynamic_fields (entity_type, sort_order);

-- Create dynamic_form_history table for audit trail
CREATE TABLE IF NOT EXISTS dynamic_form_history (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,
    fields_snapshot JSONB NOT NULL,
    user_id INTEGER REFERENCES "user"(id),
    
    -- Base columns from BaseMixin
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_dynamic_form_history_entity_type ON dynamic_form_history (entity_type);
CREATE INDEX IF NOT EXISTS ix_dynamic_form_history_created_at ON dynamic_form_history (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_dynamic_form_history_entity_created ON dynamic_form_history (entity_type, created_at DESC);

-- Seed core fields for bulletin, incident, and actor entities
INSERT INTO dynamic_fields (
    name,
    title,
    entity_type,
    field_type,
    searchable,
    ui_component,
    schema_config,
    ui_config,
    validation_config,
    options,
    active,
    sort_order,
    core
)
SELECT
    payload.name,
    payload.title,
    payload.entity_type,
    payload.field_type,
    payload.searchable,
    payload.ui_component,
    payload.schema_config,
    payload.ui_config,
    payload.validation_config,
    payload.options,
    payload.active,
    payload.sort_order,
    payload.core
FROM (
    VALUES
        ('name', 'Name', 'actor', 'text', false, 'input', '{}'::jsonb, '{"width": "w-100"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 1, true),
        ('first_name', 'First Name', 'actor', 'text', false, 'input', '{}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 2, true),
        ('middle_name', 'Middle Name', 'actor', 'text', false, 'input', '{}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 3, true),
        ('last_name', 'Last Name', 'actor', 'text', false, 'input', '{}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 4, true),
        ('nickname', 'Nickname', 'actor', 'text', false, 'input', '{}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 5, true),
        ('father_name', 'Father Name', 'actor', 'text', false, 'input', '{}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 6, true),
        ('mother_name', 'Mother Name', 'actor', 'text', false, 'input', '{}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 7, true),
        ('sex', 'Sex', 'actor', 'select', false, 'dropdown', '{"allow_multiple": false}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 8, true),
        ('age', 'Age', 'actor', 'number', false, 'number_input', '{}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 9, true),
        ('civilian', 'Civilian', 'actor', 'select', false, 'dropdown', '{"allow_multiple": false}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 10, true),
        ('origin_place', 'Origin Place', 'actor', 'select', false, 'dropdown', '{"allow_multiple": true}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 11, true),
        ('occupation', 'Occupation', 'actor', 'text', false, 'input', '{}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 12, true),
        ('position', 'Position', 'actor', 'text', false, 'input', '{}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 13, true),
        ('family_status', 'Family Status', 'actor', 'select', false, 'dropdown', '{"allow_multiple": false}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 14, true),
        ('no_children', 'Number of Children', 'actor', 'number', false, 'number_input', '{}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 15, true),
        ('ethnographies', 'Ethnographies', 'actor', 'select', false, 'dropdown', '{"allow_multiple": true}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 16, true),
        ('nationalities', 'Nationalities', 'actor', 'select', false, 'dropdown', '{"allow_multiple": true}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 17, true),
        ('dialects', 'Dialects', 'actor', 'select', false, 'dropdown', '{"allow_multiple": true}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 18, true),
        ('tags', 'Tags', 'actor', 'select', false, 'dropdown', '{"allow_multiple": true}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 19, true),
        ('id_number', 'ID Number', 'actor', 'text', false, 'input', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 20, true),
        ('actor_profiles', 'Actor Profiles', 'actor', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template": "actor_profiles"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 21, true),
        ('events_section', 'Events', 'actor', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template": "events_section"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 22, true),
        ('related_bulletins', 'Related Bulletins', 'actor', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template": "related_bulletins"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 23, true),
        ('related_actors', 'Related Actors', 'actor', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template": "related_actors"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 24, true),
        ('related_incidents', 'Related Incidents', 'actor', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template": "related_incidents"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 25, true),
        ('medias', 'Media', 'actor', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template": "medias"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 26, true),
        ('comments', 'Comments', 'actor', 'long_text', false, 'textarea', '{}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 27, true),
        ('status', 'Status', 'actor', 'select', false, 'dropdown', '{"allow_multiple": false}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 28, true),
        ('title', 'Original Title', 'bulletin', 'text', false, 'input', '{}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 1, true),
        ('sjac_title', 'Title', 'bulletin', 'text', false, 'input', '{}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 2, true),
        ('tags', 'Tags', 'bulletin', 'select', false, 'dropdown', '{"allow_multiple": true}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 3, true),
        ('sources', 'Sources', 'bulletin', 'select', false, 'dropdown', '{"allow_multiple": true}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 4, true),
        ('description', 'Description', 'bulletin', 'long_text', false, 'textarea', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 5, true),
        ('labels', 'Labels', 'bulletin', 'select', false, 'dropdown', '{"allow_multiple": true}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 6, true),
        ('ver_labels', 'Verified Labels', 'bulletin', 'select', false, 'dropdown', '{"allow_multiple": true}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 7, true),
        ('locations', 'Locations', 'bulletin', 'select', false, 'dropdown', '{"allow_multiple": true}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 8, true),
        ('global_map', 'Global Map', 'bulletin', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template": "global_map"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 9, true),
        ('events_section', 'Events', 'bulletin', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template": "events_section"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 10, true),
        ('geo_locations', 'Geo Locations', 'bulletin', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template": "geo_locations"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 11, true),
        ('related_bulletins', 'Related Bulletins', 'bulletin', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template": "related_bulletins"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 12, true),
        ('related_actors', 'Related Actors', 'bulletin', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template": "related_actors"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 13, true),
        ('related_incidents', 'Related Incidents', 'bulletin', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template": "related_incidents"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 14, true),
        ('source_link', 'Source Link', 'bulletin', 'text', false, 'input', '{}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 15, true),
        ('publish_date', 'Publish Date', 'bulletin', 'datetime', false, 'date_picker', '{}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 16, true),
        ('documentation_date', 'Documentation Date', 'bulletin', 'datetime', false, 'date_picker', '{}'::jsonb, '{"align": "right", "width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 17, true),
        ('comments', 'Comments', 'bulletin', 'long_text', false, 'textarea', '{}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 18, true),
        ('status', 'Status', 'bulletin', 'select', false, 'dropdown', '{"allow_multiple": false}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 19, true),
        ('title', 'Title', 'incident', 'text', false, 'input', '{}'::jsonb, '{"width": "w-100"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 1, true),
        ('description', 'Description', 'incident', 'long_text', false, 'textarea', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 2, true),
        ('potential_violations', 'Potential Violations', 'incident', 'select', false, 'dropdown', '{"allow_multiple": true}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 3, true),
        ('claimed_violations', 'Claimed Violations', 'incident', 'select', false, 'dropdown', '{"allow_multiple": true}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 4, true),
        ('labels', 'Labels', 'incident', 'select', false, 'dropdown', '{"allow_multiple": true}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 5, true),
        ('locations', 'Locations', 'incident', 'select', false, 'dropdown', '{"allow_multiple": true}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 6, true),
        ('events_section', 'Events', 'incident', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template": "events_section"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 7, true),
        ('related_bulletins', 'Related Bulletins', 'incident', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template": "related_bulletins"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 8, true),
        ('related_actors', 'Related Actors', 'incident', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template": "related_actors"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 9, true),
        ('related_incidents', 'Related Incidents', 'incident', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template": "related_incidents"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 10, true),
        ('comments', 'Comments', 'incident', 'long_text', false, 'textarea', '{}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 11, true),
        ('status', 'Status', 'incident', 'select', false, 'dropdown', '{"allow_multiple": false}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 12, true)
) AS payload (
    name,
    title,
    entity_type,
    field_type,
    searchable,
    ui_component,
    schema_config,
    ui_config,
    validation_config,
    options,
    active,
    sort_order,
    core
)
WHERE NOT EXISTS (
    SELECT 1
    FROM dynamic_fields df
    WHERE df.name = payload.name
      AND df.entity_type = payload.entity_type
);

-- Create initial form history snapshots for each entity type
INSERT INTO dynamic_form_history (entity_type, fields_snapshot, user_id, created_at, updated_at, deleted)
SELECT
    df.entity_type,
    jsonb_agg(
        jsonb_build_object(
            'id', df.id,
            'name', df.name,
            'title', df.title,
            'entity_type', df.entity_type,
            'field_type', df.field_type,
            'searchable', df.searchable,
            'ui_component', df.ui_component,
            'schema_config', df.schema_config,
            'ui_config', df.ui_config,
            'validation_config', df.validation_config,
            'options', df.options,
            'active', df.active,
            'sort_order', df.sort_order,
            'core', df.core
        ) ORDER BY df.sort_order
    ),
    NULL,
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    FALSE
FROM dynamic_fields df
WHERE df.active = TRUE AND df.deleted = FALSE AND df.core = TRUE
  AND NOT EXISTS (
      SELECT 1 FROM dynamic_form_history h WHERE h.entity_type = df.entity_type
  )
GROUP BY df.entity_type;

COMMIT;

-- Rollback script:
/*
BEGIN;
DROP TABLE IF EXISTS dynamic_form_history;
DROP TABLE IF EXISTS dynamic_fields;
COMMIT;
*/
