"""
RBAC tests for user management endpoints.
Ported from tests/admin/test_users.py (main branch).
"""

import uuid
from unittest.mock import patch
from uuid import uuid4

import pytest
from flask import current_app

from enferno.user.models import Session, User, WebAuthn
from tests.factories import UserFactory, WebAuthnFactory

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


# =========================================================================
# POST /admin/api/user/ - invalid email
# =========================================================================


class TestUserCreateInvalidEmail:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 400),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_create_invalid_email(self, request, session, client_fixture, expected):
        with patch.dict(
            current_app.config,
            {"MAIL_ENABLED": True, "MAIL_ALLOWED_DOMAINS": ["valid_domain.com"]},
        ):
            user = UserFactory()
            user.fs_uniquifier = uuid4().hex
            data = _user_payload(user)
            data["email"] = "email@invalid-domain.com"
            client = request.getfixturevalue(client_fixture)
            resp = client.post(
                "/admin/api/user/",
                json={"item": data},
                headers=HEADERS,
            )
            assert resp.status_code == expected
            if expected == 400:
                assert "valid_domain.com" in resp.json["errors"]["item.email"]


# =========================================================================
# POST /admin/api/user/ - allow all domains
# =========================================================================


class TestUserCreateAllowAllDomains:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 201),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_create_allow_all_domains(self, request, session, client_fixture, expected):
        with patch.dict(
            current_app.config,
            {"MAIL_ENABLED": True, "MAIL_ALLOWED_DOMAINS": ["*"]},
        ):
            user = UserFactory()
            user.fs_uniquifier = uuid4().hex
            data = _user_payload(user)
            data["email"] = "email@any-domain.com"
            client = request.getfixturevalue(client_fixture)
            resp = client.post(
                "/admin/api/user/",
                json={"item": data},
                headers=HEADERS,
            )
            assert resp.status_code == expected


# =========================================================================
# POST /admin/api/user/ - conflict (409)
# =========================================================================


class TestUserCreateConflict:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 409),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_create_conflict_username(self, request, session, client_fixture, expected):
        existing = UserFactory()
        existing.fs_uniquifier = uuid4().hex
        session.add(existing)
        session.commit()

        dup = UserFactory()
        dup.username = existing.username
        client = request.getfixturevalue(client_fixture)
        resp = client.post(
            "/admin/api/user/",
            json={"item": _user_payload(dup)},
            headers=HEADERS,
        )
        assert resp.status_code == expected
        found = User.query.filter(User.username == existing.username).first()
        assert found.id == existing.id

    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 409),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_create_conflict_email(self, request, session, client_fixture, expected):
        existing = UserFactory()
        existing.fs_uniquifier = uuid4().hex
        session.add(existing)
        session.commit()

        dup = UserFactory()
        dup.email = existing.email
        client = request.getfixturevalue(client_fixture)
        resp = client.post(
            "/admin/api/user/",
            json={"item": _user_payload(dup)},
            headers=HEADERS,
        )
        assert resp.status_code == expected
        found = User.query.filter(User.email == existing.email).first()
        assert found.id == existing.id


# =========================================================================
# POST /admin/api/checkuser/
# =========================================================================


class TestCheckUser:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_checkuser(self, request, session, client_fixture, expected):
        existing = UserFactory()
        existing.fs_uniquifier = uuid4().hex
        session.add(existing)
        session.commit()

        client = request.getfixturevalue(client_fixture)
        if expected == 200:
            # Existing username should return 409
            resp = client.post(
                "/admin/api/checkuser/",
                json={"item": existing.username},
                headers=HEADERS,
            )
            assert resp.status_code == 409

        # Fresh username should return expected status
        fresh = UserFactory()
        resp = client.post(
            "/admin/api/checkuser/",
            json={"item": fresh.username},
            headers=HEADERS,
        )
        assert resp.status_code == expected


# =========================================================================
# PUT /admin/api/user/ - conflict (409)
# =========================================================================


class TestUserUpdateConflict:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 409),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_update_conflict_username(self, request, session, client_fixture, expected):
        existing = UserFactory()
        existing.fs_uniquifier = uuid4().hex
        session.add(existing)
        session.commit()

        target = UserFactory()
        target.fs_uniquifier = uuid4().hex
        session.add(target)
        session.commit()

        new_data = UserFactory()
        new_data.username = existing.username
        payload = _user_payload(new_data)
        payload["id"] = target.id
        del payload["password"]

        client = request.getfixturevalue(client_fixture)
        resp = client.put(
            "/admin/api/user/",
            json={"item": payload},
            headers=HEADERS,
        )
        assert resp.status_code == expected
        found = User.query.filter(User.username == existing.username).first()
        assert found.id == existing.id

    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 409),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_update_conflict_email(self, request, session, client_fixture, expected):
        existing = UserFactory()
        existing.fs_uniquifier = uuid4().hex
        session.add(existing)
        session.commit()

        target = UserFactory()
        target.fs_uniquifier = uuid4().hex
        session.add(target)
        session.commit()

        new_data = UserFactory()
        payload = _user_payload(new_data)
        payload["id"] = target.id
        payload["email"] = existing.email
        del payload["password"]

        client = request.getfixturevalue(client_fixture)
        resp = client.put(
            "/admin/api/user/",
            json={"item": payload},
            headers=HEADERS,
        )
        assert resp.status_code == expected
        found = User.query.filter(User.email == existing.email).first()
        assert found.id == existing.id


# =========================================================================
# POST /admin/api/user/force-reset
# =========================================================================


