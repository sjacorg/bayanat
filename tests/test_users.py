"""
RBAC tests for user management endpoints.
Ported from tests/admin/test_users.py (main branch).
"""

from uuid import uuid4

import pytest

from enferno.user.models import User
from tests.factories import UserFactory

HEADERS = {"Content-Type": "application/json"}


def _user_payload(user):
    return {
        "name": user.name,
        "username": user.username,
        "active": user.active,
        "password": user.password,
        "email": user.email,
    }


# =========================================================================
# GET /admin/api/users/
# =========================================================================


class TestUserList:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 200),
            ("anonymous_client", 401),
        ],
    )
    def test_list(self, request, session, client_fixture, expected):
        client = request.getfixturevalue(client_fixture)
        resp = client.get("/admin/api/users/", headers=HEADERS)
        assert resp.status_code == expected


# =========================================================================
# POST /admin/api/user/
# =========================================================================


class TestUserCreate:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 201),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_create(self, request, session, client_fixture, expected):
        user = UserFactory()
        user.fs_uniquifier = uuid4().hex
        client = request.getfixturevalue(client_fixture)
        resp = client.post(
            "/admin/api/user/",
            json={"item": _user_payload(user)},
            headers=HEADERS,
        )
        assert resp.status_code == expected
        found = User.query.filter(User.username == user.username).first()
        if expected == 201:
            assert found is not None
        else:
            assert found is None


# =========================================================================
# PUT /admin/api/user/
# =========================================================================


class TestUserUpdate:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_update(self, request, session, client_fixture, expected):
        # Create a user to update
        target = UserFactory()
        target.fs_uniquifier = uuid4().hex
        session.add(target)
        session.commit()

        new_data = UserFactory()
        payload = _user_payload(new_data)
        payload["id"] = target.id
        # Don't send password on update
        del payload["password"]

        client = request.getfixturevalue(client_fixture)
        resp = client.put(
            "/admin/api/user/",
            json={"item": payload},
            headers=HEADERS,
        )
        assert resp.status_code == expected
        found = User.query.filter(User.id == target.id).first()
        if expected == 200:
            assert found.username == new_data.username
        else:
            assert found.username != new_data.username


# =========================================================================
# DELETE /admin/api/user/<int:id>
# =========================================================================


class TestUserDelete:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_delete(self, request, session, client_fixture, expected):
        # Create an inactive user (active users cannot be deleted)
        target = UserFactory()
        target.active = False
        target.fs_uniquifier = uuid4().hex
        session.add(target)
        session.commit()

        client = request.getfixturevalue(client_fixture)
        resp = client.delete(
            f"/admin/api/user/{target.id}",
            headers=HEADERS,
        )
        assert resp.status_code == expected
        found = User.query.filter(User.id == target.id).first()
        if expected == 200:
            assert found is None
        else:
            assert found is not None


# =========================================================================
# POST /admin/api/password/
# =========================================================================


class TestPasswordChange:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 200),
            ("mod_client", 200),
            ("anonymous_client", 401),
        ],
    )
    def test_change_password(self, request, session, client_fixture, expected):
        strong_password = "On3Tw0Thr33!"
        client = request.getfixturevalue(client_fixture)
        resp = client.post(
            "/admin/api/password/",
            json={"password": strong_password},
            headers=HEADERS,
        )
        assert resp.status_code == expected

    def test_weak_password_rejected(self, request, session):
        client = request.getfixturevalue("admin_client")
        resp = client.post(
            "/admin/api/password/",
            json={"password": "1234567890"},
            headers=HEADERS,
        )
        assert resp.status_code == 400
        assert "password" in resp.json["errors"]

    def test_short_password_rejected(self, request, session):
        client = request.getfixturevalue("admin_client")
        resp = client.post(
            "/admin/api/password/",
            json={"password": "12345"},
            headers=HEADERS,
        )
        assert resp.status_code == 400
        assert "password" in resp.json["errors"]
