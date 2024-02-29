import pytest

from enferno.admin.models import ActorHistory, BulletinHistory, IncidentHistory, LocationHistory
from tests.factories import (
    ActorFactory,
    ActorHistoryFactory,
    BulletinFactory,
    BulletinHistoryFactory,
    IncidentFactory,
    IncidentHistoryFactory,
    LocationFactory,
    LocationHistoryFactory,
)
from tests.models.admin import HistoryHelpersResponseModel
from tests.admin.test_actors import clean_slate_actors
from tests.admin.test_bulletins import clean_slate_bulletins
from tests.admin.test_incidents import clean_slate_incidents
from tests.admin.test_locations import clean_slate_locations
from tests.test_utils import (
    conform_to_schema_or_fail,
    convert_empty_strings_to_none,
)

#### PYDANTIC MODELS #####

from tests.models.admin import GeoLocationTypesResponseModel

##### FIXTURES #####


@pytest.fixture(scope="function")
def create_actor_history(session):
    actor = ActorFactory()
    session.add(actor)
    session.commit()
    history = ActorHistoryFactory()
    history.actor_id = actor.id
    history.actor = actor
    session.add(history)
    session.commit()
    yield history
    session.query(ActorHistory).filter(ActorHistory.id == history.id).delete(
        synchronize_session=False
    )
    session.query(ActorHistory).filter(ActorHistory.actor_id == actor.id).delete(
        synchronize_session=False
    )
    session.delete(actor)
    session.commit()


@pytest.fixture(scope="function")
def clean_slate_actor_histories(session):
    session.query(ActorHistory).delete(synchronize_session=False)
    session.commit()
    yield


@pytest.fixture(scope="function")
def create_bulletin_history(session):
    bulletin = BulletinFactory()
    session.add(bulletin)
    session.commit()
    history = BulletinHistoryFactory()
    history.bulletin_id = bulletin.id
    history.bulletin = bulletin
    session.add(history)
    session.commit()
    yield history
    session.query(BulletinHistory).filter(BulletinHistory.id == history.id).delete(
        synchronize_session=False
    )
    session.query(BulletinHistory).filter(BulletinHistory.bulletin_id == bulletin.id).delete(
        synchronize_session=False
    )
    session.delete(bulletin)
    session.commit()


@pytest.fixture(scope="function")
def clean_slate_bulletin_histories(session):
    session.query(BulletinHistory).delete(synchronize_session=False)
    session.commit()
    yield


@pytest.fixture(scope="function")
def create_incident_history(session):
    incident = IncidentFactory()
    session.add(incident)
    session.commit()
    history = IncidentHistoryFactory()
    history.incident_id = incident.id
    history.incident = incident
    session.add(history)
    session.commit()
    yield history
    session.query(IncidentHistory).filter(IncidentHistory.id == history.id).delete(
        synchronize_session=False
    )
    session.query(IncidentHistory).filter(IncidentHistory.incident_id == incident.id).delete(
        synchronize_session=False
    )
    session.delete(incident)
    session.commit()


@pytest.fixture(scope="function")
def clean_slate_incident_histories(session):
    session.query(IncidentHistory).delete(synchronize_session=False)
    session.commit()
    yield


@pytest.fixture(scope="function")
def create_location_history(session):
    location = LocationFactory()
    session.add(location)
    session.commit()
    history = LocationHistoryFactory()
    history.location_id = location.id
    history.location = location
    session.add(history)
    session.commit()
    yield history
    session.query(LocationHistory).filter(LocationHistory.id == history.id).delete(
        synchronize_session=False
    )
    session.query(LocationHistory).filter(LocationHistory.location_id == location.id).delete(
        synchronize_session=False
    )
    session.delete(location)
    session.commit()


@pytest.fixture(scope="function")
def clean_slate_location_histories(session):
    session.query(LocationHistory).delete(synchronize_session=False)
    session.commit()
    yield


##### GET /admin/api/actorhistory/<int:actorid> #####

get_actor_history_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", get_actor_history_endpoint_roles)
def test_get_actor_history_endpoint(
    clean_slate_actors,
    clean_slate_actor_histories,
    create_actor_history,
    request,
    client_fixture,
    expected_status,
):
    client_ = request.getfixturevalue(client_fixture)
    actor_hist_id = create_actor_history.id
    response = client_.get(
        f"/admin/api/actorhistory/{actor_hist_id}",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), HistoryHelpersResponseModel
        )


##### GET /admin/api/bulletinhistory/<int:bulletinid> #####

get_bulletin_history_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", get_bulletin_history_endpoint_roles)
def test_get_bulletin_history_endpoint(
    clean_slate_bulletins,
    clean_slate_bulletin_histories,
    create_bulletin_history,
    request,
    client_fixture,
    expected_status,
):
    client_ = request.getfixturevalue(client_fixture)
    bulletin_hist_id = create_bulletin_history.id
    response = client_.get(
        f"/admin/api/bulletinhistory/{bulletin_hist_id}",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), HistoryHelpersResponseModel
        )


##### GET /admin/api/incidenthistory/<int:incidentid> #####

get_incident_history_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", get_incident_history_endpoint_roles)
def test_get_incident_history_endpoint(
    clean_slate_incidents,
    clean_slate_incident_histories,
    create_incident_history,
    request,
    client_fixture,
    expected_status,
):
    client_ = request.getfixturevalue(client_fixture)
    incident_hist_id = create_incident_history.id
    response = client_.get(
        f"/admin/api/incidenthistory/{incident_hist_id}",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), HistoryHelpersResponseModel
        )


##### GET /admin/api/locationhistory/<int:locationid> #####

get_location_history_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", get_location_history_endpoint_roles)
def test_get_location_history_endpoint(
    clean_slate_locations,
    clean_slate_location_histories,
    create_location_history,
    request,
    client_fixture,
    expected_status,
):
    client_ = request.getfixturevalue(client_fixture)
    location_hist_id = create_location_history.id
    response = client_.get(
        f"/admin/api/locationhistory/{location_hist_id}",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), HistoryHelpersResponseModel
        )
