"""baseline schema v3.0.0

Consolidates all legacy SQL migrations into one idempotent Alembic revision.
Safe to run on any Bayanat version (v2.4+). All statements use IF EXISTS /
IF NOT EXISTS / ON CONFLICT / exception guards so they skip work already done.

For fresh installs: create-db builds the full schema, then `flask db upgrade`
runs this (mostly no-ops) and stamps it.

For existing deployments: `flask db upgrade` applies anything missing.

Revision ID: 6bbb9e68dc26
Revises:
Create Date: 2026-03-26 16:17:37.547634

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "6bbb9e68dc26"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    # Helper: check if a column exists
    def col_exists(table, column):
        result = conn.execute(
            sa.text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = :t AND column_name = :c"
            ),
            {"t": table, "c": column},
        )
        return result.scalar() is not None

    # Helper: check if a table exists
    def table_exists(table):
        result = conn.execute(
            sa.text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_name = :t AND table_schema = 'public'"
            ),
            {"t": table},
        )
        return result.scalar() is not None

    # Helper: check if a constraint exists
    def constraint_exists(table, constraint):
        result = conn.execute(
            sa.text(
                "SELECT 1 FROM information_schema.table_constraints "
                "WHERE table_name = :t AND constraint_name = :c"
            ),
            {"t": table, "c": constraint},
        )
        return result.scalar() is not None

    # ==========================================
    # 1. Origin ID indices (replace btree with GIN trigram)
    # ==========================================
    op.execute("DROP INDEX IF EXISTS ix_actor_profile_originid")
    op.execute("DROP INDEX IF EXISTS ix_bulletin_originid")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_bulletin_originid_gin "
        "ON bulletin USING gin (originid gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_actor_profile_originid_gin "
        "ON actor_profile USING gin (originid gin_trgm_ops)"
    )

    # ==========================================
    # 2. Export: rename ref -> tags (v2.4 -> v2.9)
    # ==========================================
    if col_exists("export", "ref") and not col_exists("export", "tags"):
        op.execute("ALTER TABLE export RENAME COLUMN ref TO tags")
    if col_exists("export", "tags"):
        op.execute("UPDATE export SET tags = '{}' WHERE tags IS NULL")
        op.execute("ALTER TABLE export ALTER COLUMN tags SET NOT NULL")
        op.execute("ALTER TABLE export ALTER COLUMN tags SET DEFAULT '{}'")

    # ==========================================
    # 3. Search optimization indexes (all IF NOT EXISTS)
    # ==========================================
    _create_search_indexes(op)

    # ==========================================
    # 4. ID number types table + actor id_number migration
    # ==========================================
    if not table_exists("id_number_types"):
        op.execute(
            """
            CREATE TABLE id_number_types (
                id SERIAL PRIMARY KEY,
                title VARCHAR NOT NULL,
                title_tr VARCHAR,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted BOOLEAN DEFAULT FALSE
            )
        """
        )
        op.execute(
            """
            INSERT INTO id_number_types (title, title_tr) VALUES
                ('National ID', ''), ('Passport', ''), ('Driver License', ''),
                ('Social Security Number', ''), ('Tax ID', ''), ('Military ID', ''),
                ('Birth Certificate', ''), ('Student ID', '')
        """
        )
    else:
        # Ensure National ID with id=1 exists for the migration below
        op.execute(
            "INSERT INTO id_number_types (id, title, title_tr, created_at, updated_at, deleted) "
            "VALUES (1, 'National ID', '', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, FALSE) "
            "ON CONFLICT (id) DO NOTHING"
        )

    # Actor id_number: string -> JSONB array (only if still a string column)
    if col_exists("actor", "id_number"):
        # Check if it's already JSONB
        result = conn.execute(
            sa.text(
                "SELECT data_type FROM information_schema.columns "
                "WHERE table_name = 'actor' AND column_name = 'id_number'"
            )
        )
        row = result.fetchone()
        if row and row[0] not in ("jsonb",):
            _migrate_actor_id_number(op)

    # ==========================================
    # 5. Notification table
    # ==========================================
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS notification (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            title VARCHAR NOT NULL,
            message TEXT NOT NULL,
            category VARCHAR NOT NULL DEFAULT 'Update',
            read_status BOOLEAN DEFAULT FALSE,
            read_at TIMESTAMP,
            is_urgent BOOLEAN DEFAULT FALSE,
            email_enabled BOOLEAN DEFAULT FALSE,
            email_sent BOOLEAN DEFAULT FALSE,
            email_sent_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted BOOLEAN DEFAULT FALSE
        )
    """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_notification_user_id ON notification (user_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_notification_user_read "
        "ON notification (user_id, read_status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_notification_user_type "
        "ON notification (user_id, category)"
    )
    op.execute(
        """
        DO $$ BEGIN
            ALTER TABLE notification ADD CONSTRAINT fk_notification_user_id
            FOREIGN KEY (user_id) REFERENCES "user"(id);
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """
    )

    # ==========================================
    # 6. Dynamic fields + form history tables
    # ==========================================
    _create_dynamic_fields_tables(op)
    _seed_core_fields(conn)

    # ==========================================
    # 7. Actor meta GIN index
    # ==========================================
    op.execute("CREATE INDEX IF NOT EXISTS ix_actor_meta_gin ON actor USING gin (meta)")

    # ==========================================
    # 8. Extraction table (OCR)
    # ==========================================
    _create_extraction_table(op)

    # ==========================================
    # 9. Label constraints
    # ==========================================
    if not constraint_exists("label", "label_no_self_parent"):
        op.execute(
            "ALTER TABLE label ADD CONSTRAINT label_no_self_parent CHECK (parent_label_id != id)"
        )
    if not constraint_exists("label", "label_unique_sibling_title"):
        op.execute(
            "ALTER TABLE label ADD CONSTRAINT label_unique_sibling_title "
            "UNIQUE (title, parent_label_id)"
        )

    # ==========================================
    # 10. OCR simplification (history column, orientation on media)
    # ==========================================
    op.execute(
        "ALTER TABLE extraction ADD COLUMN IF NOT EXISTS "
        "history JSONB DEFAULT '[]'::jsonb NOT NULL"
    )
    op.execute("ALTER TABLE media ADD COLUMN IF NOT EXISTS orientation INTEGER DEFAULT 0")
    # Migrate orientation data (idempotent: overwrites with same value)
    op.execute(
        "UPDATE media SET orientation = e.orientation "
        "FROM extraction e WHERE e.media_id = media.id AND e.orientation != 0"
    )
    # Normalize statuses
    op.execute(
        "UPDATE extraction SET status = 'processed' "
        "WHERE status IN ('needs_review', 'needs_transcription')"
    )

    # ==========================================
    # 11. Normalize search_text newlines
    # ==========================================
    # Recreate generated column (DROP + ADD is idempotent for generated columns)
    if table_exists("extraction"):
        op.execute("ALTER TABLE extraction DROP COLUMN IF EXISTS search_text")
        op.execute(
            "ALTER TABLE extraction ADD COLUMN search_text text "
            "GENERATED ALWAYS AS (normalize_arabic_text(text)) STORED"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_extraction_search_text_trgm "
            "ON extraction USING GIN(search_text gin_trgm_ops)"
        )

    # ==========================================
    # 12. User can_access_media column
    # ==========================================
    op.execute('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS can_access_media BOOLEAN DEFAULT FALSE')

    # ==========================================
    # 13. Fix deleted column NOT NULL on all tables
    # ==========================================
    _fix_deleted_columns(op)


