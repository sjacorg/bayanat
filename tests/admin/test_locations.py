from enum import Enum
import pytest


from enferno.admin.models import Location, LocationType

from tests.factories import LocationFactory, create_location, LocationTypeFactory

from tests.test_utils import (
    conform_to_schema_or_fail,
    convert_empty_strings_to_none,
    get_first_or_fail,
    load_data,
)

##### PYDANTIC MODELS #####

from tests.models.admin import LocationItemModel, LocationResponseModel

##### FIXTURES #####


@pytest.fixture(scope="function")
def clean_slate_locations(session):
    from enferno.admin.models import LocationHistory

    session.query(LocationHistory).delete(synchronize_session=False)
    session.query(Location).delete(synchronize_session=False)
    session.commit()
    yield


class LocationTypeEnum(Enum):
    ADMINISTRATIVE_LOCATION = "Administrative Location"
    POINT_OF_INTEREST = "Point of Interest"


@pytest.fixture(scope="function")
def create_location_type(request, session):
    def _create_location_type(location_type_enum):
        location_type = LocationTypeFactory()
        location_type.title = location_type_enum.value
        session.add(location_type)
        session.commit()
        request.addfinalizer(lambda: session.delete(location_type))
        return location_type

    return _create_location_type


##### GET /admin/api/locations #####

locations_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", locations_endpoint_roles)
def test_locations_endpoint(create_location, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get(
        "/admin/api/locations",
        json={"q": {}, "options": {}},
        headers={"Content-Type": "application/json"},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        data = convert_empty_strings_to_none(load_data(response))
        conform_to_schema_or_fail(data, LocationResponseModel)


##### GET /admin/api/location/<int:id> #####

location_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("client", 302),
]


@pytest.mark.parametrize("client_fixture, expected_status", location_endpoint_roles)
def test_location_endpoint(create_location, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    location = get_first_or_fail(Location)
    response = client_.get(f"/admin/api/location/{location.id}")
    assert response.status_code == expected_status
    if expected_status == 200:
        data = convert_empty_strings_to_none(load_data(response))
        conform_to_schema_or_fail(data, LocationItemModel)
    elif expected_status == 302:
        assert "login" in response.headers["Location"]


##### POST /admin/api/location #####

post_location_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 400),
    ("mod_client", 200),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_location_endpoint_roles)
def test_post_location_endpoint(
    create_location_type, clean_slate_locations, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    location = LocationFactory()
    location_type = create_location_type(LocationTypeEnum.POINT_OF_INTEREST)
    location.location_type = location_type
    item = location.to_dict()
    response = client_.post(
        "/admin/api/location",
        headers={"content-type": "application/json"},
        json={"item": item},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    found_location = Location.query.filter(Location.title == location.title).first()
    if expected_status == 200:
        assert found_location
    else:
        assert found_location is None


##### PUT /admin/api/location/<int:id> #####

put_location_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 400),
    ("mod_client", 200),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_location_endpoint_roles)
def test_put_location_endpoint(
    create_location_type, create_location, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    location = get_first_or_fail(Location)
    location_type = create_location_type(LocationTypeEnum.POINT_OF_INTEREST)
    location_id = location.id
    new_title = LocationFactory().title
    item = location.to_dict()
    item["location_type"] = location_type.to_dict()
    item["title"] = new_title
    response = client_.put(
        f"/admin/api/location/{location_id}",
        headers={"content-type": "application/json"},
        json={"item": item},
    )
    assert response.status_code == expected_status
    found_location = Location.query.filter(Location.id == location_id).first()
    if expected_status == 200:
        assert found_location.title == new_title
    else:
        assert found_location.title != new_title
