-- Migration: Create dynamic_fields and dynamic_form_history tables, seed bulletin core fields
-- Ensures compatibility with DynamicField model and audit trail introduced in dynamic-content-fresh branch.

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
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS ix_dynamic_form_history_entity_type ON dynamic_form_history (entity_type);
CREATE INDEX IF NOT EXISTS ix_dynamic_form_history_created_at ON dynamic_form_history (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_dynamic_form_history_entity_created ON dynamic_form_history (entity_type, created_at DESC);

-- Seed core bulletin fields so existing deployments remain functional after upgrade
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
        ('title', 'Title', 'bulletin', 'text', FALSE, 'input', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 1, TRUE),
        ('sjac_title', 'SJAC Title', 'bulletin', 'text', FALSE, 'input', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 2, TRUE),
        ('description', 'Description', 'bulletin', 'long_text', FALSE, 'textarea', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 3, TRUE),
        ('tags', 'Tags', 'bulletin', 'multi_select', FALSE, 'multi_dropdown', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 4, TRUE),
        ('sources', 'Sources', 'bulletin', 'multi_select', FALSE, 'multi_dropdown', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 5, TRUE),
        ('locations', 'Locations', 'bulletin', 'multi_select', FALSE, 'multi_dropdown', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 6, TRUE),
        ('labels', 'Labels', 'bulletin', 'multi_select', FALSE, 'multi_dropdown', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 7, TRUE),
        ('ver_labels', 'Verified Labels', 'bulletin', 'multi_select', FALSE, 'multi_dropdown', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 8, TRUE),
        ('publish_date', 'Publish Date', 'bulletin', 'datetime', FALSE, 'date_picker', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 9, TRUE),
        ('documentation_date', 'Documentation Date', 'bulletin', 'datetime', FALSE, 'date_picker', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 10, TRUE),
        ('status', 'Status', 'bulletin', 'single_select', FALSE, 'dropdown', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 11, TRUE),
        ('events_section', 'Events', 'bulletin', 'html_block', FALSE, 'html_block', '{}'::jsonb, '{"html_template": "events_section"}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 20, TRUE),
        ('geo_locations', 'Geo Locations', 'bulletin', 'html_block', FALSE, 'html_block', '{}'::jsonb, '{"html_template": "geo_locations"}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 21, TRUE),
        ('global_map', 'Global Map', 'bulletin', 'html_block', FALSE, 'html_block', '{}'::jsonb, '{"html_template": "global_map"}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 22, TRUE),
        ('related_bulletins', 'Related Bulletins', 'bulletin', 'html_block', FALSE, 'html_block', '{}'::jsonb, '{"html_template": "related_bulletins"}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 23, TRUE),
        ('related_actors', 'Related Actors', 'bulletin', 'html_block', FALSE, 'html_block', '{}'::jsonb, '{"html_template": "related_actors"}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 24, TRUE),
        ('related_incidents', 'Related Incidents', 'bulletin', 'html_block', FALSE, 'html_block', '{}'::jsonb, '{"html_template": "related_incidents"}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 25, TRUE),
        ('source_link', 'Source Link', 'bulletin', 'text', FALSE, 'input', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 26, TRUE),
        ('comments', 'Comments', 'bulletin', 'long_text', FALSE, 'textarea', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 27, TRUE)
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

COMMIT;

-- Rollback script:
/*
BEGIN;
DROP TABLE IF EXISTS dynamic_form_history;
DROP TABLE IF EXISTS dynamic_fields;
COMMIT;
*/