class TestForceReset:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_force_reset(self, request, session, client_fixture, expected):
        target = UserFactory()
        target.fs_uniquifier = uuid4().hex
        session.add(target)
        session.commit()

        client = request.getfixturevalue(client_fixture)
        resp = client.post(
            "/admin/api/user/force-reset",
            json={"item": {"id": target.id}},
            headers=HEADERS,
        )
        assert resp.status_code == expected


# =========================================================================
# POST /admin/api/user/force-reset-all
# =========================================================================


class TestForceResetAll:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_force_reset_all(self, request, session, client_fixture, expected):
        client = request.getfixturevalue(client_fixture)
        resp = client.post(
            "/admin/api/user/force-reset-all",
            headers=HEADERS,
            follow_redirects=True,
        )
        assert resp.status_code == expected


# =========================================================================
# GET /admin/api/user/<int:id>/sessions
# =========================================================================


class MockRedis:
    def __init__(self):
        self._data = {}

    def set(self, key, value):
        self._data[key] = value

    def get(self, key):
        return self._data.get(key)

    def delete(self, key):
        if key in self._data:
            del self._data[key]

    def exists(self, key):
        return key in self._data


class TestUserSessions:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_get_sessions(self, request, session, client_fixture, expected):
        target = UserFactory()
        target.fs_uniquifier = uuid4().hex
        session.add(target)
        session.commit()

        sess = Session()
        sess.user_id = target.id
        sess.ip_address = "127.0.0.1"
        sess.session_token = uuid.uuid4().hex
        session.add(sess)
        session.commit()

        client = request.getfixturevalue(client_fixture)
        resp = client.get(
            f"/admin/api/user/{target.id}/sessions",
            headers=HEADERS,
        )
        assert resp.status_code == expected


# =========================================================================
# DELETE /admin/api/session/logout (single session)
# =========================================================================


class TestSessionLogout:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_session_logout(self, request, session, client_fixture, expected):
        rds = MockRedis()
        target = UserFactory()
        target.fs_uniquifier = uuid4().hex
        session.add(target)
        session.commit()

        sess = Session()
        sess.user_id = target.id
        sess.ip_address = "127.0.0.1"
        sess.session_token = uuid.uuid4().hex
        session.add(sess)
        session.commit()

        control = Session()
        control.user_id = target.id
        control.ip_address = "127.0.0.1"
        control.session_token = uuid.uuid4().hex
        session.add(control)
        session.commit()

        rds.set(f"session:{sess.session_token}", "1")
        rds.set(f"session:{control.session_token}", "1")

        client = request.getfixturevalue(client_fixture)
        with patch.dict(current_app.config, {"SESSION_REDIS": rds}):
            resp = client.delete(
                "/admin/api/session/logout",
                json={"sessid": sess.id},
                headers=HEADERS,
            )
            assert resp.status_code == expected
            if expected == 200:
                assert not rds.exists(f"session:{sess.session_token}")
                assert rds.exists(f"session:{control.session_token}")


# =========================================================================
# DELETE /admin/api/user/<int:id>/sessions/logout (all sessions)
# =========================================================================


class TestUserSessionsLogout:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_user_sessions_logout(self, request, session, client_fixture, expected):
        rds = MockRedis()
        target = UserFactory()
        target.fs_uniquifier = uuid4().hex
        session.add(target)
        session.commit()

        sess1 = Session()
        sess1.user_id = target.id
        sess1.ip_address = "127.0.0.1"
        sess1.session_token = uuid.uuid4().hex
        session.add(sess1)
        session.commit()

        sess2 = Session()
        sess2.user_id = target.id
        sess2.ip_address = "127.0.0.1"
        sess2.session_token = uuid.uuid4().hex
        session.add(sess2)
        session.commit()

        rds.set(f"session:{sess1.session_token}", "1")
        rds.set(f"session:{sess2.session_token}", "1")

        client = request.getfixturevalue(client_fixture)
        with patch.dict(current_app.config, {"SESSION_REDIS": rds}):
            resp = client.delete(
                f"/admin/api/user/{target.id}/sessions/logout",
                headers=HEADERS,
            )
            assert resp.status_code == expected
            if expected == 200:
                assert not rds.exists(f"session:{sess1.session_token}")
                assert not rds.exists(f"session:{sess2.session_token}")


# =========================================================================
# DELETE /admin/api/user/revoke_2fa
# =========================================================================


class TestRevoke2FA:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_revoke_2fa(self, request, session, client_fixture, expected):
        target = UserFactory()
        target.fs_uniquifier = uuid4().hex
        session.add(target)
        session.commit()

        assert target.tf_totp_secret
        assert target.tf_phone_number
        assert target.tf_primary_method

        webauthn = WebAuthnFactory()
        webauthn.user_id = target.id
        session.add(webauthn)
        session.commit()
        found_wa = session.query(WebAuthn).filter(WebAuthn.user_id == target.id).all()
        assert len(found_wa) == 1

        client = request.getfixturevalue(client_fixture)
        resp = client.delete(
            f"/admin/api/user/revoke_2fa?user_id={target.id}",
            headers=HEADERS,
        )
        assert resp.status_code == expected
        found_user = session.query(User).filter(User.id == target.id).first()
        assert found_user
        new_wa = session.query(WebAuthn).filter(WebAuthn.user_id == target.id).all()
        if expected == 200:
            assert found_user.tf_totp_secret is None
            assert found_user.tf_phone_number is None
            assert found_user.tf_primary_method is None
            assert len(new_wa) == 0
        else:
            assert found_user.tf_totp_secret == target.tf_totp_secret
            assert found_user.tf_phone_number == target.tf_phone_number
            assert found_user.tf_primary_method == target.tf_primary_method
            assert len(new_wa) == 1
