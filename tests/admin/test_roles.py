import pytest

from enferno.utils.validation_utils import convert_empty_strings_to_none
from enferno.user.models import Role
from tests.factories import RoleFactory

from tests.models.admin import RoleCreatedResponseModel, RolesResponseModel
from tests.test_utils import conform_to_schema_or_fail, create_csv_for_entities
from sqlalchemy import not_


##### FIXTURES #####


@pytest.fixture(scope="function")
def create_role(session):
    role = RoleFactory()
    session.add(role)
    session.commit()
    yield role
    try:
        session.delete(role)
        session.commit()
    except:
        pass


@pytest.fixture(scope="function")
def clean_slate_roles(session):
    Role.query.filter(not_(Role.name.in_(["Admin", "DA", "Mod"]))).delete(synchronize_session=False)


@pytest.fixture(scope="function")
def create_role_csv():
    r1 = RoleFactory()
    r2 = RoleFactory()
    r1.name = "Imported Role 1"
    r2.name = "Imported Role 2"
    headers = ["name", "color", "description"]
    yield from create_csv_for_entities([r1, r2], headers)


##### GET /admin/api/roles #####

roles_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", roles_endpoint_roles)
def test_roles_endpoint(request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get("/admin/api/roles/", headers={"Content-Type": "application/json"})
    assert response.status_code == expected_status
    if expected_status == 200:
        assert len(response.json["data"]["items"]) == len(Role.query.all())


##### POST /admin/api/role/ #####

post_role_endpoint_roles = [
    ("admin_client", 201),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_role_endpoint_roles)
def test_post_role_endpoint(request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    r = RoleFactory()
    response = client_.post(
        "/admin/api/role/", headers={"Content-Type": "application/json"}, json={"item": r.to_dict()}
    )
    assert response.status_code == expected_status
    found_role = Role.query.filter(Role.name == r.name).first()
    if expected_status == 201:
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), RoleCreatedResponseModel
        )
        assert found_role
        # Clean up
        Role.query.filter(Role.id == found_role.id).delete()
    else:
        assert found_role is None


##### PUT /admin/api/role/<int:id> #####

put_role_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_role_endpoint_roles)
def test_put_role_endpoint(create_role, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    r = RoleFactory()
    role_id = create_role.id
    response = client_.put(
        f"/admin/api/role/{role_id}",
        headers={"Content-Type": "application/json"},
        json={"item": r.to_dict()},
    )
    assert response.status_code == expected_status
    found_role = Role.query.filter(Role.id == role_id).first()
    if expected_status == 200:
        assert found_role.name == r.name
    else:
        assert found_role.name != r.name


##### DELETE /admin/api/role/<int:id> #####

delete_role_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", delete_role_endpoint_roles)
def test_delete_role_endpoint(create_role, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    role_id = create_role.id
    response = client_.delete(
        f"/admin/api/role/{role_id}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == expected_status
    found_role = Role.query.filter(Role.id == role_id).first()
    if expected_status == 200:
        assert found_role is None
    else:
        assert found_role
