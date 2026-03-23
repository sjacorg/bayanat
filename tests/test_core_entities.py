"""
RBAC tests for core entities: Bulletins, Actors, Incidents.
Uses savepoint isolation (session fixture) and parametrized client fixtures.
"""

import json
from unittest.mock import patch

import pytest
from flask import current_app

from enferno.admin.models import (
    Actor,
    Bulletin,
    Incident,
)
from enferno.user.models import User
from tests.factories import (
    ActorFactory,
    BulletinFactory,
    IncidentFactory,
)

HEADERS = {"Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_uid(users, client_fixture):
    admin_user, da_user, mod_user, _ = users
    if client_fixture == "admin_client":
        return admin_user.id
    if client_fixture == "da_client":
        return da_user.id
    if client_fixture == "mod_client":
        return mod_user.id
    return None


# =========================================================================
# BULLETIN tests
# =========================================================================


class TestBulletinCreate:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 201),
            ("da_client", 201),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_create(self, request, session, client_fixture, expected):
        client = request.getfixturevalue(client_fixture)
        b = BulletinFactory()
        payload = b.to_dict()
        payload.pop("roles", None)
        resp = client.post(
            "/admin/api/bulletin",
            json={"item": payload},
            headers=HEADERS,
            follow_redirects=True,
        )
        assert resp.status_code == expected


class TestBulletinGetById:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 200),
            ("mod_client", 200),
            ("anonymous_client", 401),
        ],
    )
    def test_get_by_id(self, request, session, client_fixture, expected):
        b = BulletinFactory()
        session.add(b)
        session.commit()
        client = request.getfixturevalue(client_fixture)
        with patch.dict(current_app.config, {"ACCESS_CONTROL_RESTRICTIVE": False}):
            resp = client.get(
                f"/admin/api/bulletin/{b.id}",
                headers={"Accept": "application/json"},
            )
        assert resp.status_code == expected


class TestBulletinGetRestrictive:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_get_restrictive(self, request, session, client_fixture, expected):
        b = BulletinFactory()
        session.add(b)
        session.commit()
        client = request.getfixturevalue(client_fixture)
        with patch.dict(current_app.config, {"ACCESS_CONTROL_RESTRICTIVE": True}):
            resp = client.get(
                f"/admin/api/bulletin/{b.id}",
                headers={"Accept": "application/json"},
            )
        assert resp.status_code == expected


class TestBulletinUpdateUnassigned:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_update_unassigned(self, request, session, client_fixture, expected):
        b = BulletinFactory()
        session.add(b)
        session.commit()
        payload = b.to_dict()
        payload.pop("roles", None)
        payload["title"] = "Updated title"
        client = request.getfixturevalue(client_fixture)
        resp = client.put(
            f"/admin/api/bulletin/{b.id}",
            json={"item": payload},
            headers=HEADERS,
        )
        assert resp.status_code == expected


class TestBulletinUpdateAssigned:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 200),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_update_assigned(self, request, session, users, client_fixture, expected):
        b = BulletinFactory()
        session.add(b)
        session.commit()
        uid = _get_uid(users, client_fixture)
        if uid:
            b.assigned_to = User.query.filter(User.id == uid).first()
            session.commit()
        payload = b.to_dict()
        payload.pop("roles", None)
        payload["title"] = "Updated assigned"
        client = request.getfixturevalue(client_fixture)
        with patch.dict(current_app.config, {"ACCESS_CONTROL_RESTRICTIVE": False}):
            resp = client.put(
                f"/admin/api/bulletin/{b.id}",
                json={"item": payload},
                headers=HEADERS,
            )
        assert resp.status_code == expected


class TestBulletinReview:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 200),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_review(self, request, session, users, client_fixture, expected):
        b = BulletinFactory()
        admin_user, _, _, _ = users
        b.assigned_to = admin_user
        b.first_peer_reviewer = admin_user
        session.add(b)
        session.commit()
        nb = BulletinFactory()
        client = request.getfixturevalue(client_fixture)
        with patch.dict(current_app.config, {"ACCESS_CONTROL_RESTRICTIVE": False}):
            resp = client.put(
                f"/admin/api/bulletin/review/{b.id}",
                json={"item": nb.to_dict()},
                headers=HEADERS,
            )
        assert resp.status_code == expected


