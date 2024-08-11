import re
from unittest.mock import patch
import uuid
import pytest
from flask import current_app
from enferno.admin.models import Activity
from enferno.user.models import User, Session, WebAuthn

from tests.factories import UserFactory, create_webauthn_for
from tests.test_utils import (
    conform_to_schema_or_fail,
    convert_empty_strings_to_none,
    get_uid_from_client,
)

#### PYDANTIC MODELS #####

from tests.models.admin import UserSessionsResponseModel, UsersResponseModel

##### FIXTURES #####


@pytest.fixture(scope="function")
def clean_slate_users(session):
    session.query(Activity).delete(synchronize_session=False)
    session.query(User).delete(synchronize_session=False)
    session.commit()
    yield


@pytest.fixture(scope="function")
def create_user(session):
    user = UserFactory()
    session.add(user)
    session.commit()
    yield user
    try:
        session.query(Activity).filter(Activity.user_id == user.id).delete(
            synchronize_session=False
        )
        session.delete(user)
        session.commit()
    except:
        pass


@pytest.fixture(scope="function")
def create_inactive_user(session):
    user = UserFactory()
    user.active = False
    session.add(user)
    session.commit()
    yield user


@pytest.fixture(scope="function")
def create_session_for(request, session):
    def _clean_up(sess):
        try:
            session.delete(sess)
            session.commit()
        except:
            pass

    def _create_session_for(user):
        sess = Session()
        sess.user_id = user.id
        sess.ip_address = "127.0.0.1"
        sess.session_token = uuid.uuid4().hex
        session.add(sess)
        session.commit()
        request.addfinalizer(lambda: _clean_up(sess))
        return sess

    return _create_session_for


##### MOCKS #####
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


##### UTILITIES #####


def user_to_dict(user):
    return {
        "name": user.name,
        "username": user.username,
        "active": user.active,
        "password": user.password,
        "email": user.email,
    }


##### GET /admin/api/users #####

