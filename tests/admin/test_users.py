import pytest
from enferno.admin.models import Activity

from enferno.user.models import User
from tests.factories import UserFactory
from tests.test_utils import (
    conform_to_schema_or_fail,
    convert_empty_strings_to_none,
)

#### PYDANTIC MODELS #####

from tests.models.admin import UsersResponseModel

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


##### UTILITIES #####


def user_to_dict(user):
    return {
        "name": user.name,
        "username": user.username,
        "active": user.active,
        "password": user.password,
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
    response = client_.put(
        f"/admin/api/user/{user_id}",
        headers={"Content-Type": "application/json"},
        json={"item": user_to_dict(u)},
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
