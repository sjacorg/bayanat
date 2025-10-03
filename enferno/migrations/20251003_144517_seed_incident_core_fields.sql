-- Migration: Seed incident core fields
-- Adds core field definitions for incident entity to support dynamic field builder UI.

BEGIN;

-- Seed core incident fields based on incident_dialog.html
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
        ('title', 'Title', 'incident', 'text', FALSE, 'input', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 1, TRUE),
        ('description', 'Description', 'incident', 'long_text', FALSE, 'textarea', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 2, TRUE),
        ('potential_violations', 'Potential Violations', 'incident', 'multi_select', FALSE, 'multi_dropdown', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 3, TRUE),
        ('claimed_violations', 'Claimed Violations', 'incident', 'multi_select', FALSE, 'multi_dropdown', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 4, TRUE),
        ('labels', 'Labels', 'incident', 'multi_select', FALSE, 'multi_dropdown', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 5, TRUE),
        ('locations', 'Locations', 'incident', 'multi_select', FALSE, 'multi_dropdown', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 6, TRUE),
        ('events_section', 'Events', 'incident', 'html_block', FALSE, 'html_block', '{}'::jsonb, '{"html_template": "events_section"}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 7, TRUE),
        ('related_bulletins', 'Related Bulletins', 'incident', 'html_block', FALSE, 'html_block', '{}'::jsonb, '{"html_template": "related_bulletins"}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 8, TRUE),
        ('related_actors', 'Related Actors', 'incident', 'html_block', FALSE, 'html_block', '{}'::jsonb, '{"html_template": "related_actors"}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 9, TRUE),
        ('related_incidents', 'Related Incidents', 'incident', 'html_block', FALSE, 'html_block', '{}'::jsonb, '{"html_template": "related_incidents"}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 10, TRUE),
        ('comments', 'Comments', 'incident', 'long_text', FALSE, 'textarea', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, TRUE, 11, TRUE),
        ('status', 'Status', 'incident', 'single_select', FALSE, 'dropdown', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[{"label": "Draft", "value": "draft"}, {"label": "Published", "value": "published"}, {"label": "Archived", "value": "archived"}]'::jsonb, TRUE, 12, TRUE)
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
DELETE FROM dynamic_fields WHERE entity_type = 'incident' AND core = TRUE;
COMMIT;
*/
