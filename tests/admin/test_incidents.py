import pytest
from enferno.admin.models import Incident, Itoi
from enferno.user.models import User
from tests.factories import (
    IncidentFactory,
    create_event_for,
    create_label_for,
    create_ver_label_for,
    create_source,
    create_eventtype_for,
    create_profile_for,
    create_location,
)
from tests.admin.data.generators import (
    create_full_incident,
    create_related_incident,
    create_simple_incident,
)

from tests.test_utils import (
    conform_to_schema_or_fail,
    convert_empty_strings_to_none,
    get_first_or_fail,
    load_data,
    get_uid_from_client,
)

##### PYDANTIC MODELS #####

from tests.models.admin import (
    IncidentsResponseModel,
    IncidentItemMode3PlusModel,
    IncidentItemMode3Model,
    IncidentItemMode2Model,
    IncidentItemMinModel,
)

##### FIXTURES #####


@pytest.fixture(scope="function")
def clean_slate_incidents(session):
    from enferno.admin.models import IncidentHistory

    session.query(IncidentHistory).delete(synchronize_session=False)
    session.query(Itoi).delete(synchronize_session=False)
    session.query(Incident).delete(synchronize_session=False)
    session.commit()
    yield


##### GET /admin/api/incidents #####

incidents_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", incidents_endpoint_roles)
def test_incidents_endpoint(
    clean_slate_incidents, create_full_incident, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get(
        "/admin/api/incidents",
        json={"q": {}},
        headers={"content-type": "application/json"},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        data = convert_empty_strings_to_none(load_data(response))
        conform_to_schema_or_fail(data, IncidentsResponseModel)


##### GET /admin/api/incident/<int:id> #####

incident_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("client", 302),
]


@pytest.mark.parametrize("client_fixture, expected_status", incident_endpoint_roles)
def test_incident_endpoint(
    clean_slate_incidents, create_full_incident, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    incident = get_first_or_fail(Incident)
    response = client_.get(f"/admin/api/incident/{incident.id}")
    assert response.status_code == expected_status
    if expected_status == 200:
        data = convert_empty_strings_to_none(load_data(response))
        conform_to_schema_or_fail(data, IncidentItemMode3PlusModel)
        assert "bulletin_relations" in dict.keys(data)
        # Mode 1
        response = client_.get(f"/admin/api/incident/{incident.id}?mode=1")
        data = convert_empty_strings_to_none(load_data(response))
        conform_to_schema_or_fail(data, IncidentItemMinModel)
        # Mode 2
        response = client_.get(f"/admin/api/incident/{incident.id}?mode=2")
        data = convert_empty_strings_to_none(load_data(response))
        conform_to_schema_or_fail(data, IncidentItemMode2Model)
        # Mode 3
        response = client_.get(f"/admin/api/incident/{incident.id}?mode=3")
        data = convert_empty_strings_to_none(load_data(response))
        conform_to_schema_or_fail(data, IncidentItemMode3Model)
    elif expected_status == 302:
        assert "login" in response.headers["Location"]


##### POST /admin/api/incident #####

post_incident_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 403),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_incident_endpoint_roles)
def test_post_incident_endpoint(clean_slate_incidents, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    incident = IncidentFactory()
    response = client_.post(
        "/admin/api/incident",
        headers={"content-type": "application/json"},
        json={"item": incident.to_dict()},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    found_incident = Incident.query.filter(Incident.title == incident.title).first()
    if expected_status == 200:
        assert found_incident
    else:
        assert found_incident is None


##### PUT /admin/api/incident/<int:id> #####

put_incident_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_incident_endpoint_roles)
def test_put_incident_endpoint(
    clean_slate_incidents, create_full_incident, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    incident = get_first_or_fail(Incident)
    incident_id = incident.id
    new_title = IncidentFactory().title
    incident_dict = incident.to_dict()
    incident_dict["title"] = new_title
    response = client_.put(
        f"/admin/api/incident/{incident_id}",
        headers={"content-type": "application/json"},
        json={"item": incident_dict},
    )
    assert response.status_code == expected_status
    found_incident = Incident.query.filter(Incident.id == incident_id).first()
    if expected_status == 200:
        assert found_incident.title == new_title
    else:
        assert found_incident.title != new_title


put_incident_endpoint_roles2 = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 403),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_incident_endpoint_roles2)
def test_put_incident_assigned_endpoint(
    users, clean_slate_incidents, create_full_incident, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    incident = get_first_or_fail(Incident)
    uid = get_uid_from_client(users, client_fixture)
    incident.assigned_to = User.query.filter(User.id == uid).first()
    incident.save()
    incident_id = incident.id
    new_title = IncidentFactory().title
    incident_dict = incident.to_dict()
    incident_dict["title"] = new_title
    response = client_.put(
        f"/admin/api/incident/{incident_id}",
        headers={"content-type": "application/json"},
        json={"item": incident_dict},
    )
    assert response.status_code == expected_status
    found_incident = Incident.query.filter(Incident.id == incident_id).first()
    if expected_status == 200:
        assert found_incident.title == new_title
    else:
        assert found_incident.title != new_title


##### PUT /admin/api/incident/assign/<int:id> #####

put_incident_assign_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("client", 401),
    ("admin_sa_client", 200),
    ("da_sa_client", 200),
    ("mod_sa_client", 403),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_incident_assign_endpoint_roles)
def test_put_incident_assign_endpoint(
    clean_slate_incidents, create_simple_incident, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    incident = get_first_or_fail(Incident)
    incident_id = incident.id
    response = client_.put(
        f"/admin/api/incident/assign/{incident_id}",
        headers={"content-type": "application/json"},
        json={"incident": {"comments": "must exist"}},
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        found_incident = Incident.query.filter(Incident.id == incident_id).first()
        assert found_incident.assigned_to is not None


##### PUT /admin/api/incident/review/<int:id> #####

put_incident_review_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 403),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_incident_review_endpoint_roles)
def test_put_incident_review_endpoint(
    clean_slate_incidents, create_full_incident, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    i = IncidentFactory()
    incident = get_first_or_fail(Incident)
    incident_id = incident.id
    assert incident.review != i.review
    response = client_.put(
        f"/admin/api/incident/review/{incident_id}",
        headers={"content-type": "application/json"},
        json={"item": i.to_dict()},
    )
    assert response.status_code == expected_status
    found_incident = Incident.query.filter(Incident.id == incident_id).first()
    if expected_status == 200:
        assert found_incident.review == i.review
    else:
        assert found_incident.review != i.review


##### PUT /admin/api/incident/bulk #####

put_incident_bulk_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 200),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_incident_bulk_endpoint_roles)
def test_put_incident_bulk_endpoint(
    clean_slate_incidents, create_full_incident, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    incident = get_first_or_fail(Incident)
    ids = [incident.id]
    bulk = {"status": "bulk updated"}
    response = client_.put(
        f"/admin/api/incident/bulk",
        headers={"content-type": "application/json"},
        json={"items": ids, "bulk": bulk},
        follow_redirects=True,
    )
    assert response.status_code == expected_status


##### GET /admin/api/incident/relations/<int:id> #####

get_incident_relations_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", get_incident_relations_endpoint_roles)
def test_get_incident_relations_endpoint(
    clean_slate_incidents, create_related_incident, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    i1, i2, i3 = create_related_incident
    incident_id = i1.id
    response = client_.get(
        f"/admin/api/incident/relations/{incident_id}?class=incident",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        assert all([x["incident"]["id"] in [i2.id, i3.id] for x in load_data(response)["items"]])
