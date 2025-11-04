# Core Fields Configuration
# Built-in fields that users can show/hide/reorder but not delete

from enferno.admin.models.DynamicField import DynamicField


# Format: (name, title, field_type, sort_order, **kwargs)
# kwargs can include: ui_config, schema_config, html_template
BULLETIN_CORE_FIELDS = [
    ("title", "Original Title", "text", 1, {"ui_config": {"width": "w-50"}}),
    ("sjac_title", "Title", "text", 2, {"ui_config": {"width": "w-50"}}),
    ("tags", "Tags", "select", 3, {"schema_config": {"allow_multiple": True}}),
    ("sources", "Sources", "select", 4, {"schema_config": {"allow_multiple": True}}),
    ("description", "Description", "long_text", 5),
    (
        "labels",
        "Labels",
        "select",
        6,
        {"schema_config": {"allow_multiple": True}, "ui_config": {"width": "w-50"}},
    ),
    (
        "ver_labels",
        "Verified Labels",
        "select",
        7,
        {"schema_config": {"allow_multiple": True}, "ui_config": {"width": "w-50"}},
    ),
    ("locations", "Locations", "select", 8, {"schema_config": {"allow_multiple": True}}),
    # HTML Blocks - complex components managed through dynamic fields
    ("global_map", "Global Map", "html_block", 9, {"html_template": "global_map"}),
    ("events_section", "Events", "html_block", 10, {"html_template": "events_section"}),
    ("geo_locations", "Geo Locations", "html_block", 11, {"html_template": "geo_locations"}),
    (
        "related_bulletins",
        "Related Bulletins",
        "html_block",
        12,
        {"html_template": "related_bulletins"},
    ),
    ("related_actors", "Related Actors", "html_block", 13, {"html_template": "related_actors"}),
    (
        "related_incidents",
        "Related Incidents",
        "html_block",
        14,
        {"html_template": "related_incidents"},
    ),
    ("source_link", "Source Link", "text", 15, {"ui_config": {"width": "w-50"}}),
    ("publish_date", "Publish Date", "datetime", 16, {"ui_config": {"width": "w-50"}}),
    (
        "documentation_date",
        "Documentation Date",
        "datetime",
        17,
        {"ui_config": {"width": "w-50", "align": "right"}},
    ),
    ("comments", "Comments", "long_text", 18, {"ui_config": {"width": "w-50"}}),
    (
        "status",
        "Status",
        "select",
        19,
        {"schema_config": {"allow_multiple": False}, "ui_config": {"width": "w-50"}},
    ),
]

INCIDENT_CORE_FIELDS = [
    ("title", "Title", "text", 1, {"ui_config": {"width": "w-100"}}),
    ("description", "Description", "long_text", 2),
    (
        "potential_violations",
        "Potential Violations",
        "select",
        3,
        {"schema_config": {"allow_multiple": True}, "ui_config": {"width": "w-50"}},
    ),
    (
        "claimed_violations",
        "Claimed Violations",
        "select",
        4,
        {"schema_config": {"allow_multiple": True}, "ui_config": {"width": "w-50"}},
    ),
    (
        "labels",
        "Labels",
        "select",
        5,
        {"schema_config": {"allow_multiple": True}, "ui_config": {"width": "w-50"}},
    ),
    (
        "locations",
        "Locations",
        "select",
        6,
        {"schema_config": {"allow_multiple": True}, "ui_config": {"width": "w-50"}},
    ),
    ("events_section", "Events", "html_block", 7, {"html_template": "events_section"}),
    (
        "related_bulletins",
        "Related Bulletins",
        "html_block",
        8,
        {"html_template": "related_bulletins"},
    ),
    ("related_actors", "Related Actors", "html_block", 9, {"html_template": "related_actors"}),
    (
        "related_incidents",
        "Related Incidents",
        "html_block",
        10,
        {"html_template": "related_incidents"},
    ),
    ("comments", "Comments", "long_text", 11, {"ui_config": {"width": "w-50"}}),
    (
        "status",
        "Status",
        "select",
        12,
        {"schema_config": {"allow_multiple": False}, "ui_config": {"width": "w-50"}},
    ),
]