def downgrade():
    raise RuntimeError("Cannot downgrade past the baseline migration.")


# --- Helper functions ---

import sqlalchemy as sa


def _create_search_indexes(op):
    """Create all search optimization indexes (all IF NOT EXISTS)."""
    indexes = [
        # Bulletin
        "CREATE INDEX IF NOT EXISTS ix_bulletin_assigned_to_id ON bulletin(assigned_to_id)",
        "CREATE INDEX IF NOT EXISTS ix_bulletin_first_peer_reviewer_id ON bulletin(first_peer_reviewer_id)",
        "CREATE INDEX IF NOT EXISTS ix_bulletin_second_peer_reviewer_id ON bulletin(second_peer_reviewer_id)",
        "CREATE INDEX IF NOT EXISTS ix_event_location_id ON event(location_id)",
        "CREATE INDEX IF NOT EXISTS ix_event_eventtype_id ON event(eventtype_id)",
        "CREATE INDEX IF NOT EXISTS ix_bulletin_sources_source_id ON bulletin_sources(source_id)",
        "CREATE INDEX IF NOT EXISTS ix_bulletin_sources_bulletin_id ON bulletin_sources(bulletin_id)",
        "CREATE INDEX IF NOT EXISTS ix_bulletin_labels_label_id ON bulletin_labels(label_id)",
        "CREATE INDEX IF NOT EXISTS ix_bulletin_labels_bulletin_id ON bulletin_labels(bulletin_id)",
        "CREATE INDEX IF NOT EXISTS ix_bulletin_verlabels_label_id ON bulletin_verlabels(label_id)",
        "CREATE INDEX IF NOT EXISTS ix_bulletin_verlabels_bulletin_id ON bulletin_verlabels(bulletin_id)",
        "CREATE INDEX IF NOT EXISTS ix_bulletin_locations_location_id ON bulletin_locations(location_id)",
        "CREATE INDEX IF NOT EXISTS ix_bulletin_locations_bulletin_id ON bulletin_locations(bulletin_id)",
        "CREATE INDEX IF NOT EXISTS ix_bulletin_roles_role_id ON bulletin_roles(role_id)",
        "CREATE INDEX IF NOT EXISTS ix_bulletin_roles_bulletin_id ON bulletin_roles(bulletin_id)",
        "CREATE INDEX IF NOT EXISTS ix_bulletin_events_event_id ON bulletin_events(event_id)",
        "CREATE INDEX IF NOT EXISTS ix_bulletin_events_bulletin_id ON bulletin_events(bulletin_id)",
        "CREATE INDEX IF NOT EXISTS ix_bulletin_status ON bulletin(status)",
        "CREATE INDEX IF NOT EXISTS ix_bulletin_tags_gin ON bulletin USING gin(tags)",
        "CREATE INDEX IF NOT EXISTS ix_bulletin_status_assigned ON bulletin(status, assigned_to_id)",
        # Actor
        "CREATE INDEX IF NOT EXISTS ix_actor_assigned_to_id ON actor(assigned_to_id)",
        "CREATE INDEX IF NOT EXISTS ix_actor_first_peer_reviewer_id ON actor(first_peer_reviewer_id)",
        "CREATE INDEX IF NOT EXISTS ix_actor_second_peer_reviewer_id ON actor(second_peer_reviewer_id)",
        "CREATE INDEX IF NOT EXISTS ix_actor_origin_place_id ON actor(origin_place_id)",
        "CREATE INDEX IF NOT EXISTS ix_actor_sources_source_id ON actor_sources(source_id)",
        "CREATE INDEX IF NOT EXISTS ix_actor_sources_actor_profile_id ON actor_sources(actor_profile_id)",
        "CREATE INDEX IF NOT EXISTS ix_actor_labels_label_id ON actor_labels(label_id)",
        "CREATE INDEX IF NOT EXISTS ix_actor_labels_actor_profile_id ON actor_labels(actor_profile_id)",
        "CREATE INDEX IF NOT EXISTS ix_actor_verlabels_label_id ON actor_verlabels(label_id)",
        "CREATE INDEX IF NOT EXISTS ix_actor_verlabels_actor_profile_id ON actor_verlabels(actor_profile_id)",
        "CREATE INDEX IF NOT EXISTS ix_actor_events_event_id ON actor_events(event_id)",
        "CREATE INDEX IF NOT EXISTS ix_actor_events_actor_id ON actor_events(actor_id)",
        "CREATE INDEX IF NOT EXISTS ix_actor_roles_role_id ON actor_roles(role_id)",
        "CREATE INDEX IF NOT EXISTS ix_actor_roles_actor_id ON actor_roles(actor_id)",
        "CREATE INDEX IF NOT EXISTS ix_actor_tags ON actor USING gin (tags array_ops)",
        # Incident
        "CREATE INDEX IF NOT EXISTS ix_incident_assigned_to_id ON incident(assigned_to_id)",
        "CREATE INDEX IF NOT EXISTS ix_incident_first_peer_reviewer_id ON incident(first_peer_reviewer_id)",
        "CREATE INDEX IF NOT EXISTS ix_incident_second_peer_reviewer_id ON incident(second_peer_reviewer_id)",
        "CREATE INDEX IF NOT EXISTS ix_incident_labels_label_id ON incident_labels(label_id)",
        "CREATE INDEX IF NOT EXISTS ix_incident_labels_incident_id ON incident_labels(incident_id)",
        "CREATE INDEX IF NOT EXISTS ix_incident_locations_location_id ON incident_locations(location_id)",
        "CREATE INDEX IF NOT EXISTS ix_incident_locations_incident_id ON incident_locations(incident_id)",
        "CREATE INDEX IF NOT EXISTS ix_incident_events_event_id ON incident_events(event_id)",
        "CREATE INDEX IF NOT EXISTS ix_incident_events_incident_id ON incident_events(incident_id)",
        "CREATE INDEX IF NOT EXISTS ix_incident_roles_role_id ON incident_roles(role_id)",
        "CREATE INDEX IF NOT EXISTS ix_incident_roles_incident_id ON incident_roles(incident_id)",
        "CREATE INDEX IF NOT EXISTS ix_incident_potential_violations_potentialviolation_id ON incident_potential_violations(potentialviolation_id)",
        "CREATE INDEX IF NOT EXISTS ix_incident_potential_violations_incident_id ON incident_potential_violations(incident_id)",
        "CREATE INDEX IF NOT EXISTS ix_incident_claimed_violations_claimedviolation_id ON incident_claimed_violations(claimedviolation_id)",
        "CREATE INDEX IF NOT EXISTS ix_incident_claimed_violations_incident_id ON incident_claimed_violations(incident_id)",
    ]
    for stmt in indexes:
        op.execute(stmt)


