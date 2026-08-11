"""Tests for user account revision history."""

from uuid import uuid4

import pytest

from enferno.admin.models import UserHistory
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
# GET /admin/api/userhistory/<id>
# =========================================================================


class TestUserHistoryAccess:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_access(self, request, session, users, client_fixture, expected):
        admin_user, _, _, _ = users
        client = request.getfixturevalue(client_fixture)
        resp = client.get(f"/admin/api/userhistory/{admin_user.id}", headers=HEADERS)
        assert resp.status_code == expected

    def test_unknown_user_404(self, admin_client, session):
        resp = admin_client.get("/admin/api/userhistory/999999", headers=HEADERS)
        assert resp.status_code == 404


# =========================================================================
# Revisions recorded on write
# =========================================================================


class TestUserHistoryRecording:
    def test_create_records_revision(self, admin_client, session, users):
        admin_user, _, _, _ = users
        user = UserFactory()
        user.fs_uniquifier = uuid4().hex
        resp = admin_client.post(
            "/admin/api/user/", json={"item": _user_payload(user)}, headers=HEADERS
        )
        assert resp.status_code == 201

        created = User.query.filter_by(username=user.username).one()
        revisions = UserHistory.query.filter_by(target_user_id=created.id).all()
        assert len(revisions) == 1
        assert revisions[0].user_id == admin_user.id
        assert revisions[0].data["username"] == user.username

    def test_update_records_revision_with_permission_change(self, admin_client, session, users):
        user = UserFactory()
        user.fs_uniquifier = uuid4().hex
        session.add(user)
        session.commit()

        payload = _user_payload(user)
        payload["id"] = user.id
        payload["can_export"] = True
        resp = admin_client.put("/admin/api/user/", json={"item": payload}, headers=HEADERS)
        assert resp.status_code == 200

        revisions = UserHistory.query.filter_by(target_user_id=user.id).all()
        assert len(revisions) == 1
        assert revisions[0].data["can_export"] is True

    def test_snapshot_carries_no_secrets(self, session):
        user = UserFactory()
        user.fs_uniquifier = uuid4().hex
        session.add(user)
        session.commit()

        snapshot = user.to_history_dict()
        assert "password" not in snapshot
        assert "force_reset" not in snapshot
        assert "fs_uniquifier" not in snapshot

    def test_role_order_is_stable(self, session):
        """Unstable role order would read as a change when nothing changed."""
        from enferno.user.models import Role

        user = UserFactory()
        user.fs_uniquifier = uuid4().hex
        roles = Role.query.order_by(Role.id).limit(2).all()
        assert len(roles) == 2
        user.roles = list(reversed(roles))
        session.add(user)
        session.commit()

        snapshot = user.to_history_dict()
        assert [r["id"] for r in snapshot["roles"]] == sorted(r.id for r in roles)

    def test_delete_cascades_revisions(self, session, users):
        """A user carries revisions, so deletion must not be blocked by them."""
        admin_user, _, _, _ = users
        user = UserFactory()
        user.fs_uniquifier = uuid4().hex
        session.add(user)
        session.commit()
        user.create_revision(user_id=admin_user.id)
        user_id = user.id
        assert UserHistory.query.filter_by(target_user_id=user_id).count() == 1

        assert user.delete() is True
        assert UserHistory.query.filter_by(target_user_id=user_id).count() == 0
