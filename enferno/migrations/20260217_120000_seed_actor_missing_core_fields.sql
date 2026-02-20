-- Migration: Seed missing actor core fields (sources, labels, ver_labels)
-- These fields are referenced in ActorSearchBox.js but were not seeded in the
-- initial dynamic_fields migration, causing them to be hidden in the search dialog.

BEGIN;

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
        ('sources',    'Sources',         'actor', 'select', false, 'dropdown', '{"allow_multiple": true}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 29, true),
        ('labels',     'Labels',          'actor', 'select', false, 'dropdown', '{"allow_multiple": true}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 30, true),
        ('ver_labels', 'Verified Labels', 'actor', 'select', false, 'dropdown', '{"allow_multiple": true}'::jsonb, '{"width": "w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 31, true)
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

-- Rollback:
/*
BEGIN;
DELETE FROM dynamic_fields WHERE entity_type = 'actor' AND name IN ('sources', 'labels', 'ver_labels') AND core = TRUE;
COMMIT;
*/