def _migrate_actor_id_number(op):
    """Convert actor.id_number from string to JSONB array."""
    op.execute(
        """
        CREATE OR REPLACE FUNCTION validate_actor_id_number(id_number_data JSONB)
        RETURNS BOOLEAN AS $$
        BEGIN
            IF jsonb_typeof(id_number_data) != 'array' THEN RETURN FALSE; END IF;
            IF jsonb_array_length(id_number_data) = 0 THEN RETURN TRUE; END IF;
            RETURN (
                SELECT bool_and(
                    jsonb_typeof(elem->'type') = 'string' AND
                    jsonb_typeof(elem->'number') = 'string' AND
                    (elem->'type') IS NOT NULL AND
                    (elem->'number') IS NOT NULL AND
                    trim((elem->>'type')) != '' AND
                    trim((elem->>'number')) != '' AND
                    (elem->>'type') ~ '^[0-9]+$'
                )
                FROM jsonb_array_elements(id_number_data) AS elem
            );
        END;
        $$ LANGUAGE plpgsql IMMUTABLE
    """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS actor_id_number_backup AS
        SELECT id, id_number FROM actor
        WHERE id_number IS NOT NULL AND id_number != ''
    """
    )
    op.execute("ALTER TABLE actor ADD COLUMN id_number_temp JSONB")
    op.execute(
        """
        UPDATE actor SET id_number_temp = CASE
            WHEN id_number IS NOT NULL AND trim(id_number) != ''
            THEN jsonb_build_array(jsonb_build_object('type', '1', 'number', trim(id_number)))
            ELSE '[]'::jsonb
        END
    """
    )
    op.execute("ALTER TABLE actor DROP COLUMN id_number")
    op.execute("ALTER TABLE actor RENAME COLUMN id_number_temp TO id_number")
    op.execute("ALTER TABLE actor ALTER COLUMN id_number SET DEFAULT '[]'::jsonb")
    op.execute("ALTER TABLE actor ALTER COLUMN id_number SET NOT NULL")
    op.execute(
        "ALTER TABLE actor ADD CONSTRAINT check_actor_id_number_element_structure "
        "CHECK (validate_actor_id_number(id_number))"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_actor_id_number_gin ON actor USING GIN (id_number)")


def _create_dynamic_fields_tables(op):
    """Create dynamic_fields and dynamic_form_history tables."""
    op.execute(
        """
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
        )
    """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_dynamic_fields_entity_type "
        "ON dynamic_fields (entity_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_dynamic_fields_entity_active "
        "ON dynamic_fields (entity_type, active)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_dynamic_fields_entity_core "
        "ON dynamic_fields (entity_type, core)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_dynamic_fields_entity_sort "
        "ON dynamic_fields (entity_type, sort_order)"
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS dynamic_form_history (
            id SERIAL PRIMARY KEY,
            entity_type VARCHAR(50) NOT NULL,
            fields_snapshot JSONB NOT NULL,
            user_id INTEGER REFERENCES "user"(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted BOOLEAN DEFAULT FALSE
        )
    """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_dynamic_form_history_entity_type "
        "ON dynamic_form_history (entity_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_dynamic_form_history_created_at "
        "ON dynamic_form_history (created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_dynamic_form_history_entity_created "
        "ON dynamic_form_history (entity_type, created_at DESC)"
    )


