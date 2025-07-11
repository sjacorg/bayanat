import pytest

from enferno.admin.models import Eventtype
from enferno.admin.validation.util import convert_empty_strings_to_none
from tests.factories import EventtypeFactory
from tests.models.admin import EventtypesResponseModel
from tests.test_utils import (
    conform_to_schema_or_fail,
    get_first_or_fail,
    create_csv_for_entities,
)


#### PYDANTIC MODELS #####

##### FIXTURES #####


@pytest.fixture(scope="function")
def create_eventtype(session):
    evt = EventtypeFactory()
    session.add(evt)
    session.commit()
    yield evt
    try:
        session.query(Eventtype).filter(Eventtype.id == evt.id).delete(synchronize_session=False)
        session.commit()
    except:
        pass


@pytest.fixture(scope="function")
def clean_slate_eventtypes(session):
    session.query(Eventtype).delete(synchronize_session=False)
    session.commit()
    yield


@pytest.fixture(scope="function")
def create_eventtype_csv():
    evt1 = EventtypeFactory()
    evt2 = EventtypeFactory()
    evt2.for_bulletin = True
    evt1.comments = "Comments"
    headers = ["title", "title_ar", "comments", "for_actor", "for_bulletin"]
    yield from create_csv_for_entities([evt1, evt2], headers)


##### GET /admin/api/eventtypes #####

eventtypes_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", eventtypes_endpoint_roles)
def test_eventtypes_endpoint(
    clean_slate_eventtypes, create_eventtype, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get(
        "/admin/api/eventtypes", headers={"Content-Type": "application/json"}, follow_redirects=True
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        assert len(response.json["data"]["items"]) > 0
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), EventtypesResponseModel
        )


##### POST /admin/api/eventtype  #####

post_eventtype_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_eventtype_endpoint_roles)
def test_post_eventtype_endpoint(clean_slate_eventtypes, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    evt = EventtypeFactory()
    item = evt.to_dict()
    item.pop("id")
    item.pop("updated_at")
    response = client_.post(
        "/admin/api/eventtype",
        headers={"Content-Type": "application/json"},
        json={"item": item},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    found_evt = Eventtype.query.filter(Eventtype.title == evt.title).first()
    if expected_status == 200:
        assert found_evt
    else:
        assert found_evt is None


##### PUT /admin/api/eventtype/<int:id> #####

put_eventtype_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_eventtype_endpoint_roles)
def test_put_eventtype_endpoint(
    clean_slate_eventtypes, create_eventtype, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    evt = get_first_or_fail(Eventtype)
    assert evt.for_actor is False
    item = evt
    item.for_actor = True
    response = client_.put(
        f"/admin/api/eventtype/{evt.id}",
        headers={"Content-Type": "application/json"},
        json={"item": item.to_dict()},
    )
    assert response.status_code == expected_status
    found_evt = Eventtype.query.filter(Eventtype.id == evt.id).first()
    if expected_status == 200:
        assert found_evt.for_actor is True
    else:
        assert found_evt.for_actor is False


##### DELETE /admin/api/eventtype/<int:id> #####

delete_eventtype_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", delete_eventtype_endpoint_roles)
def test_delete_eventtype_endpoint(
    clean_slate_eventtypes, create_eventtype, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    evt = get_first_or_fail(Eventtype)
    response = client_.delete(
        f"/admin/api/eventtype/{evt.id}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == expected_status
    found_evt = Eventtype.query.filter(Eventtype.id == evt.id).first()
    if expected_status == 200:
        assert found_evt is None
    else:
        assert found_evt


##### POST /admin/api/eventtype/import #####

import_eventtype_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", import_eventtype_endpoint_roles)
def test_import_eventtype_endpoint(
    clean_slate_eventtypes, create_eventtype_csv, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    with open(create_eventtype_csv, "rb") as f:
        data = {"csv": (f, "test.csv")}
        response = client_.post(
            "/admin/api/eventtype/import",
            content_type="multipart/form-data",
            data=data,
            follow_redirects=True,
            headers={"Accept": "application/json"},
        )
        assert response.status_code == expected_status
        evts = Eventtype.query.all()
        if expected_status == 200:
            assert len(evts) == 2
        else:
            assert len(evts) == 0
