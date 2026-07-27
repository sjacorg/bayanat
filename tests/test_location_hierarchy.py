import pytest
from sqlalchemy.exc import IntegrityError

from enferno.admin.models import (
    Location,
    LocationAdminLevel,
    LocationHierarchy,
    LocationType,
)

HEADERS = {"Content-Type": "application/json"}


@pytest.fixture
def hierarchy(session):
    """A partner hierarchy with its own Territory > Governorate > Locality ladder."""
    h = LocationHierarchy(title="Palestine operational")
    session.add(h)
    session.commit()
    levels = [
        LocationAdminLevel(code=1, title="Territory", display_order=1, hierarchy_id=h.id),
        LocationAdminLevel(code=2, title="Governorate", display_order=2, hierarchy_id=h.id),
        LocationAdminLevel(code=3, title="Locality", display_order=3, hierarchy_id=h.id),
    ]
    session.add_all(levels)
    session.commit()
    # requests commit and expire the session, so tear down by id, not by instance
    hierarchy_id = h.id
    yield h
    session.query(LocationAdminLevel).filter(
        LocationAdminLevel.hierarchy_id == hierarchy_id
    ).delete(synchronize_session=False)
    session.query(LocationHierarchy).filter(LocationHierarchy.id == hierarchy_id).delete(
        synchronize_session=False
    )
    session.commit()


