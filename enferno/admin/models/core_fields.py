# Core Fields Configuration
# These are built-in Bulletin model fields that users can only show/hide/reorder

from enferno.admin.models.DynamicField import DynamicField

BULLETIN_CORE_FIELDS = {
    "title": {
        "title": "Title",
        "field_type": "text",
        "ui_component": "input",
        "sort_order": 1,
        "visible": True,
        "core": True,
    },
    "sjac_title": {
        "title": "SJAC Title",
        "field_type": "text",
        "ui_component": "input",
        "sort_order": 2,
        "visible": True,
        "core": True,
    },
    "description": {
        "title": "Description",
        "field_type": "long_text",
        "ui_component": "textarea",
        "sort_order": 3,
        "visible": True,
        "core": True,
    },
    "tags": {
        "title": "Tags",
        "field_type": "multi_select",
        "ui_component": "multi_dropdown",
        "sort_order": 4,
        "visible": True,
        "core": True,
    },
    "sources": {
        "title": "Sources",
        "field_type": "multi_select",
        "ui_component": "multi_dropdown",
        "sort_order": 5,
        "visible": True,
        "core": True,
    },
    "locations": {
        "title": "Locations",
        "field_type": "multi_select",
        "ui_component": "multi_dropdown",
        "sort_order": 6,
        "visible": True,
        "core": True,
    },
    "labels": {
        "title": "Labels",
        "field_type": "multi_select",
        "ui_component": "multi_dropdown",
        "sort_order": 7,
        "visible": True,
        "core": True,
    },
    "ver_labels": {
        "title": "Verified Labels",
        "field_type": "multi_select",
        "ui_component": "multi_dropdown",
        "sort_order": 8,
        "visible": True,
        "core": True,
    },
    "publish_date": {
        "title": "Publish Date",
        "field_type": "datetime",
        "ui_component": "date_picker",
        "sort_order": 9,
        "visible": True,
        "core": True,
    },
    "documentation_date": {
        "title": "Documentation Date",
        "field_type": "datetime",
        "ui_component": "date_picker",
        "sort_order": 10,
        "visible": True,
        "core": True,
    },
    "status": {
        "title": "Status",
        "field_type": "single_select",
        "ui_component": "dropdown",
        "sort_order": 11,
        "visible": True,
        "core": True,
        "options": [
            {"label": "Draft", "value": "draft"},
            {"label": "Published", "value": "published"},
            {"label": "Archived", "value": "archived"},
        ],
    },
    # === Complex HTML Block Fields (Phase 1) ===
    # These render existing components but are managed through the dynamic fields system
    "events_section": {
        "title": "Events",
        "field_type": "html_block",
        "ui_component": "html_block",
        "sort_order": 20,
        "visible": True,
        "core": True,
        "html_template": "events_section",
    },
    "geo_locations": {
        "title": "Geo Locations",
        "field_type": "html_block",
        "ui_component": "html_block",
        "sort_order": 21,
        "visible": True,
        "core": True,
        "html_template": "geo_locations",
    },
    "global_map": {
        "title": "Global Map",
        "field_type": "html_block",
        "ui_component": "html_block",
        "sort_order": 22,
        "visible": True,
        "core": True,
        "html_template": "global_map",
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
    "source_link": {
        "title": "Source Link",
        "field_type": "text",
        "ui_component": "input",
        "sort_order": 26,
        "visible": True,
        "core": True,
    },
    "comments": {
        "title": "Comments",
        "field_type": "long_text",
        "ui_component": "textarea",
        "sort_order": 27,
        "visible": True,
        "core": True,
    },
}


def seed_core_fields():
    """
    Seed core fields into the database for bulletin entity (idempotent).
    This includes both simple fields and complex HTML block fields.
    Can be run multiple times safely.
    """

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
            print(f"✅ Created core field: {name}")
        else:
            print(f"✓ Core field already exists: {name}")
