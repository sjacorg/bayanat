import json
import pytest

from enferno.admin.models import Actor
from tests.factories import ActorFactory
from tests.test_utils import (
    conform_to_schema_or_fail,
    convert_empty_strings_to_none,
    get_first_or_fail,
    load_data,
)

##### PYDANTIC MODELS #####

from tests.models.admin import (
    ActorsResponseModel,
    ActorItemMinModel,
    ActorItemMode2Model,
    ActorItemMode3Model,
    ActorItemMode3PlusModel,
)

##### FIXTURES #####


@pytest.fixture(scope="function")
def create_actor(session):
    from enferno.admin.models import ActorHistory

    actor = ActorFactory()
    session.add(actor)
    session.commit()
    yield actor
    session.query(ActorHistory).filter(ActorHistory.actor_id == actor.id).delete(
        synchronize_session=False
    )
    session.query(Actor).filter(Actor.id == actor.id).delete(synchronize_session=False)
    session.commit()


@pytest.fixture(scope="function")
def clean_slate_actors(session):
    from enferno.admin.models import ActorHistory

    session.query(ActorHistory).delete(synchronize_session=False)
    session.query(Actor).delete(synchronize_session=False)
    session.commit()
    yield


@pytest.fixture(scope="function")
def create_related_actor(session, users):
    from enferno.admin.models import ActorHistory, Atoa

    a1 = ActorFactory()
    a2 = ActorFactory()
    a3 = ActorFactory()
    session.add(a3)
    session.add(a2)
    session.add(a1)
    session.commit()
    a2.relate_actor(a1, json.dumps({}), False)
    a3.relate_actor(a1, json.dumps({}), False)
    yield a1, a2, a3
    session.query(Atoa).filter(Atoa.actor_id.in_([a1.id, a2.id, a3.id])).delete(
        synchronize_session=False
    )
    session.query(Atoa).filter(Atoa.related_actor_id.in_([a1.id, a2.id, a3.id])).delete(
        synchronize_session=False
    )
    session.query(ActorHistory).filter(ActorHistory.actor_id.in_([a1.id, a2.id, a3.id])).delete(
        synchronize_session=False
    )
    session.query(Actor).filter(Actor.id.in_([a1.id, a2.id, a3.id])).delete(
        synchronize_session=False
    )
    session.commit()


##### UTILITIES #####


def get_first_actor_or_fail():
    return get_first_or_fail(Actor)


##### GET /admin/api/actors #####

