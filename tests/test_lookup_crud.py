"""
Config-driven RBAC tests for all lookup table endpoints.
Replaces 13 separate test files with a single parametrized module.

Each test gets ONE client (via request.getfixturevalue), matching
how the original tests work. This avoids FlaskLoginClient session leakage.
"""

import pytest
from uuid import uuid4

# ---------------------------------------------------------------------------
# Role matrices (derived from actual route decorators)
# ---------------------------------------------------------------------------

ADMIN_ONLY_UPDATE = {
    "list": [
        ("admin_client", 200),
        ("da_client", 200),
        ("mod_client", 200),
        ("anonymous_client", 401),
    ],
    "create": [
        ("admin_client", 201),
        ("da_client", 403),
        ("mod_client", 201),
        ("anonymous_client", 401),
    ],
    "update": [
        ("admin_client", 200),
        ("da_client", 403),
        ("mod_client", 403),
        ("anonymous_client", 401),
    ],
    "delete": [
        ("admin_client", 200),
        ("da_client", 403),
        ("mod_client", 403),
        ("anonymous_client", 401),
    ],
}

ADMIN_MOD_UPDATE = {
    **ADMIN_ONLY_UPDATE,
    "update": [
        ("admin_client", 200),
        ("da_client", 403),
        ("mod_client", 200),
        ("anonymous_client", 401),
    ],
}

ADMIN_ONLY = {
    "list": [
        ("admin_client", 200),
        ("da_client", 403),
        ("mod_client", 403),
        ("anonymous_client", 401),
    ],
    "create": [
        ("admin_client", 201),
        ("da_client", 403),
        ("mod_client", 403),
        ("anonymous_client", 401),
    ],
    "update": [
        ("admin_client", 200),
        ("da_client", 403),
        ("mod_client", 403),
        ("anonymous_client", 401),
    ],
    "delete": [
        ("admin_client", 200),
        ("da_client", 403),
        ("mod_client", 403),
        ("anonymous_client", 401),
    ],
}

# ---------------------------------------------------------------------------
# Lookup table config
# ---------------------------------------------------------------------------

LOOKUP_TABLES = {
    "countries": (
        "/admin/api/countries/",
        "/admin/api/country",
        {"item": {"title": "TestCountry"}},
        {"item": {"title": "Updated"}},
        ADMIN_ONLY_UPDATE,
    ),
    "ethnographies": (
        "/admin/api/ethnographies/",
        "/admin/api/ethnography",
        {"item": {"title": "TestEthno"}},
        {"item": {"title": "Updated"}},
        ADMIN_ONLY_UPDATE,
    ),
    "location_types": (
        "/admin/api/location-types/",
        "/admin/api/location-type",
        {"item": {"title": "TestLocType"}},
        {"item": {"title": "Updated"}},
        ADMIN_ONLY_UPDATE,
    ),
    "location_admin_levels": (
        "/admin/api/location-admin-levels/",
        "/admin/api/location-admin-level",
        {"item": {"code": 6, "title": "TestLevel"}},
        {"item": {"code": 6, "title": "Updated"}},
        ADMIN_ONLY_UPDATE,
    ),
    "media_categories": (
        "/admin/api/mediacategories/",
        "/admin/api/mediacategory",
        {"item": {"title": "TestMediaCat", "title_tr": ""}},
        {"item": {"title": "Updated", "title_tr": ""}},
        ADMIN_ONLY_UPDATE,
    ),
    "geo_location_types": (
        "/admin/api/geolocationtypes/",
        "/admin/api/geolocationtype",
        {"item": {"title": "TestGeoType", "title_tr": ""}},
        {"item": {"title": "Updated", "title_tr": ""}},
        ADMIN_ONLY_UPDATE,
    ),
    "claimed_violations": (
        "/admin/api/claimedviolation/",
        "/admin/api/claimedviolation/",
        {"item": {"title": "TestCV"}},
        {"item": {"title": "Updated"}},
        ADMIN_MOD_UPDATE,
    ),
    "potential_violations": (
        "/admin/api/potentialviolation/",
        "/admin/api/potentialviolation/",
        {"item": {"title": "TestPV"}},
        {"item": {"title": "Updated"}},
        ADMIN_MOD_UPDATE,
    ),
    "labels": (
        "/admin/api/labels/",
        "/admin/api/label/",
        {
            "item": {
                "title": "TestLabel",
                "for_bulletin": True,
                "for_actor": False,
                "for_incident": False,
                "verified": False,
            }
        },
        {"item": {"title": "Updated", "verified": True}},
        ADMIN_MOD_UPDATE,
    ),
    "sources": (
        "/admin/api/sources/",
        "/admin/api/source/",
        {"item": {"title": "TestSource", "etl_id": "test-src-001"}},
        {"item": {"title": "Updated"}},
        ADMIN_MOD_UPDATE,
    ),
    "event_types": (
        "/admin/api/eventtypes/",
        "/admin/api/eventtype/",
        {"item": {"title": "TestEventtype", "for_bulletin": True, "for_actor": False}},
        {"item": {"title": "Updated"}},
        ADMIN_MOD_UPDATE,
    ),
    "roles": (
        "/admin/api/roles/",
        "/admin/api/role/",
        {"item": {"name": f"TestRole_{uuid4().hex[:6]}", "description": "Test", "color": "#333"}},
        {"item": {"name": f"Updated_{uuid4().hex[:6]}", "description": "Upd", "color": "#444"}},
        ADMIN_ONLY,
    ),
}


