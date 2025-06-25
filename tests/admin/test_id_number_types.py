import pytest

from enferno.admin.models.Actor import Actor
from enferno.admin.models.IDNumberType import IDNumberType
from enferno.admin.validation.util import convert_empty_strings_to_none
from tests.factories import IDNumberTypeFactory
from tests.test_utils import (
    conform_to_schema_or_fail,
    get_first_or_fail,
)
from tests.factories import create_simple_actor

#### PYDANTIC MODELS #####

from tests.models.admin import EthnographiesResponseModel  # Reusing the same response model

##### FIXTURES #####


@pytest.fixture(scope="function")
def create_id_number_type(session):
    id_number_type = IDNumberTypeFactory()
    session.add(id_number_type)
    session.commit()
    yield id_number_type
    try:
        session.query(IDNumberType).filter(IDNumberType.id == id_number_type.id).delete(
            synchronize_session=False
        )
        session.commit()
    except:
        pass


@pytest.fixture(scope="function")
def clean_slate_id_number_types(session):
    session.query(IDNumberType).delete(synchronize_session=False)
    session.commit()
    yield


##### GET /admin/api/idnumbertypes #####

id_number_types_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", id_number_types_endpoint_roles)
def test_id_number_types_endpoint(
    clean_slate_id_number_types, create_id_number_type, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get(
        "/admin/api/idnumbertypes",
        headers={"Content-Type": "application/json"},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), EthnographiesResponseModel
        )


##### POST /admin/api/idnumbertype #####

post_id_number_type_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_id_number_type_roles)
def test_post_id_number_type(clean_slate_id_number_types, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    id_number_type = IDNumberTypeFactory()
    response = client_.post(
        "/admin/api/idnumbertype",
        headers={"Content-Type": "application/json"},
        json={"item": id_number_type.to_dict()},
    )
    assert response.status_code == expected_status
    found_id_number_type = IDNumberType.query.filter(
        IDNumberType.title == id_number_type.title
    ).first()
    if expected_status == 200:
        assert found_id_number_type
    else:
        assert found_id_number_type is None


##### PUT /admin/api/idnumbertype/<int:id> #####

put_id_number_type_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_id_number_type_roles)
def test_put_id_number_type(
    clean_slate_id_number_types, create_id_number_type, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    id_number_type = get_first_or_fail(IDNumberType)
    id_number_type_id = id_number_type.id
    new_id_number_type = IDNumberTypeFactory()
    new_id_number_type.id = id_number_type_id
    response = client_.put(
        f"/admin/api/idnumbertype/{id_number_type_id}",
        headers={"Content-Type": "application/json"},
        json={"item": new_id_number_type.to_dict()},
    )
    assert response.status_code == expected_status
    found_id_number_type = IDNumberType.query.filter(IDNumberType.id == id_number_type_id).first()
    if expected_status == 200:
        assert found_id_number_type.title == new_id_number_type.title
    else:
        assert found_id_number_type.title != new_id_number_type.title


##### DELETE /admin/api/idnumbertype/<int:id> #####

delete_id_number_type_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", delete_id_number_type_roles)
def test_delete_id_number_type(
    clean_slate_id_number_types, create_id_number_type, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    id_number_type = get_first_or_fail(IDNumberType)
    id_number_type_id = id_number_type.id
    response = client_.delete(
        f"/admin/api/idnumbertype/{id_number_type_id}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == expected_status
    found_id_number_type = IDNumberType.query.filter(IDNumberType.id == id_number_type_id).first()
    if expected_status == 200:
        assert found_id_number_type is None
    else:
        assert found_id_number_type


delete_id_number_type_still_referenced_roles = [
    ("admin_client", 409),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize(
    "client_fixture, expected_status", delete_id_number_type_still_referenced_roles
)
def test_delete_id_number_type_still_referenced(
    clean_slate_id_number_types,
    create_id_number_type,
    request,
    client_fixture,
    expected_status,
    create_simple_actor,
):
    actor = get_first_or_fail(Actor)
    actor.id_number = [{"type": str(create_id_number_type.id), "number": "1234567890"}]
    actor.save()
    client_ = request.getfixturevalue(client_fixture)
    response = client_.delete(
        f"/admin/api/id-number-type/{create_id_number_type.id}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == expected_status
    if expected_status == 409:
        assert "is referenced by" in response.text.lower()
