# Core Fields Configuration
# These are built-in Bulletin model fields that users can only show/hide/reorder

from enferno.admin.models.DynamicField import DynamicField

BULLETIN_CORE_FIELDS = {
    "title": {
        "title": "Original Title",
        "field_type": "text",
        "ui_component": "input",
        "sort_order": 1,
        "visible": True,
        "core": True,
        "ui_config": {"width": "w-50"},
    },
    "sjac_title": {
        "title": "Title",
        "field_type": "text",
        "ui_component": "input",
        "sort_order": 2,
        "visible": True,
        "core": True,
        "ui_config": {"width": "w-50"},
    },
    "tags": {
        "title": "Tags",
        "field_type": "select",
        "ui_component": "dropdown",
        "sort_order": 3,
        "visible": True,
        "core": True,
        "schema_config": {"allow_multiple": True},
    },
    "sources": {
        "title": "Sources",
        "field_type": "select",
        "ui_component": "dropdown",
        "sort_order": 4,
        "visible": True,
        "core": True,
        "schema_config": {"allow_multiple": True},
    },
    "description": {
        "title": "Description",
        "field_type": "long_text",
        "ui_component": "textarea",
        "sort_order": 5,
        "visible": True,
        "core": True,
    },
    "labels": {
        "title": "Labels",
        "field_type": "select",
        "ui_component": "dropdown",
        "sort_order": 6,
        "visible": True,
        "core": True,
        "schema_config": {"allow_multiple": True},
        "ui_config": {"width": "w-50"},
    },
    "ver_labels": {
        "title": "Verified Labels",
        "field_type": "select",
        "ui_component": "dropdown",
        "sort_order": 7,
        "visible": True,
        "core": True,
        "schema_config": {"allow_multiple": True},
        "ui_config": {"width": "w-50"},
    },
    "locations": {
        "title": "Locations",
        "field_type": "select",
        "ui_component": "dropdown",
        "sort_order": 8,
        "visible": True,
        "core": True,
        "schema_config": {"allow_multiple": True},
    },
    # === Complex HTML Block Fields (Phase 1) ===
    # These render existing components but are managed through the dynamic fields system
    "global_map": {
        "title": "Global Map",
        "field_type": "html_block",
        "ui_component": "html_block",
        "sort_order": 9,
        "visible": True,
        "core": True,
        "html_template": "global_map",
    },
    "events_section": {
        "title": "Events",
        "field_type": "html_block",
        "ui_component": "html_block",
        "sort_order": 10,
        "visible": True,
        "core": True,
        "html_template": "events_section",
    },
    "geo_locations": {
        "title": "Geo Locations",
        "field_type": "html_block",
        "ui_component": "html_block",
        "sort_order": 11,
        "visible": True,
        "core": True,
        "html_template": "geo_locations",
    },
    "related_bulletins": {
        "title": "Related Bulletins",
        "field_type": "html_block",
        "ui_component": "html_block",
        "sort_order": 12,
        "visible": True,
        "core": True,
        "html_template": "related_bulletins",
    },
    "related_actors": {
        "title": "Related Actors",
        "field_type": "html_block",
        "ui_component": "html_block",
        "sort_order": 13,
        "visible": True,
        "core": True,
        "html_template": "related_actors",
    },
    "related_incidents": {
        "title": "Related Incidents",
        "field_type": "html_block",
        "ui_component": "html_block",
        "sort_order": 14,
        "visible": True,
        "core": True,
        "html_template": "related_incidents",
    },
    "source_link": {
        "title": "Source Link",
        "field_type": "text",
        "ui_component": "input",
        "sort_order": 15,
        "visible": True,
        "core": True,
        "ui_config": {"width": "w-50"},
    },
    "publish_date": {
        "title": "Publish Date",
        "field_type": "datetime",
        "ui_component": "date_picker",
        "sort_order": 16,
        "visible": True,
        "core": True,
        "ui_config": {"width": "w-50"},
    },
    "documentation_date": {
        "title": "Documentation Date",
        "field_type": "datetime",
        "ui_component": "date_picker",
        "sort_order": 17,
        "visible": True,
        "core": True,
        "ui_config": {"width": "w-50", "align": "right"},
    },
    "comments": {
        "title": "Comments",
        "field_type": "long_text",
        "ui_component": "textarea",
        "sort_order": 18,
        "visible": True,
        "core": True,
        "ui_config": {"width": "w-50"},
    },
    "status": {
        "title": "Status",
        "field_type": "select",
        "ui_component": "dropdown",
        "sort_order": 19,
        "visible": True,
        "core": True,
        "schema_config": {"allow_multiple": False},
        "ui_config": {"width": "w-50"},
    },
}