class TestBulletinBulk:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 200),
            ("anonymous_client", 401),
        ],
    )
    def test_bulk(self, request, session, client_fixture, expected):
        b = BulletinFactory()
        session.add(b)
        session.commit()
        client = request.getfixturevalue(client_fixture)
        resp = client.put(
            "/admin/api/bulletin/bulk",
            json={"items": [b.id], "bulk": {"status": "bulk updated"}},
            headers=HEADERS,
            follow_redirects=True,
        )
        assert resp.status_code == expected


class TestBulletinSelfAssign:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
            ("admin_sa_client", 200),
            ("da_sa_client", 200),
            ("mod_sa_client", 403),
        ],
    )
    def test_self_assign(self, request, session, client_fixture, expected):
        b = BulletinFactory()
        session.add(b)
        session.commit()
        # Unassign before each role test
        b.assigned_to = None
        b.assigned_to_id = None
        session.commit()
        client = request.getfixturevalue(client_fixture)
        with patch.dict(current_app.config, {"ACCESS_CONTROL_RESTRICTIVE": False}):
            resp = client.put(
                f"/admin/api/bulletin/assign/{b.id}",
                json={"bulletin": {"comments": "mandatory"}},
                headers=HEADERS,
            )
        assert resp.status_code == expected


class TestBulletinRelations:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 200),
            ("mod_client", 200),
            ("anonymous_client", 401),
        ],
    )
    def test_relations(self, request, session, client_fixture, expected):
        b1 = BulletinFactory()
        b2 = BulletinFactory()
        session.add_all([b1, b2])
        session.commit()
        b2.relate_bulletin(b1, json.dumps({}), False)
        client = request.getfixturevalue(client_fixture)
        resp = client.get(
            f"/admin/api/bulletin/relations/{b1.id}?class=bulletin",
            headers=HEADERS,
        )
        assert resp.status_code == expected


# =========================================================================
# ACTOR tests
# =========================================================================


class TestActorCreate:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 201),
            ("da_client", 201),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_create(self, request, session, client_fixture, expected):
        client = request.getfixturevalue(client_fixture)
        a = ActorFactory()
        payload = a.to_dict()
        payload["actor_profiles"] = [{"mode": 1}]
        payload["id_number"] = a.id_number
        resp = client.post(
            "/admin/api/actor",
            json={"item": payload},
            headers=HEADERS,
            follow_redirects=True,
        )
        assert resp.status_code == expected


class TestActorGetById:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 200),
            ("mod_client", 200),
            ("anonymous_client", 401),
        ],
    )
    def test_get_by_id(self, request, session, client_fixture, expected):
        a = ActorFactory()
        session.add(a)
        session.commit()
        client = request.getfixturevalue(client_fixture)
        with patch.dict(current_app.config, {"ACCESS_CONTROL_RESTRICTIVE": False}):
            resp = client.get(
                f"/admin/api/actor/{a.id}",
                headers=HEADERS,
            )
        assert resp.status_code == expected


class TestActorGetRestrictive:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_get_restrictive(self, request, session, client_fixture, expected):
        a = ActorFactory()
        session.add(a)
        session.commit()
        client = request.getfixturevalue(client_fixture)
        with patch.dict(current_app.config, {"ACCESS_CONTROL_RESTRICTIVE": True}):
            resp = client.get(
                f"/admin/api/actor/{a.id}",
                headers=HEADERS,
            )
        assert resp.status_code == expected


class TestActorUpdateUnassigned:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_update_unassigned(self, request, session, client_fixture, expected):
        a = ActorFactory()
        session.add(a)
        session.commit()
        payload = a.to_dict()
        payload["name"] = "Updated name"
        payload["comments"] = "updated"
        payload["actor_profiles"] = [{"mode": 1}]
        payload["id_number"] = a.id_number
        client = request.getfixturevalue(client_fixture)
        resp = client.put(
            f"/admin/api/actor/{a.id}",
            json={"item": payload},
            headers=HEADERS,
        )
        assert resp.status_code == expected