def _list_params():
    """Generate (entity, client_fixture, expected_status) for LIST tests."""
    for entity, (list_url, _, _, _, roles) in LOOKUP_TABLES.items():
        for client_fixture, status in roles["list"]:
            yield pytest.param(
                entity, list_url, client_fixture, status, id=f"{entity}-{client_fixture}-{status}"
            )


def _create_params():
    for entity, (_, create_url, payload, _, roles) in LOOKUP_TABLES.items():
        for client_fixture, status in roles["create"]:
            yield pytest.param(
                entity,
                create_url,
                payload,
                client_fixture,
                status,
                id=f"{entity}-{client_fixture}-{status}",
            )


def _update_params():
    for entity, (_, create_url, create_payload, update_payload, roles) in LOOKUP_TABLES.items():
        for client_fixture, status in roles["update"]:
            yield pytest.param(
                entity,
                create_url,
                create_payload,
                update_payload,
                client_fixture,
                status,
                id=f"{entity}-{client_fixture}-{status}",
            )


def _delete_params():
    for entity, (_, create_url, create_payload, _, roles) in LOOKUP_TABLES.items():
        for client_fixture, status in roles["delete"]:
            yield pytest.param(
                entity,
                create_url,
                create_payload,
                client_fixture,
                status,
                id=f"{entity}-{client_fixture}-{status}",
            )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

HEADERS = {"Content-Type": "application/json"}


@pytest.mark.parametrize("entity,list_url,client_fixture,expected", list(_list_params()))
def test_lookup_list(request, session, entity, list_url, client_fixture, expected):
    client = request.getfixturevalue(client_fixture)
    resp = client.get(list_url, headers=HEADERS)
    assert resp.status_code == expected


@pytest.mark.parametrize(
    "entity,create_url,payload,client_fixture,expected", list(_create_params())
)
def test_lookup_create(request, session, entity, create_url, payload, client_fixture, expected):
    client = request.getfixturevalue(client_fixture)
    resp = client.post(create_url, json=payload, headers=HEADERS)
    assert resp.status_code == expected


@pytest.mark.parametrize(
    "entity,create_url,create_payload,update_payload,client_fixture,expected",
    list(_update_params()),
)
def test_lookup_update(
    request,
    session,
    entity,
    create_url,
    create_payload,
    update_payload,
    client_fixture,
    expected,
):
    # Create item via ORM so it's in the savepoint
    item = _create_item_via_orm(session, entity, create_payload)
    base = create_url.rstrip("/")

    client = request.getfixturevalue(client_fixture)
    resp = client.put(f"{base}/{item.id}", json=update_payload, headers=HEADERS)
    assert resp.status_code == expected


@pytest.mark.parametrize(
    "entity,create_url,create_payload,client_fixture,expected", list(_delete_params())
)
def test_lookup_delete(
    request, session, entity, create_url, create_payload, client_fixture, expected
):
    item = _create_item_via_orm(session, entity, create_payload)
    base = create_url.rstrip("/")

    client = request.getfixturevalue(client_fixture)
    resp = client.delete(f"{base}/{item.id}", headers=HEADERS)
    assert resp.status_code == expected


# ---------------------------------------------------------------------------
# ORM helpers
# ---------------------------------------------------------------------------

_MODEL_MAP = None


def _get_model_map():
    global _MODEL_MAP
    if _MODEL_MAP is None:
        from enferno.admin.models import (
            ClaimedViolation,
            Country,
            Ethnography,
            Eventtype,
            GeoLocationType,
            Label,
            LocationAdminLevel,
            LocationType,
            MediaCategory,
            PotentialViolation,
            Source,
        )
        from enferno.user.models import Role

        _MODEL_MAP = {
            "countries": Country,
            "ethnographies": Ethnography,
            "location_types": LocationType,
            "location_admin_levels": LocationAdminLevel,
            "media_categories": MediaCategory,
            "geo_location_types": GeoLocationType,
            "claimed_violations": ClaimedViolation,
            "potential_violations": PotentialViolation,
            "labels": Label,
            "sources": Source,
            "event_types": Eventtype,
            "roles": Role,
        }
    return _MODEL_MAP


def _create_item_via_orm(session, entity_name, payload):
    """Create an item directly via ORM for update/delete tests."""
    Model = _get_model_map()[entity_name]
    fields = payload.get("item", payload)
    item = Model(**fields)
    session.add(item)
    session.commit()
    return item