INCIDENT_CORE_FIELDS = {
    "title": {
        "title": "Title",
        "field_type": "text",
        "ui_component": "input",
        "sort_order": 1,
        "visible": True,
        "core": True,
        "ui_config": {"width": "w-100"},
    },
    "description": {
        "title": "Description",
        "field_type": "long_text",
        "ui_component": "textarea",
        "sort_order": 2,
        "visible": True,
        "core": True,
    },
    "potential_violations": {
        "title": "Potential Violations",
        "field_type": "select",
        "ui_component": "dropdown",
        "sort_order": 3,
        "visible": True,
        "core": True,
        "schema_config": {"allow_multiple": True},
    },
    "claimed_violations": {
        "title": "Claimed Violations",
        "field_type": "select",
        "ui_component": "dropdown",
        "sort_order": 4,
        "visible": True,
        "core": True,
        "schema_config": {"allow_multiple": True},
    },
    "labels": {
        "title": "Labels",
        "field_type": "select",
        "ui_component": "dropdown",
        "sort_order": 5,
        "visible": True,
        "core": True,
        "schema_config": {"allow_multiple": True},
    },
    "locations": {
        "title": "Locations",
        "field_type": "select",
        "ui_component": "dropdown",
        "sort_order": 6,
        "visible": True,
        "core": True,
        "schema_config": {"allow_multiple": True},
    },
    "events_section": {
        "title": "Events",
        "field_type": "html_block",
        "ui_component": "html_block",
        "sort_order": 7,
        "visible": True,
        "core": True,
        "html_template": "events_section",
    },
    "related_bulletins": {
        "title": "Related Bulletins",
        "field_type": "html_block",
        "ui_component": "html_block",
        "sort_order": 8,
        "visible": True,
        "core": True,
        "html_template": "related_bulletins",
    },
    "related_actors": {
        "title": "Related Actors",
        "field_type": "html_block",
        "ui_component": "html_block",
        "sort_order": 9,
        "visible": True,
        "core": True,
        "html_template": "related_actors",
    },
    "related_incidents": {
        "title": "Related Incidents",
        "field_type": "html_block",
        "ui_component": "html_block",
        "sort_order": 10,
        "visible": True,
        "core": True,
        "html_template": "related_incidents",
    },
    "comments": {
        "title": "Comments",
        "field_type": "long_text",
        "ui_component": "textarea",
        "sort_order": 11,
        "visible": True,
        "core": True,
        "ui_config": {"width": "w-50"},
    },
    "status": {
        "title": "Status",
        "field_type": "select",
        "ui_component": "dropdown",
        "sort_order": 12,
        "visible": True,
        "core": True,
        "schema_config": {"allow_multiple": False},
        "ui_config": {"width": "w-50"},
    },
}