class TestActorUpdateAssigned:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 200),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_update_assigned(self, request, session, users, client_fixture, expected):
        a = ActorFactory()
        session.add(a)
        session.commit()
        uid = _get_uid(users, client_fixture)
        if uid:
            a.assigned_to = User.query.filter(User.id == uid).first()
            session.commit()
        payload = a.to_dict()
        payload["name"] = "Updated assigned"
        payload["id_number"] = a.id_number
        payload["actor_profiles"] = [{"mode": 1}]
        client = request.getfixturevalue(client_fixture)
        with patch.dict(current_app.config, {"ACCESS_CONTROL_RESTRICTIVE": False}):
            resp = client.put(
                f"/admin/api/actor/{a.id}",
                json={"item": payload},
                headers=HEADERS,
            )
        assert resp.status_code == expected


class TestActorReview:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 200),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_review(self, request, session, users, client_fixture, expected):
        a = ActorFactory()
        admin_user, _, _, _ = users
        a.assigned_to = admin_user
        a.first_peer_reviewer = admin_user
        session.add(a)
        session.commit()
        na = ActorFactory()
        na_dict = na.to_dict()
        na_dict["id_number"] = na.id_number
        client = request.getfixturevalue(client_fixture)
        with patch.dict(current_app.config, {"ACCESS_CONTROL_RESTRICTIVE": False}):
            resp = client.put(
                f"/admin/api/actor/review/{a.id}",
                json={"item": na_dict},
                headers=HEADERS,
            )
        assert resp.status_code == expected


class TestActorBulk:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 200),
            ("anonymous_client", 401),
        ],
    )
    def test_bulk(self, request, session, client_fixture, expected):
        a = ActorFactory()
        session.add(a)
        session.commit()
        client = request.getfixturevalue(client_fixture)
        resp = client.put(
            "/admin/api/actor/bulk/",
            json={"items": [a.id], "bulk": {"status": "bulk updated"}},
            headers=HEADERS,
        )
        assert resp.status_code == expected


class TestActorSelfAssign:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
            ("admin_sa_client", 200),
            ("da_sa_client", 200),
            ("mod_sa_client", 403),
        ],
    )
    def test_self_assign(self, request, session, client_fixture, expected):
        a = ActorFactory()
        session.add(a)
        session.commit()
        a.assigned_to = None
        a.assigned_to_id = None
        session.commit()
        client = request.getfixturevalue(client_fixture)
        with patch.dict(current_app.config, {"ACCESS_CONTROL_RESTRICTIVE": False}):
            resp = client.put(
                f"/admin/api/actor/assign/{a.id}",
                json={"actor": {"comments": "mandatory"}},
                headers=HEADERS,
            )
        assert resp.status_code == expected


class TestActorRelations:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 200),
            ("mod_client", 200),
            ("anonymous_client", 401),
        ],
    )
    def test_relations(self, request, session, client_fixture, expected):
        a1 = ActorFactory()
        a2 = ActorFactory()
        session.add_all([a1, a2])
        session.commit()
        a2.relate_actor(a1, json.dumps({}), False)
        client = request.getfixturevalue(client_fixture)
        resp = client.get(
            f"/admin/api/actor/relations/{a1.id}?class=actor",
            headers=HEADERS,
        )
        assert resp.status_code == expected


# =========================================================================
# INCIDENT tests
# =========================================================================


class TestIncidentCreate:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 201),
            ("da_client", 201),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_create(self, request, session, client_fixture, expected):
        client = request.getfixturevalue(client_fixture)
        i = IncidentFactory()
        resp = client.post(
            "/admin/api/incident",
            json={"item": i.to_dict()},
            headers=HEADERS,
            follow_redirects=True,
        )
        assert resp.status_code == expected


class TestIncidentGetById:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 200),
            ("mod_client", 200),
            ("anonymous_client", 401),
        ],
    )
    def test_get_by_id(self, request, session, client_fixture, expected):
        i = IncidentFactory()
        session.add(i)
        session.commit()
        client = request.getfixturevalue(client_fixture)
        with patch.dict(current_app.config, {"ACCESS_CONTROL_RESTRICTIVE": False}):
            resp = client.get(
                f"/admin/api/incident/{i.id}",
                headers={"Accept": "application/json"},
            )
        assert resp.status_code == expected