actors_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture,expected_status", actors_endpoint_roles)
def test_actors_endpoint(create_actor, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get(
        "/admin/api/actors",
        json={"q": [{}]},
        headers={"Content-Type": "application/json"},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    # If expected response is 200, assert that the response conforms to schema
    if expected_status == 200:
        conform_to_schema_or_fail(response.json, ActorsResponseModel)


##### GET /admin/api/actor/<int:id> #####


@pytest.mark.parametrize("client_fixture,expected_status", actors_endpoint_roles)
def test_actor_endpoint(create_actor, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    actor = get_first_actor_or_fail()
    response = client_.get(
        f"/admin/api/actor/{actor.id}?mode=1", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == expected_status
    # Perform additional checks
    if expected_status == 200:
        # Mode 1
        data = convert_empty_strings_to_none(load_data(response))
        conform_to_schema_or_fail(data, ActorItemMinModel)
        assert "originid" not in dict.keys(data)
        # Mode 2
        response = client_.get(
            f"/admin/api/actor/{actor.id}?mode=2", headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = convert_empty_strings_to_none(load_data(response))
        conform_to_schema_or_fail(data, ActorItemMode2Model)
        assert "originid" in dict.keys(data)
        assert "bulletin_relations" not in dict.keys(data)
        # Mode 3
        response = client_.get(
            f"/admin/api/actor/{actor.id}?mode=3", headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = convert_empty_strings_to_none(load_data(response))
        conform_to_schema_or_fail(data, ActorItemMode3Model)
        assert "originid" in dict.keys(data)
        assert "bulletin_relations" in dict.keys(data)
        # Mode 3+/unspecified
        response = client_.get(
            f"/admin/api/actor/{actor.id}", headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = convert_empty_strings_to_none(load_data(response))
        conform_to_schema_or_fail(data, ActorItemMode3PlusModel)
        assert "bulletin_relations" in dict.keys(data)


##### POST /admin/api/actor #####

post_actor_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 403),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture,expected_status", post_actor_endpoint_roles)
def test_post_actor_endpoint(clean_slate_actors, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    actor = ActorFactory()
    response = client_.post(
        "/admin/api/actor",
        headers={"content-type": "application/json"},
        json={"item": {"name": actor.name}},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    found_actor = Actor.query.filter(Actor.name == actor.name).first()
    # If expected status 200, assert that actor was created,
    # Else assert it was not created
    if expected_status == 200:
        assert found_actor
    else:
        assert found_actor is None


##### PUT /admin/api/actor/<int:id> #####

put_actor_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 403),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture,expected_status", put_actor_endpoint_roles)
def test_put_actor_endpoint(create_actor, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    actor = get_first_actor_or_fail()
    actor_id = actor.id
    new_name = ActorFactory().name
    response = client_.put(
        f"/admin/api/actor/{actor_id}",
        headers={"content-type": "application/json"},
        json={"item": {"name": new_name}},
    )
    assert response.status_code == expected_status
    found_actor = Actor.query.filter(Actor.id == actor_id).first()
    if expected_status == 200:
        assert found_actor.name == new_name
    else:
        assert found_actor.name != new_name


##### PUT /admin/api/actor/assign/<int:id> #####

put_actor_assign_endpoint_roles = [
    ("admin_client", 400),
    ("da_client", 400),
    ("mod_client", 403),
    ("client", 401),
    ("admin_sa_client", 200),
    ("da_sa_client", 200),
    ("mod_sa_client", 403),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_actor_assign_endpoint_roles)
def test_put_actor_assign_endpoint(
    clean_slate_actors, create_actor, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    actor = get_first_or_fail(Actor)
    id = actor.id
    response = client_.put(
        f"/admin/api/actor/assign/{id}",
        headers={"content-type": "application/json"},
        json={"actor": {"comments": ""}},
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        found_actor = Actor.query.filter(Actor.id == id).first()
        assert found_actor.assigned_to is not None


##### PUT /admin/api/actor/review/<int:id> #####

put_actor_review_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 403),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_actor_review_endpoint_roles)
def test_put_actor_review_endpoint(
    clean_slate_actors, create_actor, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    nb = ActorFactory()
    actor = get_first_or_fail(Actor)
    id = actor.id
    assert actor.review != nb.review
    response = client_.put(
        f"/admin/api/actor/review/{id}",
        headers={"content-type": "application/json"},
        json={"item": nb.to_dict()},
    )
    assert response.status_code == expected_status
    found_actor = Actor.query.filter(Actor.id == id).first()
    if expected_status == 200:
        assert found_actor.review == nb.review
    else:
        assert found_actor.review != nb.review


##### PUT /admin/api/actor/bulk #####

put_actor_bulk_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 200),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_actor_bulk_endpoint_roles)
def test_put_actor_bulk_endpoint(
    clean_slate_actors, create_actor, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    actor = get_first_or_fail(Actor)
    ids = [actor.id]
    bulk = {"status": "bulk updated"}
    response = client_.put(
        f"/admin/api/actor/bulk/",
        headers={"content-type": "application/json"},
        json={"items": ids, "bulk": bulk},
    )
    assert response.status_code == expected_status


##### GET /admin/api/actor/relations/<int:id> #####

get_actor_relations_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", get_actor_relations_endpoint_roles)
def test_get_actor_relations_endpoint(
    clean_slate_actors, create_related_actor, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    a1, a2, a3 = create_related_actor
    id = a1.id
    response = client_.get(
        f"/admin/api/actor/relations/{id}?class=actor",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        assert all([x["actor"]["id"] in [a2.id, a3.id] for x in load_data(response)["items"]])