class TestLevelScoping:
    def test_legacy_levels_carry_no_hierarchy(self, session):
        """The default Syrian ladder stays global, which is what every install has today."""
        legacy = LocationAdminLevel.in_hierarchy(None).all()
        assert len(legacy) >= 3
        assert all(l.hierarchy_id is None for l in legacy)

    def test_codes_restart_inside_a_hierarchy(self, session, hierarchy):
        """Duplicate codes across hierarchies are legal, they are only unique within one."""
        assert LocationAdminLevel.max_code(hierarchy.id) == 3
        assert {l.code for l in LocationAdminLevel.in_hierarchy(hierarchy.id)} == {1, 2, 3}
        assert LocationAdminLevel.in_hierarchy(None).filter_by(code=1).count() == 1

    def test_duplicate_code_within_a_hierarchy_is_rejected(self, session, hierarchy):
        session.add(LocationAdminLevel(code=1, title="Dup", hierarchy_id=hierarchy.id))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    def test_duplicate_legacy_code_is_rejected(self, session):
        """The partial index is what protects the global defaults from duplicates."""
        session.add(LocationAdminLevel(code=1, title="Dup legacy"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

    def test_level_order_falls_back_to_code(self, session, hierarchy):
        """Legacy rows predate display_order, so ordering must not depend on it."""
        level = LocationAdminLevel(code=4, title="Unordered", hierarchy_id=hierarchy.id)
        session.add(level)
        session.commit()
        assert level.level_order == 4
        found = (
            LocationAdminLevel.in_hierarchy(hierarchy.id)
            .order_by(LocationAdminLevel.level_order.desc())
            .first()
        )
        assert found.id == level.id
        session.delete(level)
        session.commit()


class TestLevelEndpoints:
    def test_list_scoped_by_hierarchy(self, admin_client, hierarchy):
        resp = admin_client.get(f"/admin/api/location-admin-levels/?hierarchy_id={hierarchy.id}")
        titles = {i["title"] for i in resp.json["data"]["items"]}
        assert titles == {"Territory", "Governorate", "Locality"}

        resp = admin_client.get("/admin/api/location-admin-levels/?hierarchy_id=null")
        assert all(i["hierarchy"] is None for i in resp.json["data"]["items"])
        assert "Territory" not in {i["title"] for i in resp.json["data"]["items"]}

    def test_list_unscoped_returns_every_level(self, admin_client, hierarchy):
        resp = admin_client.get("/admin/api/location-admin-levels/?per_page=1000")
        titles = {i["title"] for i in resp.json["data"]["items"]}
        assert "Territory" in titles and "Governorate" in titles

    def test_create_assigns_next_code_inside_its_hierarchy(self, session, admin_client, hierarchy):
        resp = admin_client.post(
            "/admin/api/location-admin-level",
            json={"item": {"title": "Neighbourhood", "code": 4, "hierarchy_id": hierarchy.id}},
            headers=HEADERS,
        )
        assert resp.status_code == 201
        assert resp.json["data"]["item"]["hierarchy"]["id"] == hierarchy.id
        created = session.get(LocationAdminLevel, resp.json["data"]["item"]["id"])
        session.delete(created)
        session.commit()

    def test_create_rejects_a_code_that_skips_the_hierarchy_sequence(self, admin_client, hierarchy):
        resp = admin_client.post(
            "/admin/api/location-admin-level",
            json={"item": {"title": "Too far", "code": 9, "hierarchy_id": hierarchy.id}},
            headers=HEADERS,
        )
        assert resp.status_code == 400

    def test_create_rejects_an_unknown_hierarchy(self, admin_client):
        resp = admin_client.post(
            "/admin/api/location-admin-level",
            json={"item": {"title": "Orphan", "code": 1, "hierarchy_id": 999999}},
            headers=HEADERS,
        )
        assert resp.status_code == 404

    def test_a_serialized_level_can_be_sent_straight_back(self, session, admin_client, hierarchy):
        """The admin table PUTs the row exactly as it loaded it, hierarchy keys included."""
        level = LocationAdminLevel.in_hierarchy(hierarchy.id).filter_by(code=3).first()
        payload = level.to_dict()
        payload["title"] = "Locality (renamed)"
        resp = admin_client.put(
            f"/admin/api/location-admin-level/{level.id}",
            json={"item": payload},
            headers=HEADERS,
        )
        assert resp.status_code == 200

    def test_level_cannot_move_between_hierarchies(self, session, admin_client, hierarchy):
        level = LocationAdminLevel.in_hierarchy(hierarchy.id).filter_by(code=3).first()
        resp = admin_client.put(
            f"/admin/api/location-admin-level/{level.id}",
            json={"item": {"title": "Locality", "code": 3, "hierarchy_id": None}},
            headers=HEADERS,
        )
        assert resp.status_code == 400

    def test_legacy_defaults_are_protected_by_code_not_id(self, session, admin_client):
        """The old guard hard-coded ids 1-3, which breaks on any reseeded install."""
        level = LocationAdminLevel.in_hierarchy(None).filter_by(code=2).first()
        resp = admin_client.delete(f"/admin/api/location-admin-level/{level.id}")
        assert resp.status_code == 400

    def test_only_the_highest_level_of_a_hierarchy_is_deletable(
        self, session, admin_client, hierarchy
    ):
        middle = LocationAdminLevel.in_hierarchy(hierarchy.id).filter_by(code=2).first()
        resp = admin_client.delete(f"/admin/api/location-admin-level/{middle.id}")
        assert resp.status_code == 400

        top = LocationAdminLevel.in_hierarchy(hierarchy.id).filter_by(code=3).first()
        resp = admin_client.delete(f"/admin/api/location-admin-level/{top.id}")
        assert resp.status_code == 200
        # the partner ladder may drop below three levels, that floor is legacy-only
        assert LocationAdminLevel.in_hierarchy(hierarchy.id).count() == 2

    def test_reorder_rejects_mixed_hierarchies(self, session, admin_client, hierarchy):
        legacy_id = LocationAdminLevel.in_hierarchy(None).first().id
        ids = [l.id for l in LocationAdminLevel.in_hierarchy(hierarchy.id)]
        resp = admin_client.post(
            "/admin/api/location-admin-levels/reorder",
            json={"order": ids + [legacy_id], "hierarchy_id": hierarchy.id},
            headers=HEADERS,
        )
        assert resp.status_code == 400

    def test_reorder_scoped_to_one_hierarchy(self, session, admin_client, hierarchy):
        ids = [l.id for l in LocationAdminLevel.in_hierarchy(hierarchy.id)]
        resp = admin_client.post(
            "/admin/api/location-admin-levels/reorder",
            json={"order": list(reversed(ids)), "hierarchy_id": hierarchy.id},
            headers=HEADERS,
        )
        assert resp.status_code == 200
        session.expire_all()
        assert session.get(LocationAdminLevel, ids[-1]).display_order == 1


class TestHierarchyEndpoints:
    def test_create(self, session, admin_client):
        resp = admin_client.post(
            "/admin/api/location-hierarchy",
            json={"item": {"title": "UK ONS", "title_tr": "المملكة المتحدة"}},
            headers=HEADERS,
        )
        assert resp.status_code == 201
        created = session.get(LocationHierarchy, resp.json["data"]["item"]["id"])
        assert created.title == "UK ONS"
        session.delete(created)
        session.commit()

    def test_update(self, session, admin_client, hierarchy):
        resp = admin_client.put(
            f"/admin/api/location-hierarchy/{hierarchy.id}",
            json={"item": {"title": "Palestine (revised)"}},
            headers=HEADERS,
        )
        assert resp.status_code == 200

    def test_delete(self, session, admin_client):
        h = LocationHierarchy(title="Israel CBS")
        session.add(h)
        session.commit()
        id = h.id

        assert admin_client.delete(f"/admin/api/location-hierarchy/{id}").status_code == 200
        assert LocationHierarchy.query.filter_by(id=id).count() == 0

    def test_cannot_delete_a_hierarchy_that_still_has_levels(self, admin_client, hierarchy):
        resp = admin_client.delete(f"/admin/api/location-hierarchy/{hierarchy.id}")
        assert resp.status_code == 409

    @pytest.mark.parametrize(
        "client_fixture, expected",
        [("admin_client", 201), ("da_client", 403), ("mod_client", 403)],
    )
    def test_create_is_admin_only(self, request, session, client_fixture, expected):
        client = request.getfixturevalue(client_fixture)
        resp = client.post(
            "/admin/api/location-hierarchy",
            json={"item": {"title": f"Scoped {client_fixture}"}},
            headers=HEADERS,
        )
        assert resp.status_code == expected
        if expected == 201:
            session.query(LocationHierarchy).filter_by(id=resp.json["data"]["item"]["id"]).delete(
                synchronize_session=False
            )
            session.commit()


@pytest.fixture
def ladder(session, hierarchy):
    """A two-rung location tree inside the partner hierarchy."""
    admin_type = LocationType.query.filter_by(title="Administrative Location").first()
    levels = {l.code: l for l in LocationAdminLevel.in_hierarchy(hierarchy.id)}
    level_ids = {code: l.id for code, l in levels.items()}
    territory = Location(
        title="West Bank",
        location_type=admin_type,
        admin_level=levels[1],
        full_location="West Bank",
    )
    session.add(territory)
    session.commit()
    governorate = Location(
        title="Ramallah",
        location_type=admin_type,
        admin_level=levels[2],
        parent_id=territory.id,
        full_location="West Bank, Ramallah",
    )
    session.add(governorate)
    session.commit()
    ids = [governorate.id, territory.id]
    yield territory.id, governorate.id, level_ids
    session.query(Location).filter(Location.id.in_(ids)).delete(synchronize_session=False)
    session.commit()


class TestLocationSearch:
    def test_admin_level_filter_uses_the_level_id(self, admin_client, ladder):
        """Regression: the filter compared an incoming code against admin_level_id."""
        territory_id, _, levels = ladder
        resp = admin_client.post(
            "/admin/api/locations/",
            json={
                "q": {"admin_level": {"id": levels[1], "code": 1}},
                "options": {},
            },
            headers=HEADERS,
        )
        assert [i["id"] for i in resp.json["data"]["items"]] == [territory_id]

    def test_parent_of_resolves_the_preceding_level(self, admin_client, ladder):
        """Eligible parents come from the level order, not from the child's code minus one."""
        territory_id, governorate_id, levels = ladder
        resp = admin_client.post(
            "/admin/api/locations/",
            json={"q": {"parent_of": levels[2]}, "options": {}},
            headers=HEADERS,
        )
        assert [i["id"] for i in resp.json["data"]["items"]] == [territory_id]

        resp = admin_client.post(
            "/admin/api/locations/",
            json={"q": {"parent_of": levels[3]}, "options": {}},
            headers=HEADERS,
        )
        assert [i["id"] for i in resp.json["data"]["items"]] == [governorate_id]

    def test_top_level_has_no_eligible_parents(self, admin_client, ladder):
        _, _, levels = ladder
        resp = admin_client.post(
            "/admin/api/locations/",
            json={"q": {"parent_of": levels[1]}, "options": {}},
            headers=HEADERS,
        )
        assert resp.json["data"]["items"] == []

    def test_lvl_lookup_defaults_to_legacy_levels(self, admin_client, ladder):
        """A request with no hierarchy must not pick up a partner level sharing that code."""
        territory_id, _, _ = ladder
        resp = admin_client.post(
            "/admin/api/locations/", json={"q": {"lvl": 1}, "options": {}}, headers=HEADERS
        )
        assert territory_id not in [i["id"] for i in resp.json["data"]["items"]]

    def test_lvl_lookup_scoped_to_a_hierarchy(self, admin_client, ladder, hierarchy):
        territory_id, _, _ = ladder
        resp = admin_client.post(
            "/admin/api/locations/",
            json={"q": {"lvl": 1, "hierarchy_id": hierarchy.id}, "options": {}},
            headers=HEADERS,
        )
        assert [i["id"] for i in resp.json["data"]["items"]] == [territory_id]


class TestBackwardCompatibility:
    def test_location_serializer_is_unchanged_for_legacy_rows(self, session):
        """Legacy locations keep their id, parents and serialized shape."""
        admin_type = LocationType.query.filter_by(title="Administrative Location").first()
        level = LocationAdminLevel.in_hierarchy(None).filter_by(code=1).first()
        loc = Location(title="Sidnaya", location_type=admin_type, admin_level=level)
        session.add(loc)
        session.commit()

        data = loc.to_dict()
        assert data["id"] == loc.id
        assert data["admin_level"]["hierarchy"] is None
        assert data["admin_level"]["code"] == 1
        assert set(data) >= {"id", "title", "full_location", "parent", "admin_level"}

        session.delete(loc)
        session.commit()
