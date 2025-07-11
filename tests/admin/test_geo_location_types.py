import pytest

from enferno.admin.models import GeoLocationType
from enferno.admin.validation.util import convert_empty_strings_to_none
from tests.factories import GeoLocationTypeFactory
from tests.test_utils import (
    conform_to_schema_or_fail,
    get_first_or_fail,
)

#### PYDANTIC MODELS #####

from tests.models.admin import GeoLocationTypesResponseModel

##### FIXTURES #####


@pytest.fixture(scope="function")
def create_geo_location_type(session):
    typ = GeoLocationTypeFactory()
    session.add(typ)
    session.commit()
    yield typ
    try:
        session.query(GeoLocationType).filter(GeoLocationType.id == typ.id).delete(
            synchronize_session=False
        )
        session.commit()
    except:
        pass


@pytest.fixture(scope="function")
def clean_slate_geo_location_types(session):
    session.query(GeoLocationType).delete(synchronize_session=False)
    session.commit()
    yield


##### GET /admin/api/geolocationtypes #####

geolocationtypes_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", geolocationtypes_endpoint_roles)
def test_geolocationtypes_endpoint(
    clean_slate_geo_location_types,
    create_geo_location_type,
    request,
    client_fixture,
    expected_status,
):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get(
        "/admin/api/geolocationtypes",
        headers={"Content-Type": "application/json"},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        assert len(response.json["data"]["items"]) > 0
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), GeoLocationTypesResponseModel
        )


##### POST /admin/api/geolocationtype #####

post_geolocationtype_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_geolocationtype_endpoint_roles)
def test_post_geolocationtype_endpoint(
    clean_slate_geo_location_types, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    typ = GeoLocationTypeFactory()
    response = client_.post(
        "/admin/api/geolocationtype",
        headers={"Content-Type": "application/json"},
        json={"item": typ.to_dict()},
    )
    assert response.status_code == expected_status
    found_type = GeoLocationType.query.filter(GeoLocationType.title == typ.title).first()
    if expected_status == 200:
        assert found_type
    else:
        assert found_type is None


##### PUT /admin/api/geolocationtype/<int:id> #####

put_geolocationtype_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_geolocationtype_endpoint_roles)
def test_put_geolocationtype_endpoint(
    clean_slate_geo_location_types,
    create_geo_location_type,
    request,
    client_fixture,
    expected_status,
):
    client_ = request.getfixturevalue(client_fixture)
    typ = get_first_or_fail(GeoLocationType)
    geo_id = typ.id
    new_type = GeoLocationTypeFactory()
    new_type.id = geo_id
    response = client_.put(
        f"/admin/api/geolocationtype/{geo_id}",
        headers={"Content-Type": "application/json"},
        json={"item": new_type.to_dict()},
    )
    assert response.status_code == expected_status
    found_type = GeoLocationType.query.filter(GeoLocationType.id == geo_id).first()
    if expected_status == 200:
        assert found_type.title == new_type.title
    else:
        assert found_type.title != new_type.title


##### DELETE /admin/api/geolocationtype/<int:id> #####

delete_geolocationtype_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", delete_geolocationtype_endpoint_roles)
def test_delete_geolocationtype_endpoint(
    clean_slate_geo_location_types,
    create_geo_location_type,
    request,
    client_fixture,
    expected_status,
):
    client_ = request.getfixturevalue(client_fixture)
    typ = get_first_or_fail(GeoLocationType)
    geo_id = typ.id
    response = client_.delete(
        f"/admin/api/geolocationtype/{geo_id}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == expected_status
    found_type = GeoLocationType.query.filter(GeoLocationType.id == geo_id).first()
    if expected_status == 200:
        assert found_type is None
    else:
        assert found_type
