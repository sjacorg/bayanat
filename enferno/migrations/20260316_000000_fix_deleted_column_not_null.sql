-- Fix deleted column: set NULL values to FALSE, add NOT NULL constraint and default.
-- This affects all tables inheriting from BaseMixin.

BEGIN;

DO $$
DECLARE
    tbl TEXT;
    tables TEXT[] := ARRAY[
        'activity', 'actor', 'actor_history', 'actor_profile', 'app_config',
        'atoa', 'atoa_info', 'atob', 'atob_info', 'btob', 'btob_info',
        'bulletin', 'bulletin_history', 'claimed_violation', 'countries',
        'dialects', 'dynamic_fields', 'dynamic_form_history', 'ethnographies',
        'event', 'eventtype', 'extraction', 'geo_location', 'geo_location_types',
        'id_number_types', 'incident', 'incident_history', 'itoa', 'itoa_info',
        'itob', 'itob_info', 'itoi', 'itoi_info', 'label', 'location',
        'location_admin_level', 'location_history', 'location_type', 'media',
        'media_categories', 'notification', 'potential_violation', 'query',
        'role', 'sessions', 'settings', 'source', 'user', 'workflow_statuses'
    ];
BEGIN
    FOREACH tbl IN ARRAY tables LOOP
        EXECUTE format('UPDATE %I SET deleted = FALSE WHERE deleted IS NULL', tbl);
        EXECUTE format('ALTER TABLE %I ALTER COLUMN deleted SET DEFAULT FALSE', tbl);
        EXECUTE format('ALTER TABLE %I ALTER COLUMN deleted SET NOT NULL', tbl);
    END LOOP;
END $$;

COMMIT;
