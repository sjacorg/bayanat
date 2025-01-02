import pytest

from enferno.admin.models import LocationType
from enferno.admin.validation.util import convert_empty_strings_to_none
from tests.factories import LocationTypeFactory
from tests.test_utils import (
    conform_to_schema_or_fail,
    get_first_or_fail,
)

#### PYDANTIC MODELS #####

from tests.models.admin import LocationTypesResponseModel

##### FIXTURES #####


@pytest.fixture(scope="function")
def create_location_type(session):
    lt = LocationTypeFactory()
    session.add(lt)
    session.commit()
    yield lt
    try:
        session.query(LocationType).filter(LocationType.id == lt.id).delete(
            synchronize_session=False
        )
        session.commit()
    except:
        pass


@pytest.fixture(scope="function")
def clean_slate_location_types(session):
    session.query(LocationType).delete(synchronize_session=False)
    session.commit()
    yield


##### GET /admin/api/location-types #####

lts_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", lts_endpoint_roles)
def test_location_types_endpoint(
    clean_slate_location_types, create_location_type, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get(
        "/admin/api/location-types",
        headers={"Content-Type": "application/json"},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), LocationTypesResponseModel
        )


##### POST /admin/api/location-type #####

post_lt_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_lt_endpoint_roles)
def test_post_location_type_endpoint(
    clean_slate_location_types, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    lt = LocationTypeFactory()
    response = client_.post(
        "/admin/api/location-type",
        headers={"Content-Type": "application/json"},
        json={"item": lt.to_dict()},
    )
    assert response.status_code == expected_status
    found_lt = LocationType.query.filter(LocationType.title == lt.title).first()
    if expected_status == 200:
        assert found_lt
    else:
        assert found_lt is None


##### PUT /admin/api/location-type/<int:id> #####

put_lt_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_lt_endpoint_roles)
def test_put_location_type_endpoint(
    clean_slate_location_types, create_location_type, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    lt = get_first_or_fail(LocationType)
    loc_id = lt.id
    new_lt = LocationTypeFactory()
    response = client_.put(
        f"/admin/api/location-type/{loc_id}",
        headers={"Content-Type": "application/json"},
        json={"item": new_lt.to_dict()},
    )
    assert response.status_code == expected_status
    found_lt = LocationType.query.filter(LocationType.id == loc_id).first()
    if expected_status == 200:
        assert found_lt.title == new_lt.title
    else:
        assert found_lt.title != new_lt.title


##### DELETE /admin/api/location-type/<int:id> #####

delete_lt_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", delete_lt_endpoint_roles)
def test_delete_location_type_endpoint(
    clean_slate_location_types, create_location_type, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    lt = get_first_or_fail(LocationType)
    loc_id = lt.id
    response = client_.delete(
        f"/admin/api/location-type/{loc_id}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == expected_status
    found_lt = LocationType.query.filter(LocationType.id == loc_id).first()
    if expected_status == 200:
        assert found_lt is None
    else:
        assert found_lt
