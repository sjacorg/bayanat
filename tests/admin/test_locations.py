import pytest

from enferno.admin.models import Location
from tests.factories import LocationFactory
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
def create_location(session):
    from enferno.admin.models import LocationHistory

    location = LocationFactory()
    session.add(location)
    session.commit()
    yield location
    session.query(LocationHistory).filter(LocationHistory.location_id == location.id).delete(
        synchronize_session=False
    )
    session.delete(location)
    session.commit()


@pytest.fixture(scope="function")
def clean_slate_locations(session):
    from enferno.admin.models import LocationHistory

    session.query(LocationHistory).delete(synchronize_session=False)
    session.query(Location).delete(synchronize_session=False)
    session.commit()
    yield


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
def test_post_location_endpoint(clean_slate_locations, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    location = LocationFactory()
    response = client_.post(
        "/admin/api/location",
        headers={"content-type": "application/json"},
        json={"item": {"title": location.title}},
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
def test_put_location_endpoint(create_location, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    location = get_first_or_fail(Location)
    location_id = location.id
    new_title = LocationFactory().title
    response = client_.put(
        f"/admin/api/location/{location_id}",
        headers={"content-type": "application/json"},
        json={"item": {"title": new_title}},
    )
    assert response.status_code == expected_status
    found_location = Location.query.filter(Location.id == location_id).first()
    if expected_status == 200:
        assert found_location.title == new_title
    else:
        assert found_location.title != new_title