class TestIncidentGetRestrictive:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_get_restrictive(self, request, session, client_fixture, expected):
        i = IncidentFactory()
        session.add(i)
        session.commit()
        client = request.getfixturevalue(client_fixture)
        with patch.dict(current_app.config, {"ACCESS_CONTROL_RESTRICTIVE": True}):
            resp = client.get(
                f"/admin/api/incident/{i.id}",
                headers={"Accept": "application/json"},
            )
        assert resp.status_code == expected


class TestIncidentUpdateUnassigned:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_update_unassigned(self, request, session, client_fixture, expected):
        i = IncidentFactory()
        session.add(i)
        session.commit()
        payload = i.to_dict()
        payload["title"] = "Updated title"
        payload["comments"] = "updated"
        client = request.getfixturevalue(client_fixture)
        resp = client.put(
            f"/admin/api/incident/{i.id}",
            json={"item": payload},
            headers=HEADERS,
        )
        assert resp.status_code == expected


class TestIncidentUpdateAssigned:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 200),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_update_assigned(self, request, session, users, client_fixture, expected):
        i = IncidentFactory()
        session.add(i)
        session.commit()
        uid = _get_uid(users, client_fixture)
        if uid:
            i.assigned_to = User.query.filter(User.id == uid).first()
            session.commit()
        payload = i.to_dict()
        payload["title"] = "Updated assigned"
        client = request.getfixturevalue(client_fixture)
        with patch.dict(current_app.config, {"ACCESS_CONTROL_RESTRICTIVE": False}):
            resp = client.put(
                f"/admin/api/incident/{i.id}",
                json={"item": payload},
                headers=HEADERS,
            )
        assert resp.status_code == expected


class TestIncidentReview:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 200),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_review(self, request, session, users, client_fixture, expected):
        i = IncidentFactory()
        admin_user, _, _, _ = users
        i.assigned_to = admin_user
        i.first_peer_reviewer = admin_user
        session.add(i)
        session.commit()
        ni = IncidentFactory()
        client = request.getfixturevalue(client_fixture)
        with patch.dict(current_app.config, {"ACCESS_CONTROL_RESTRICTIVE": False}):
            resp = client.put(
                f"/admin/api/incident/review/{i.id}",
                json={"item": ni.to_dict()},
                headers=HEADERS,
            )
        assert resp.status_code == expected


class TestIncidentBulk:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 200),
            ("anonymous_client", 401),
        ],
    )
    def test_bulk(self, request, session, client_fixture, expected):
        i = IncidentFactory()
        session.add(i)
        session.commit()
        client = request.getfixturevalue(client_fixture)
        resp = client.put(
            "/admin/api/incident/bulk",
            json={"items": [i.id], "bulk": {"status": "bulk updated"}},
            headers=HEADERS,
            follow_redirects=True,
        )
        assert resp.status_code == expected


class TestIncidentSelfAssign:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
            ("admin_sa_client", 200),
            ("da_sa_client", 200),
            ("mod_sa_client", 403),
        ],
    )
    def test_self_assign(self, request, session, client_fixture, expected):
        i = IncidentFactory()
        session.add(i)
        session.commit()
        i.assigned_to = None
        i.assigned_to_id = None
        session.commit()
        client = request.getfixturevalue(client_fixture)
        with patch.dict(current_app.config, {"ACCESS_CONTROL_RESTRICTIVE": False}):
            resp = client.put(
                f"/admin/api/incident/assign/{i.id}",
                json={"incident": {"comments": "must exist"}},
                headers=HEADERS,
            )
        assert resp.status_code == expected


class TestIncidentRelations:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 200),
            ("mod_client", 200),
            ("anonymous_client", 401),
        ],
    )
    def test_relations(self, request, session, client_fixture, expected):
        i1 = IncidentFactory()
        i2 = IncidentFactory()
        session.add_all([i1, i2])
        session.commit()
        i2.relate_incident(i1, json.dumps({}), False)
        client = request.getfixturevalue(client_fixture)
        resp = client.get(
            f"/admin/api/incident/relations/{i1.id}?class=incident",
            headers=HEADERS,
        )
        assert resp.status_code == expected
