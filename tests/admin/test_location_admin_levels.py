import pytest
from unittest.mock import patch
from enferno.admin.models import Location, LocationAdminLevel
from enferno.admin.validation.util import convert_empty_strings_to_none
from tests.factories import LocationAdminLevelFactory, LocationFactory
from tests.test_utils import (
    conform_to_schema_or_fail,
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
    lal.code = 1
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
    new_lal.code = lal.code
    response = client_.put(
        f"/admin/api/location-admin-level/{lal_id}",
        headers={"Content-Type": "application/json"},
        json={"item": new_lal.to_dict()},
    )
    print(response.text)
    assert response.status_code == expected_status
    found_lal = LocationAdminLevel.query.filter(LocationAdminLevel.id == lal_id).first()
    if expected_status == 200:
        assert found_lal.title == new_lal.title
    else:
        assert found_lal.title != new_lal.title


##### DELETE /admin/api/location-admin-level/<int:id> #####

delete_lal_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", delete_lal_endpoint_roles)
def test_delete_lal_endpoint(
    clean_slate_lals, session, create_lal, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    # add at least 3 levels
    lal1 = LocationAdminLevelFactory()
    lal2 = LocationAdminLevelFactory()
    lal3 = LocationAdminLevelFactory()
    session.add(lal1)
    session.add(lal2)
    session.add(lal3)
    session.commit()
    lal = LocationAdminLevel.query.order_by(LocationAdminLevel.code.desc()).first()
    lal_id = lal.id
    response = client_.delete(
        f"/admin/api/location-admin-level/{lal_id}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == expected_status
    found_lal = LocationAdminLevel.query.filter(LocationAdminLevel.id == lal_id).first()
    if expected_status == 200:
        assert found_lal is None
    else:
        assert found_lal is not None


##### POST /admin/api/location-admin-levels/reorder #####

reorder_lal_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", reorder_lal_endpoint_roles)
def test_reorder_lals_endpoint(clean_slate_lals, session, request, client_fixture, expected_status):
    # Create 3 lals
    lal1 = LocationAdminLevelFactory()
    lal2 = LocationAdminLevelFactory()
    lal3 = LocationAdminLevelFactory()
    lal1.code = 1
    lal2.code = 2
    lal3.code = 3
    lal1.display_order = 1
    lal2.display_order = 2
    lal3.display_order = 3
    session.add_all([lal1, lal2, lal3])
    session.commit()

    client_ = request.getfixturevalue(client_fixture)
    response = client_.post(
        "/admin/api/location-admin-levels/reorder",
        headers={"Content-Type": "application/json"},
        json={"order": [lal3.id, lal2.id, lal1.id]},
    )
    assert response.status_code == expected_status
    found_lal1 = LocationAdminLevel.query.filter(LocationAdminLevel.id == lal1.id).first()
    found_lal2 = LocationAdminLevel.query.filter(LocationAdminLevel.id == lal2.id).first()
    found_lal3 = LocationAdminLevel.query.filter(LocationAdminLevel.id == lal3.id).first()
    if expected_status == 200:
        assert found_lal1.display_order == 3
        assert found_lal2.display_order == 2
        assert found_lal3.display_order == 1
    else:
        assert found_lal1.display_order == 1
        assert found_lal2.display_order == 2
        assert found_lal3.display_order == 3


##### Unit test for `get_full_string` method and static `regenerate_all_full_locations` method in Location model #####


def test_get_full_string_method_and_regenerate_all_full_locations(clean_slate_lals, session):
    # Create a hierarchy of LocationAdminLevels
    lal1 = LocationAdminLevelFactory()
    lal2 = LocationAdminLevelFactory()
    lal3 = LocationAdminLevelFactory()
    lal4 = LocationAdminLevelFactory()
    lal1.code = 1
    lal2.code = 2
    lal3.code = 3
    lal4.code = 4

    # Mix the display order
    lal1.display_order = 2
    lal2.display_order = 1
    lal3.display_order = 4
    lal4.display_order = 3

    session.add_all([lal1, lal2, lal3, lal4])
    session.commit()

    location1 = LocationFactory()
    location2 = LocationFactory()
    location3 = LocationFactory()
    location4 = LocationFactory()
    location1.admin_level_id = lal1.id
    location2.admin_level_id = lal2.id
    location3.admin_level_id = lal3.id
    location4.admin_level_id = lal4.id
    location1.postal_code = "12345"
    location2.postal_code = "67890"
    location3.postal_code = "13579"
    location4.postal_code = "24680"
    session.add_all([location1, location2, location3, location4])
    session.commit()
    location4.parent_id = location3.id
    location3.parent_id = location2.id
    location2.parent_id = location1.id
    session.commit()

    titles = [location.title for location in [location2, location1, location4, location3]]

    # Test with postal code disabled
    with patch("flask.current_app.config.get") as mock_config:
        mock_config.return_value = False

        # Leaf node
        assert location4.get_full_string() == ", ".join(titles)

        # Intermediate node
        assert location3.get_full_string() == ", ".join([titles[0], titles[1], titles[3]])

        # Root node
        assert location1.get_full_string() == titles[1]

    # Test with postal code enabled
    with patch("flask.current_app.config.get") as mock_config:
        mock_config.return_value = True

        # Leaf node
        assert location4.get_full_string() == ", ".join(titles) + " " + location4.postal_code

        # Intermediate node
        assert (
            location3.get_full_string()
            == ", ".join([titles[0], titles[1], titles[3]]) + " " + location3.postal_code
        )

        # Root node
        assert location1.get_full_string() == titles[1] + " " + location1.postal_code

    # Assert the CTE for all locations is correct
    with patch("flask.current_app.config.get") as mock_config:
        mock_config.return_value = True
        Location.regenerate_all_full_locations()

        # Repeat assertions with postal code enabled
        assert location4.get_full_string() == ", ".join(titles) + " " + location4.postal_code
        assert (
            location3.get_full_string()
            == ", ".join([titles[0], titles[1], titles[3]]) + " " + location3.postal_code
        )
        assert location1.get_full_string() == titles[1] + " " + location1.postal_code