def _seed_core_fields(conn):
    """Seed core dynamic fields for all entity types."""
    # Use exec_driver_sql to bypass SQLAlchemy's text() colon parsing,
    # which conflicts with JSON values like {"key":true}.
    conn.exec_driver_sql(
        """
        INSERT INTO dynamic_fields (
            name, title, entity_type, field_type, searchable,
            ui_component, schema_config, ui_config, validation_config,
            options, active, sort_order, core
        ) VALUES
            -- Actor fields
            ('name', 'Name', 'actor', 'text', false, 'input', '{}'::jsonb, '{"width":"w-100"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 1, true),
            ('first_name', 'First Name', 'actor', 'text', false, 'input', '{}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 2, true),
            ('middle_name', 'Middle Name', 'actor', 'text', false, 'input', '{}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 3, true),
            ('last_name', 'Last Name', 'actor', 'text', false, 'input', '{}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 4, true),
            ('nickname', 'Nickname', 'actor', 'text', false, 'input', '{}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 5, true),
            ('father_name', 'Father Name', 'actor', 'text', false, 'input', '{}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 6, true),
            ('mother_name', 'Mother Name', 'actor', 'text', false, 'input', '{}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 7, true),
            ('sex', 'Sex', 'actor', 'select', false, 'dropdown', '{"allow_multiple":false}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 8, true),
            ('age', 'Age', 'actor', 'number', false, 'number_input', '{}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 9, true),
            ('civilian', 'Civilian', 'actor', 'select', false, 'dropdown', '{"allow_multiple":false}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 10, true),
            ('origin_place', 'Origin Place', 'actor', 'select', false, 'dropdown', '{"allow_multiple":true}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 11, true),
            ('occupation', 'Occupation', 'actor', 'text', false, 'input', '{}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 12, true),
            ('position', 'Position', 'actor', 'text', false, 'input', '{}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 13, true),
            ('family_status', 'Family Status', 'actor', 'select', false, 'dropdown', '{"allow_multiple":false}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 14, true),
            ('no_children', 'Number of Children', 'actor', 'number', false, 'number_input', '{}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 15, true),
            ('ethnographies', 'Ethnographies', 'actor', 'select', false, 'dropdown', '{"allow_multiple":true}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 16, true),
            ('nationalities', 'Nationalities', 'actor', 'select', false, 'dropdown', '{"allow_multiple":true}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 17, true),
            ('dialects', 'Dialects', 'actor', 'select', false, 'dropdown', '{"allow_multiple":true}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 18, true),
            ('tags', 'Tags', 'actor', 'select', false, 'dropdown', '{"allow_multiple":true}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 19, true),
            ('id_number', 'ID Number', 'actor', 'text', false, 'input', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 20, true),
            ('actor_profiles', 'Actor Profiles', 'actor', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template":"actor_profiles"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 21, true),
            ('events_section', 'Events', 'actor', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template":"events_section"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 22, true),
            ('related_bulletins', 'Related Bulletins', 'actor', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template":"related_bulletins"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 23, true),
            ('related_actors', 'Related Actors', 'actor', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template":"related_actors"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 24, true),
            ('related_incidents', 'Related Incidents', 'actor', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template":"related_incidents"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 25, true),
            ('medias', 'Media', 'actor', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template":"medias"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 26, true),
            ('comments', 'Comments', 'actor', 'long_text', false, 'textarea', '{}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 27, true),
            ('status', 'Status', 'actor', 'select', false, 'dropdown', '{"allow_multiple":false}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 28, true),
            ('sources', 'Sources', 'actor', 'select', false, 'dropdown', '{"allow_multiple":true}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 29, true),
            ('labels', 'Labels', 'actor', 'select', false, 'dropdown', '{"allow_multiple":true}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 30, true),
            ('ver_labels', 'Verified Labels', 'actor', 'select', false, 'dropdown', '{"allow_multiple":true}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 31, true),
            -- Bulletin fields
            ('title', 'Original Title', 'bulletin', 'text', false, 'input', '{}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 1, true),
            ('sjac_title', 'Title', 'bulletin', 'text', false, 'input', '{}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 2, true),
            ('tags', 'Tags', 'bulletin', 'select', false, 'dropdown', '{"allow_multiple":true}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 3, true),
            ('sources', 'Sources', 'bulletin', 'select', false, 'dropdown', '{"allow_multiple":true}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 4, true),
            ('description', 'Description', 'bulletin', 'long_text', false, 'textarea', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 5, true),
            ('labels', 'Labels', 'bulletin', 'select', false, 'dropdown', '{"allow_multiple":true}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 6, true),
            ('ver_labels', 'Verified Labels', 'bulletin', 'select', false, 'dropdown', '{"allow_multiple":true}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 7, true),
            ('locations', 'Locations', 'bulletin', 'select', false, 'dropdown', '{"allow_multiple":true}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 8, true),
            ('global_map', 'Global Map', 'bulletin', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template":"global_map"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 9, true),
            ('events_section', 'Events', 'bulletin', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template":"events_section"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 10, true),
            ('geo_locations', 'Geo Locations', 'bulletin', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template":"geo_locations"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 11, true),
            ('related_bulletins', 'Related Bulletins', 'bulletin', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template":"related_bulletins"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 12, true),
            ('related_actors', 'Related Actors', 'bulletin', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template":"related_actors"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 13, true),
            ('related_incidents', 'Related Incidents', 'bulletin', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template":"related_incidents"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 14, true),
            ('source_link', 'Source Link', 'bulletin', 'text', false, 'input', '{}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 15, true),
            ('publish_date', 'Publish Date', 'bulletin', 'datetime', false, 'date_picker', '{}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 16, true),
            ('documentation_date', 'Documentation Date', 'bulletin', 'datetime', false, 'date_picker', '{}'::jsonb, '{"align":"right","width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 17, true),
            ('comments', 'Comments', 'bulletin', 'long_text', false, 'textarea', '{}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 18, true),
            ('status', 'Status', 'bulletin', 'select', false, 'dropdown', '{"allow_multiple":false}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 19, true),
            -- Incident fields
            ('title', 'Title', 'incident', 'text', false, 'input', '{}'::jsonb, '{"width":"w-100"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 1, true),
            ('description', 'Description', 'incident', 'long_text', false, 'textarea', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 2, true),
            ('potential_violations', 'Potential Violations', 'incident', 'select', false, 'dropdown', '{"allow_multiple":true}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 3, true),
            ('claimed_violations', 'Claimed Violations', 'incident', 'select', false, 'dropdown', '{"allow_multiple":true}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 4, true),
            ('labels', 'Labels', 'incident', 'select', false, 'dropdown', '{"allow_multiple":true}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 5, true),
            ('locations', 'Locations', 'incident', 'select', false, 'dropdown', '{"allow_multiple":true}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 6, true),
            ('events_section', 'Events', 'incident', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template":"events_section"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 7, true),
            ('related_bulletins', 'Related Bulletins', 'incident', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template":"related_bulletins"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 8, true),
            ('related_actors', 'Related Actors', 'incident', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template":"related_actors"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 9, true),
            ('related_incidents', 'Related Incidents', 'incident', 'html_block', false, 'html_block', '{}'::jsonb, '{"html_template":"related_incidents"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 10, true),
            ('comments', 'Comments', 'incident', 'long_text', false, 'textarea', '{}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 11, true),
            ('status', 'Status', 'incident', 'select', false, 'dropdown', '{"allow_multiple":false}'::jsonb, '{"width":"w-50"}'::jsonb, '{}'::jsonb, '[]'::jsonb, true, 12, true)
        ON CONFLICT (name, entity_type) DO NOTHING
    """
    )

    # Create initial form history snapshots (only if none exist)
    op.execute(
        """
        INSERT INTO dynamic_form_history (entity_type, fields_snapshot, user_id)
        SELECT df.entity_type,
            jsonb_agg(jsonb_build_object(
                'id', df.id, 'name', df.name, 'title', df.title,
                'entity_type', df.entity_type, 'field_type', df.field_type,
                'searchable', df.searchable, 'ui_component', df.ui_component,
                'schema_config', df.schema_config, 'ui_config', df.ui_config,
                'validation_config', df.validation_config, 'options', df.options,
                'active', df.active, 'sort_order', df.sort_order, 'core', df.core
            ) ORDER BY df.sort_order),
            NULL
        FROM dynamic_fields df
        WHERE df.active = TRUE AND df.deleted = FALSE AND df.core = TRUE
          AND NOT EXISTS (
              SELECT 1 FROM dynamic_form_history h WHERE h.entity_type = df.entity_type
          )
        GROUP BY df.entity_type
    """
    )