ACTOR_CORE_FIELDS = {
    "name": {
        "title": "Name",
        "field_type": "text",
        "ui_component": "input",
        "sort_order": 1,
        "visible": True,
        "core": True,
        "ui_config": {"width": "w-100"},
    },
    "nickname": {
        "title": "Nickname",
        "field_type": "text",
        "ui_component": "input",
        "sort_order": 2,
        "visible": True,
        "core": True,
        "ui_config": {"width": "w-50"},
    },
    "first_name": {
        "title": "First Name",
        "field_type": "text",
        "ui_component": "input",
        "sort_order": 3,
        "visible": True,
        "core": True,
        "ui_config": {"width": "w-50"},
    },
    "middle_name": {
        "title": "Middle Name",
        "field_type": "text",
        "ui_component": "input",
        "sort_order": 4,
        "visible": True,
        "core": True,
        "ui_config": {"width": "w-50"},
    },
    "last_name": {
        "title": "Last Name",
        "field_type": "text",
        "ui_component": "input",
        "sort_order": 5,
        "visible": True,
        "core": True,
        "ui_config": {"width": "w-50"},
    },
    "father_name": {
        "title": "Father Name",
        "field_type": "text",
        "ui_component": "input",
        "sort_order": 6,
        "visible": True,
        "core": True,
        "ui_config": {"width": "w-50"},
    },
    "mother_name": {
        "title": "Mother Name",
        "field_type": "text",
        "ui_component": "input",
        "sort_order": 7,
        "visible": True,
        "core": True,
        "ui_config": {"width": "w-50"},
    },
    "sex": {
        "title": "Sex",
        "field_type": "select",
        "ui_component": "dropdown",
        "sort_order": 8,
        "visible": True,
        "core": True,
        "schema_config": {"allow_multiple": False},
        "ui_config": {"width": "w-50"},
    },
    "age": {
        "title": "Age",
        "field_type": "number",
        "ui_component": "input",
        "sort_order": 9,
        "visible": True,
        "core": True,
        "ui_config": {"width": "w-50"},
    },
    "civilian": {
        "title": "Civilian",
        "field_type": "select",
        "ui_component": "checkbox",
        "sort_order": 10,
        "visible": True,
        "core": True,
        "schema_config": {"allow_multiple": False},
    },
    "origin_place": {
        "title": "Origin Place",
        "field_type": "select",
        "ui_component": "dropdown",
        "sort_order": 11,
        "visible": True,
        "core": True,
        "schema_config": {"allow_multiple": True},
    },
    "occupation": {
        "title": "Occupation",
        "field_type": "text",
        "ui_component": "input",
        "sort_order": 12,
        "visible": True,
        "core": True,
        "ui_config": {"width": "w-50"},
    },
    "position": {
        "title": "Position",
        "field_type": "text",
        "ui_component": "input",
        "sort_order": 13,
        "visible": True,
        "core": True,
        "ui_config": {"width": "w-50"},
    },
    "family_status": {
        "title": "Family Status",
        "field_type": "select",
        "ui_component": "dropdown",
        "sort_order": 14,
        "visible": True,
        "core": True,
        "schema_config": {"allow_multiple": False},
        "ui_config": {"width": "w-50"},
    },
    "no_children": {
        "title": "Number of Children",
        "field_type": "number",
        "ui_component": "input",
        "sort_order": 15,
        "visible": True,
        "core": True,
        "ui_config": {"width": "w-50"},
    },
    "ethnographies": {
        "title": "Ethnographies",
        "field_type": "select",
        "ui_component": "dropdown",
        "sort_order": 16,
        "visible": True,
        "core": True,
        "schema_config": {"allow_multiple": True},
    },
    "nationalities": {
        "title": "Nationalities",
        "field_type": "select",
        "ui_component": "dropdown",
        "sort_order": 17,
        "visible": True,
        "core": True,
        "schema_config": {"allow_multiple": True},
    },
    "dialects": {
        "title": "Dialects",
        "field_type": "select",
        "ui_component": "dropdown",
        "sort_order": 18,
        "visible": True,
        "core": True,
        "schema_config": {"allow_multiple": True},
    },
    "tags": {
        "title": "Tags",
        "field_type": "select",
        "ui_component": "dropdown",
        "sort_order": 19,
        "visible": True,
        "core": True,
        "schema_config": {"allow_multiple": True},
    },
    "id_number": {
        "title": "ID Number",
        "field_type": "text",
        "ui_component": "input",
        "sort_order": 20,
        "visible": True,
        "core": True,
    },
    "actor_profiles": {
        "title": "Actor Profiles",
        "field_type": "html_block",
        "ui_component": "html_block",
        "sort_order": 21,
        "visible": True,
        "core": True,
        "html_template": "actor_profiles",
    },
    "events_section": {
        "title": "Events",
        "field_type": "html_block",
        "ui_component": "html_block",
        "sort_order": 22,
        "visible": True,
        "core": True,
        "html_template": "events_section",
    },
    "related_bulletins": {
        "title": "Related Bulletins",
        "field_type": "html_block",
        "ui_component": "html_block",
        "sort_order": 23,
        "visible": True,
        "core": True,
        "html_template": "related_bulletins",
    },
    "related_actors": {
        "title": "Related Actors",
        "field_type": "html_block",
        "ui_component": "html_block",
        "sort_order": 24,
        "visible": True,
        "core": True,
        "html_template": "related_actors",
    },
    "related_incidents": {
        "title": "Related Incidents",
        "field_type": "html_block",
        "ui_component": "html_block",
        "sort_order": 25,
        "visible": True,
        "core": True,
        "html_template": "related_incidents",
    },
    "medias": {
        "title": "Media",
        "field_type": "html_block",
        "ui_component": "html_block",
        "sort_order": 26,
        "visible": True,
        "core": True,
        "html_template": "medias",
    },
    "comments": {
        "title": "Comments",
        "field_type": "long_text",
        "ui_component": "textarea",
        "sort_order": 27,
        "visible": True,
        "core": True,
        "ui_config": {"width": "w-50"},
    },
    "status": {
        "title": "Status",
        "field_type": "select",
        "ui_component": "dropdown",
        "sort_order": 28,
        "visible": True,
        "core": True,
        "schema_config": {"allow_multiple": False},
        "ui_config": {"width": "w-50"},
    },
}