get_users_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 200),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", get_users_endpoint_roles)
def test_get_users_endpoint(request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get("/admin/api/users/", headers={"Content-Type": "application/json"})
    assert response.status_code == expected_status
    if expected_status == 200:
        conform_to_schema_or_fail(convert_empty_strings_to_none(response.json), UsersResponseModel)


##### POST /admin/api/user #####

post_user_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_user_endpoint_roles)
def test_post_user_endpoint(clean_slate_users, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    user = UserFactory()
    response = client_.post(
        "/admin/api/user/",
        headers={"Content-Type": "application/json"},
        json={"item": user_to_dict(user)},
    )
    assert response.status_code == expected_status
    found_user = User.query.filter(User.username == user.username).first()
    if expected_status == 200:
        assert found_user
    else:
        assert found_user is None


##### POST /admin/api/checkuser #####

post_checkuser_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_checkuser_endpoint_roles)
def test_post_checkuser_endpoint(
    clean_slate_users, create_user, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    if expected_status == 200:
        # Check for an existing username
        u = create_user
        response = client_.post(
            "/admin/api/checkuser/",
            headers={"Content-Type": "application/json"},
            json={"item": u.username},
        )
        assert response.status_code == 417
        # Check for a fresh username
    u = UserFactory()
    response = client_.post(
        "/admin/api/checkuser/",
        headers={"Content-Type": "application/json"},
        json={"item": u.username},
    )
    assert response.status_code == expected_status


##### PUT /admin/api/user/<int:uid> #####

put_user_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_user_endpoint_roles)
def test_put_user_endpoint(
    clean_slate_users, create_user, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    user_id = create_user.id
    u = UserFactory()

    user_json = user_to_dict(u)
    user_json["id"] = user_id

    response = client_.put(
        f"/admin/api/user/",
        headers={"Content-Type": "application/json"},
        json={"item": user_json},
    )
    assert response.status_code == expected_status
    found_user = User.query.filter(User.id == user_id).first()
    if expected_status == 200:
        assert found_user.username == u.username
    else:
        assert found_user.username != u.username


##### POST /admin/api/password #####

post_password_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_password_endpoint_roles)
def test_post_password_endpoint(request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    WEAK_PASSWORD = "123456"
    STRONG_PASSWORD = "On3Tw0Thr33!"
    if expected_status == 200:
        response = client_.post(
            "/admin/api/password/",
            headers={"Content-Type": "application/json"},
            json={"password": WEAK_PASSWORD},
        )
        assert response.status_code == 409
    response = client_.post(
        "/admin/api/password/",
        headers={"Content-Type": "application/json"},
        json={"password": STRONG_PASSWORD},
    )
    assert response.status_code == expected_status


##### POST /admin/api/user/force-reset #####

post_force_reset_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_force_reset_endpoint_roles)
def test_post_force_reset_endpoint(
    clean_slate_users, create_user, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    id = create_user.id
    response = client_.post(
        "/admin/api/user/force-reset",
        headers={"Content-Type": "application/json"},
        json={"item": {"id": id}},
    )
    assert response.status_code == expected_status


##### POST /admin/api/user/force-reset-all #####

post_force_reset_all_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_force_reset_all_endpoint_roles)
def test_post_force_reset_all_endpoint(
    clean_slate_users, create_user, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    user_id = create_user.id
    response = client_.post(
        "/admin/api/user/force-reset-all",
        headers={"Content-Type": "application/json"},
        follow_redirects=True,
    )
    assert response.status_code == expected_status


##### DELETE /admin/api/user/<int:id> #####

delete_user_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", delete_user_endpoint_roles)
def test_delete_user_endpoint(
    clean_slate_users, create_inactive_user, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    u = create_inactive_user
    response = client_.delete(
        f"/admin/api/user/{u.id}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == expected_status
    found_user = User.query.filter(User.id == u.id).first()
    if expected_status == 200:
        assert found_user is None
    else:
        assert found_user


##### GET /admin/api/user/<int:id>/sessions #####

get_user_sessions_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("client", 401),
]


# Basic roles access test
@pytest.mark.parametrize("client_fixture, expected_status", get_user_sessions_endpoint_roles)
def test_user_sessions(
    clean_slate_users, create_user, create_session_for, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    u = create_user
    create_session_for(u)
    response = client_.get(
        f"/admin/api/user/{u.id}/sessions",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), UserSessionsResponseModel
        )


##### DELETE /admin/api/sessions/logout #####


@pytest.mark.parametrize("client_fixture, expected_status", get_user_sessions_endpoint_roles)
def test_sessions_logout(
    clean_slate_users, create_user, create_session_for, request, client_fixture, expected_status
):
    rds = MockRedis()
    client_ = request.getfixturevalue(client_fixture)
    u = create_user
    sess = create_session_for(u)
    control = create_session_for(u)
    rds.set(f"session:{sess.session_token}", "1")
    rds.set(f"session:{control.session_token}", "1")
    assert rds.exists(f"session:{sess.session_token}")
    assert rds.exists(f"session:{control.session_token}")
    with patch.dict(current_app.config, {"SESSION_REDIS": rds}):
        response = client_.delete(
            f"/admin/api/session/logout",
            headers={"Content-Type": "application/json"},
            json={"sessid": sess.id},
        )
        assert response.status_code == expected_status
        if expected_status == 200:
            assert not rds.exists(f"session:{sess.session_token}")
            assert rds.exists(f"session:{control.session_token}")


##### DELETE /admin/api/user/<int:id>/sessions/logout #####


@pytest.mark.parametrize("client_fixture, expected_status", get_user_sessions_endpoint_roles)
def test_user_sessions_logout(
    clean_slate_users, create_user, create_session_for, request, client_fixture, expected_status
):
    rds = MockRedis()
    client_ = request.getfixturevalue(client_fixture)
    u = create_user
    sess1 = create_session_for(u)
    sess2 = create_session_for(u)
    rds.set(f"session:{sess1.session_token}", "1")
    rds.set(f"session:{sess2.session_token}", "1")
    assert rds.exists(f"session:{sess1.session_token}")
    assert rds.exists(f"session:{sess2.session_token}")
    with patch.dict(current_app.config, {"SESSION_REDIS": rds}):
        response = client_.delete(
            f"/admin/api/user/{u.id}/sessions/logout",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == expected_status
        if expected_status == 200:
            assert not rds.exists(f"session:{sess1.session_token}")
            assert not rds.exists(f"session:{sess2.session_token}")


##### DELETE /admin/api/user/revoke_2fa #####


@pytest.mark.parametrize("client_fixture, expected_status", delete_user_endpoint_roles)
def test_delete_user_revoke_2fa_endpoint(
    session,
    clean_slate_users,
    create_user,
    create_webauthn_for,
    request,
    client_fixture,
    expected_status,
):
    client_ = request.getfixturevalue(client_fixture)
    u = create_user
    assert u.tf_totp_secret
    assert u.tf_phone_number
    assert u.tf_primary_method
    webauthn = create_webauthn_for(u)
    found_webauthn = session.query(WebAuthn).all()
    assert len(found_webauthn) == 1
    response = client_.delete(
        f"/admin/api/user/revoke_2fa?user_id={u.id}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == expected_status
    found_user = session.query(User).filter(User.id == u.id).first()
    assert found_user
    new_found_webauthn = session.query(WebAuthn).all()
    if expected_status == 200:
        assert found_user.tf_totp_secret is None
        assert found_user.tf_phone_number is None
        assert found_user.tf_primary_method is None
        assert len(new_found_webauthn) == 0
    else:
        assert found_user.tf_totp_secret == u.tf_totp_secret
        assert found_user.tf_phone_number == u.tf_phone_number
        assert found_user.tf_primary_method == u.tf_primary_method
        assert len(new_found_webauthn) == 1