def _create_extraction_table(op):
    """Create extraction table with normalize function and indexes."""
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS extraction (
            id SERIAL PRIMARY KEY,
            media_id INTEGER NOT NULL UNIQUE,
            text TEXT,
            original_text TEXT,
            raw JSONB,
            confidence FLOAT,
            orientation INTEGER DEFAULT 0,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            manual BOOLEAN NOT NULL DEFAULT FALSE,
            word_count INTEGER DEFAULT 0,
            language VARCHAR(10),
            reviewed_by INTEGER,
            reviewed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted BOOLEAN
        )
    """
    )
    # ix_extraction_media_id omitted: media_id has UNIQUE constraint which creates an index
    op.execute("CREATE INDEX IF NOT EXISTS ix_extraction_status ON extraction (status)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_extraction_confidence ON extraction (confidence)")

    # Arabic text normalization function (with newline collapsing)
    op.execute(
        r"""
        CREATE OR REPLACE FUNCTION normalize_arabic_text(input text) RETURNS text AS $$
        BEGIN
            IF input IS NULL THEN RETURN NULL; END IF;
            RETURN regexp_replace(
                translate(
                    input,
                    E'\u0623\u0625\u0622\u0671\u0649\u0629\u0660\u0661\u0662\u0663\u0664\u0665\u0666\u0667\u0668\u0669\u064B\u064C\u064D\u064E\u064F\u0650\u0651\u0652\u0640',
                    E'\u0627\u0627\u0627\u0627\u064A\u06470123456789'
                ),
                E'[\r\n]+', ' ', 'g'
            );
        END;
        $$ LANGUAGE plpgsql IMMUTABLE STRICT
    """
    )

    # FK constraints
    op.execute(
        """
        DO $$ BEGIN
            ALTER TABLE extraction ADD CONSTRAINT fk_extraction_media_id
            FOREIGN KEY (media_id) REFERENCES media(id) ON DELETE CASCADE;
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """
    )
    op.execute(
        """
        DO $$ BEGIN
            ALTER TABLE extraction ADD CONSTRAINT fk_extraction_reviewed_by
            FOREIGN KEY (reviewed_by) REFERENCES "user"(id);
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$
    """
    )


def _fix_deleted_columns(op):
    """Set deleted=FALSE where NULL, add NOT NULL + DEFAULT on all tables."""
    tables = [
        "activity",
        "actor",
        "actor_history",
        "actor_profile",
        "app_config",
        "atoa",
        "atoa_info",
        "atob",
        "atob_info",
        "btob",
        "btob_info",
        "bulletin",
        "bulletin_history",
        "claimed_violation",
        "countries",
        "dialects",
        "dynamic_fields",
        "dynamic_form_history",
        "ethnographies",
        "event",
        "eventtype",
        "extraction",
        "geo_location",
        "geo_location_types",
        "id_number_types",
        "incident",
        "incident_history",
        "itoa",
        "itoa_info",
        "itob",
        "itob_info",
        "itoi",
        "itoi_info",
        "label",
        "location",
        "location_admin_level",
        "location_history",
        "location_type",
        "media",
        "media_categories",
        "notification",
        "potential_violation",
        "query",
        "role",
        "sessions",
        "settings",
        "source",
        "user",
        "workflow_statuses",
    ]
    op.execute(
        """
        DO $$
        DECLARE tbl TEXT;
            tables TEXT[] := ARRAY[{table_list}];
        BEGIN
            FOREACH tbl IN ARRAY tables LOOP
                EXECUTE format('UPDATE %I SET deleted = FALSE WHERE deleted IS NULL', tbl);
                EXECUTE format('ALTER TABLE %I ALTER COLUMN deleted SET DEFAULT FALSE', tbl);
                BEGIN
                    EXECUTE format('ALTER TABLE %I ALTER COLUMN deleted SET NOT NULL', tbl);
                EXCEPTION WHEN others THEN NULL;
                END;
            END LOOP;
        END $$
    """.format(
            table_list=",".join(f"'{t}'" for t in tables)
        )
    )
