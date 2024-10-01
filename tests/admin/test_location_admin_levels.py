import pytest

from enferno.admin.models import LocationAdminLevel
from tests.factories import LocationAdminLevelFactory
from tests.test_utils import (
    conform_to_schema_or_fail,
    convert_empty_strings_to_none,
    get_first_or_fail,
)

#### PYDANTIC MODELS #####

from tests.models.admin import LocationAdminLevelsResponseModel

##### FIXTURES #####


@pytest.fixture(scope="function")
def create_lal(session):
    lal = LocationAdminLevelFactory()
    session.add(lal)
    session.commit()
    yield lal
    try:
        session.query(LocationAdminLevel).filter(LocationAdminLevel.id == lal.id).delete(
            synchronize_session=False
        )
        session.commit()
    except:
        pass


@pytest.fixture(scope="function")
def clean_slate_lals(session):
    session.query(LocationAdminLevel).delete(synchronize_session=False)
    session.commit()
    yield


##### GET /admin/api/location-admin-levels #####

lals_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", lals_endpoint_roles)
def test_lals_endpoint(clean_slate_lals, create_lal, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get(
        "/admin/api/location-admin-levels",
        headers={"Content-Type": "application/json"},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), LocationAdminLevelsResponseModel
        )


##### POST /admin/api/location-admin-level #####

post_lal_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_lal_endpoint_roles)
def test_post_lal_endpoint(clean_slate_lals, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    lal = LocationAdminLevelFactory()
    response = client_.post(
        "/admin/api/location-admin-level",
        headers={"Content-Type": "application/json"},
        json={"item": lal.to_dict()},
    )
    assert response.status_code == expected_status
    found_lal = LocationAdminLevel.query.filter(LocationAdminLevel.code == lal.code).first()
    if expected_status == 200:
        assert found_lal
    else:
        assert found_lal is None


##### PUT /admin/api/location-admin-level/<int:id> #####

put_lal_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_lal_endpoint_roles)
def test_put_lal_endpoint(clean_slate_lals, create_lal, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    lal = get_first_or_fail(LocationAdminLevel)
    new_lal = LocationAdminLevelFactory()
    lal_id = lal.id
    response = client_.put(
        f"/admin/api/location-admin-level/{lal_id}",
        headers={"Content-Type": "application/json"},
        json={"item": new_lal.to_dict()},
    )
    assert response.status_code == expected_status
    found_lal = LocationAdminLevel.query.filter(LocationAdminLevel.id == lal_id).first()
    if expected_status == 200:
        assert found_lal.code == new_lal.code
    else:
        assert found_lal.code != new_lal.code