ACTOR_CORE_FIELDS = [
    ("name", "Name", "text", 1, {"ui_config": {"width": "w-100"}}),
    ("first_name", "First Name", "text", 2, {"ui_config": {"width": "w-50"}}),
    ("middle_name", "Middle Name", "text", 3, {"ui_config": {"width": "w-50"}}),
    ("last_name", "Last Name", "text", 4, {"ui_config": {"width": "w-50"}}),
    ("nickname", "Nickname", "text", 5, {"ui_config": {"width": "w-50"}}),
    ("father_name", "Father Name", "text", 6, {"ui_config": {"width": "w-50"}}),
    ("mother_name", "Mother Name", "text", 7, {"ui_config": {"width": "w-50"}}),
    (
        "sex",
        "Sex",
        "select",
        8,
        {"schema_config": {"allow_multiple": False}, "ui_config": {"width": "w-50"}},
    ),
    ("age", "Age", "number", 9, {"ui_config": {"width": "w-50"}}),
    ("civilian", "Civilian", "select", 10, {"schema_config": {"allow_multiple": False}, "ui_config": {"width": "w-50"}}),
    ("origin_place", "Origin Place", "select", 11, {"schema_config": {"allow_multiple": True}, "ui_config": {"width": "w-50"}}),
    ("occupation", "Occupation", "text", 12, {"ui_config": {"width": "w-50"}}),
    ("position", "Position", "text", 13, {"ui_config": {"width": "w-50"}}),
    (
        "family_status",
        "Family Status",
        "select",
        14,
        {"schema_config": {"allow_multiple": False}, "ui_config": {"width": "w-50"}},
    ),
    ("no_children", "Number of Children", "number", 15, {"ui_config": {"width": "w-50"}}),
    ("ethnographies", "Ethnographies", "select", 16, {"schema_config": {"allow_multiple": True}, "ui_config": {"width": "w-50"}}),
    ("nationalities", "Nationalities", "select", 17, {"schema_config": {"allow_multiple": True}, "ui_config": {"width": "w-50"}}),
    ("dialects", "Dialects", "select", 18, {"schema_config": {"allow_multiple": True}, "ui_config": {"width": "w-50"}}),
    ("tags", "Tags", "select", 19, {"schema_config": {"allow_multiple": True}, "ui_config": {"width": "w-50"}}),
    ("id_number", "ID Number", "text", 20),
    ("actor_profiles", "Actor Profiles", "html_block", 21, {"html_template": "actor_profiles"}),
    ("events_section", "Events", "html_block", 22, {"html_template": "events_section"}),
    (
        "related_bulletins",
        "Related Bulletins",
        "html_block",
        23,
        {"html_template": "related_bulletins"},
    ),
    ("related_actors", "Related Actors", "html_block", 24, {"html_template": "related_actors"}),
    (
        "related_incidents",
        "Related Incidents",
        "html_block",
        25,
        {"html_template": "related_incidents"},
    ),
    ("medias", "Media", "html_block", 26, {"html_template": "medias"}),
    ("comments", "Comments", "long_text", 27, {"ui_config": {"width": "w-50"}}),
    (
        "status",
        "Status",
        "select",
        28,
        {"schema_config": {"allow_multiple": False}, "ui_config": {"width": "w-50"}},
    ),
]


def _create_core_field(name, title, field_type, sort_order, entity_type, **kwargs):
    """
    Create a core field with smart defaults.

    Auto-determines ui_component from field_type using DynamicField.COMPONENT_MAP.
    Only requires overrides for what differs from defaults.

    Args:
        name: Field name
        title: Display title
        field_type: Data type (text, long_text, number, select, datetime, html_block)
        sort_order: Display order
        entity_type: Entity type (bulletin, incident, actor)
        **kwargs: Optional overrides (ui_config, schema_config, html_template, options)

    Returns:
        DynamicField instance
    """
    # Auto-determine ui_component from field_type
    ui_component = DynamicField.COMPONENT_MAP.get(field_type, [None])[0]

    # Build ui_config
    ui_config = {}
    if "html_template" in kwargs:
        ui_config["html_template"] = kwargs.pop("html_template")
    if "ui_config" in kwargs:
        ui_config.update(kwargs.pop("ui_config"))

    # Extract schema_config and options if provided
    schema_config = kwargs.pop("schema_config", {})
    options = kwargs.pop("options", [])

    return DynamicField(
        name=name,
        title=title,
        entity_type=entity_type,
        field_type=field_type,
        ui_component=ui_component,
        sort_order=sort_order,
        core=True,
        active=True,
        ui_config=ui_config,
        schema_config=schema_config,
        options=options,
    )


def _seed_entity_core_fields(entity_type: str, core_fields_list: list):
    """
    Seed core fields for a specific entity type (idempotent).

    Args:
        entity_type: The entity type ('bulletin', 'incident', 'actor')
        core_fields_list: List of tuples (name, title, field_type, sort_order, kwargs)
    """
    for field_spec in core_fields_list:
        # Unpack tuple (handles both 4 and 5 element tuples)
        if len(field_spec) == 5:
            name, title, field_type, sort_order, kwargs = field_spec
        else:
            name, title, field_type, sort_order = field_spec
            kwargs = {}

        # Check if core field already exists
        existing = DynamicField.query.filter_by(
            name=name, entity_type=entity_type, core=True
        ).first()

        if not existing:
            # Create new core field using helper
            field = _create_core_field(name, title, field_type, sort_order, entity_type, **kwargs)
            field.save()
            print(f"✅ Created {entity_type} core field: {name}")
        else:
            print(f"✓ {entity_type.title()} core field already exists: {name}")


def seed_core_fields():
    """
    Seed core fields into the database for bulletin, incident, and actor entities (idempotent).
    Can be run multiple times safely.
    """
    _seed_entity_core_fields("bulletin", BULLETIN_CORE_FIELDS)
    _seed_entity_core_fields("incident", INCIDENT_CORE_FIELDS)
    _seed_entity_core_fields("actor", ACTOR_CORE_FIELDS)
