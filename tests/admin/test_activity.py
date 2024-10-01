import pytest

from enferno.admin.models import Activity
from enferno.user.models import User
from tests.admin.test_users import create_user
from tests.factories import ActivityFactory
from tests.test_utils import (
    conform_to_schema_or_fail,
    convert_empty_strings_to_none,
    get_first_or_fail,
)

##### PYDANTIC MODELS #####

from tests.models.admin import ActivitiesResponseModel

##### FIXTURES #####


@pytest.fixture(scope="function")
def create_activity(session, create_user):
    activity = ActivityFactory()
    u = get_first_or_fail(User)
    activity.user_id = u.id
    session.add(activity)
    session.commit()
    yield activity
    session.delete(activity)
    session.commit()


@pytest.fixture(scope="function")
def clean_slate_activities(session):
    session.query(Activity).delete(synchronize_session=False)
    session.query(User).delete(synchronize_session=False)
    session.commit()
    yield


##### GET /admin/api/activity #####

activity_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", activity_endpoint_roles)
def test_activity_endpoint(
    clean_slate_activities, create_activity, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get(
        "/admin/api/activities/",
        headers={"Content-Type": "application/json"},
        json={"q": {}, "options": {}},
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), ActivitiesResponseModel
        )