def seed_core_fields():
    """
    Seed core fields into the database for bulletin and incident entities (idempotent).
    This includes both simple fields and complex HTML block fields.
    Can be run multiple times safely.
    """

    # Seed bulletin core fields
    for name, config in BULLETIN_CORE_FIELDS.items():
        # Check if core field already exists
        existing = DynamicField.query.filter_by(
            name=name, entity_type="bulletin", core=True
        ).first()

        # Create ui_config with html_template if specified
        ui_config = {}
        if config.get("html_template"):
            ui_config["html_template"] = config["html_template"]

        if not existing:
            # Create new core field
            field = DynamicField(
                name=name,
                title=config["title"],
                entity_type="bulletin",
                field_type=config["field_type"],
                ui_component=config["ui_component"],
                sort_order=config["sort_order"],
                core=True,
                active=config.get("visible", True),
                ui_config=ui_config,
                options=config.get("options", []),
            )
            field.save()
            print(f"✅ Created bulletin core field: {name}")
        else:
            print(f"✓ Bulletin core field already exists: {name}")

    # Seed incident core fields
    for name, config in INCIDENT_CORE_FIELDS.items():
        # Check if core field already exists
        existing = DynamicField.query.filter_by(
            name=name, entity_type="incident", core=True
        ).first()

        # Create ui_config with html_template if specified
        ui_config = {}
        if config.get("html_template"):
            ui_config["html_template"] = config["html_template"]

        if not existing:
            # Create new core field
            field = DynamicField(
                name=name,
                title=config["title"],
                entity_type="incident",
                field_type=config["field_type"],
                ui_component=config["ui_component"],
                sort_order=config["sort_order"],
                core=True,
                active=config.get("visible", True),
                ui_config=ui_config,
                options=config.get("options", []),
            )
            field.save()
            print(f"✅ Created incident core field: {name}")
        else:
            print(f"✓ Incident core field already exists: {name}")
