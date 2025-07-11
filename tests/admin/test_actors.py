import pytest
from unittest.mock import patch
from enferno.admin.validation.util import convert_empty_strings_to_none
from enferno.settings import Config as cfg
from enferno.admin.models import Actor, ActorProfile, Atoa
from enferno.user.models import User
from tests.factories import (
    ActorFactory,
    create_label_for,
    create_ver_label_for,
    create_source,
    create_event_for,
    create_eventtype_for,
    create_location,
    create_profile_for,
    restrict_to_roles,
    create_simple_actor,
    create_related_actor,
    create_full_actor,
)
from tests.test_utils import (
    conform_to_schema_or_fail,
    get_first_or_fail,
    get_uid_from_client,
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
def clean_slate_actors(session):
    from enferno.admin.models import ActorHistory, ActorProfile

    session.query(ActorProfile).delete(synchronize_session=False)
    session.query(ActorHistory).delete(synchronize_session=False)
    session.query(Atoa).delete(synchronize_session=False)
    session.query(Actor).delete(synchronize_session=False)
    session.commit()
    yield


##### UTILITIES #####


def get_first_actor_or_fail():
    return get_first_or_fail(Actor)


##### GET /admin/api/actors #####

actors_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture,expected_status", actors_endpoint_roles)
def test_actors_endpoint(
    clean_slate_actors, create_full_actor, request, client_fixture, expected_status
):
    """
    Test the GET actors endpoint in non-restrictive mode with no roles specified.
    """
    with patch.object(cfg, "ACCESS_CONTROL_RESTRICTIVE", False):
        client_ = request.getfixturevalue(client_fixture)
        response = client_.get(
            "/admin/api/actors",
            json={"q": []},
            headers={"Content-Type": "application/json"},
            follow_redirects=True,
        )
        assert response.status_code == expected_status
        # If expected response is 200, assert that the response conforms to schema
        if expected_status == 200:
            print(response.json)
            conform_to_schema_or_fail(
                convert_empty_strings_to_none(response.json), ActorsResponseModel
            )


##### GET /admin/api/actor/<int:id> #####


@pytest.mark.parametrize("client_fixture,expected_status", actors_endpoint_roles)
def test_actor_endpoint(
    clean_slate_actors, create_full_actor, request, client_fixture, expected_status
):
    """
    Test the actor endpoint with different request modes and roles in non-restrictive mode with no roles specified.
    """
    with patch.object(cfg, "ACCESS_CONTROL_RESTRICTIVE", False):
        client_ = request.getfixturevalue(client_fixture)
        actor = get_first_actor_or_fail()
        response = client_.get(
            f"/admin/api/actor/{actor.id}?mode=1", headers={"Content-Type": "application/json"}
        )
        assert response.status_code == expected_status
        # Perform additional checks
        if expected_status == 200:
            # Mode 1
            data = response.json["data"]
            conform_to_schema_or_fail(convert_empty_strings_to_none(data), ActorItemMinModel)
            assert "comments" not in dict.keys(data)
            # Mode 2
            response = client_.get(
                f"/admin/api/actor/{actor.id}?mode=2", headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 200
            data = response.json["data"]
            conform_to_schema_or_fail(convert_empty_strings_to_none(data), ActorItemMode2Model)
            assert "comments" in dict.keys(data)
            assert "bulletin_relations" not in dict.keys(data)
            # Mode 3
            response = client_.get(
                f"/admin/api/actor/{actor.id}?mode=3", headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 200
            data = response.json["data"]
            conform_to_schema_or_fail(convert_empty_strings_to_none(data), ActorItemMode3Model)
            assert "actor_profiles" in dict.keys(data)
            assert "comments" in dict.keys(data)
            # Mode 3+/unspecified
            response = client_.get(
                f"/admin/api/actor/{actor.id}", headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 200
            data = response.json["data"]
            conform_to_schema_or_fail(convert_empty_strings_to_none(data), ActorItemMode3PlusModel)
            assert "bulletin_relations" in dict.keys(data)


actor_endpoint_roles_roled = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("roled_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture,expected_status", actor_endpoint_roles_roled)
def test_actor_endpoint_roled_normal(
    clean_slate_actors,
    create_full_actor,
    create_test_role,
    restrict_to_roles,
    request,
    client_fixture,
    expected_status,
):
    """
    Test the actor endpoint with different roles in non-restrictive mode with roles specified.
    """
    # Restrict role to TestRole in normal mode
    # Expectations:
    # - Admin: Full access
    # - DA: No access
    # - Mod: No access
    # - Roled: Full access
    # - Client: No access

    actor = restrict_to_roles(create_full_actor, ["TestRole"])
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get(
        f"/admin/api/actor/{actor.id}?mode=3", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == expected_status


actor_endpoint_roles_restricted = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("roled_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture,expected_status", actor_endpoint_roles_restricted)
def test_actor_endpoint_no_roles_restricted(
    clean_slate_actors, create_full_actor, request, client_fixture, expected_status
):
    """
    Test the actor endpoint with different roles in restricted mode with no roles specified.
    """
    # No roles specified in restricted mode
    # Expectations:
    # - Admin: Full access
    # - DA: No access
    # - Mod: No access
    # - Roled: No access
    # - Client: No access

    client_ = request.getfixturevalue(client_fixture)
    actor = get_first_actor_or_fail()
    with patch.object(cfg, "ACCESS_CONTROL_RESTRICTIVE", True):
        response = client_.get(
            f"/admin/api/actor/{actor.id}?mode=3", headers={"Content-Type": "application/json"}
        )
        assert response.status_code == expected_status


@pytest.mark.parametrize("client_fixture,expected_status", actor_endpoint_roles_roled)
def test_actor_endpoint_roled_restricted(
    clean_slate_actors,
    create_full_actor,
    create_test_role,
    restrict_to_roles,
    request,
    client_fixture,
    expected_status,
):
    """
    Test the GET actor endpoint with different roles in restricted mode with roles specified.
    """
    # Restrict role to TestRole in restricted mode
    # Expectations:
    # - Admin: Full access
    # - DA: No access
    # - Mod: No access
    # - Roled: Full access
    # - Client: No access

    actor = restrict_to_roles(create_full_actor, ["TestRole"])
    client_ = request.getfixturevalue(client_fixture)
    with patch.object(cfg, "ACCESS_CONTROL_RESTRICTIVE", True):
        response = client_.get(
            f"/admin/api/actor/{actor.id}?mode=3", headers={"Content-Type": "application/json"}
        )
        assert response.status_code == expected_status


##### POST /admin/api/actor #####

post_actor_endpoint_roles = [
    ("admin_client", 201),
    ("da_client", 201),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture,expected_status", post_actor_endpoint_roles)
def test_post_actor_endpoint(clean_slate_actors, request, client_fixture, expected_status):
    """
    Test the POST actor endpoint in non-restrictive mode with no roles specified.
    """
    client_ = request.getfixturevalue(client_fixture)
    actor = ActorFactory()
    actor_dict = actor.to_dict()
    actor_dict["actor_profiles"] = [{"mode": 1}]
    actor_dict["id_number"] = actor.id_number
    response = client_.post(
        "/admin/api/actor",
        headers={"content-type": "application/json"},
        json={"item": actor_dict},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    found_actor = Actor.query.filter(Actor.name == actor.name).first()
    # If expected status 200, assert that actor was created,
    # Else assert it was not created
    if expected_status == 201:
        assert found_actor
    else:
        assert found_actor is None


##### PUT /admin/api/actor/<int:id> #####

put_actor_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture,expected_status", put_actor_endpoint_roles)
def test_put_actor_endpoint(
    clean_slate_actors, create_full_actor, request, client_fixture, expected_status
):
    """
    Test the PUT actor endpoint in non-restrictive mode with no roles specified.
    """
    client_ = request.getfixturevalue(client_fixture)
    actor = get_first_actor_or_fail()
    actor_id = actor.id
    new_actor = ActorFactory()
    new_name = new_actor.name
    new_first_name = new_actor.first_name
    new_last_name = new_actor.last_name
    new_middle_name = new_actor.middle_name
    new_type = new_actor.type
    actor_dict = actor.to_dict()
    actor_dict["name"] = new_name
    actor_dict["type"] = new_type
    actor_dict["first_name"] = new_first_name
    actor_dict["last_name"] = new_last_name
    actor_dict["middle_name"] = new_middle_name
    actor_dict["actor_profiles"] = [{"mode": 1}]
    actor_dict["id_number"] = actor.id_number
    response = client_.put(
        f"/admin/api/actor/{actor_id}",
        headers={"content-type": "application/json"},
        json={"item": actor_dict},
    )
    assert response.status_code == expected_status
    found_actor = Actor.query.filter(Actor.id == actor_id).first()
    if expected_status == 200:
        assert found_actor.name == new_name
    else:
        assert found_actor.name != new_name


put_actor_endpoint_roles2 = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture,expected_status", put_actor_endpoint_roles2)
def test_put_actor_assigned_endpoint(
    users, clean_slate_actors, create_full_actor, request, client_fixture, expected_status
):
    """
    Test the PUT actor endpoint in non-restrictive mode with no roles specified.
    The actor is assigned to the user that makes the request.
    """
    with patch.object(cfg, "ACCESS_CONTROL_RESTRICTIVE", False):
        client_ = request.getfixturevalue(client_fixture)
        actor = get_first_actor_or_fail()
        uid = get_uid_from_client(users, client_fixture)
        actor.assigned_to = User.query.filter(User.id == uid).first()
        actor.save()
        actor_id = actor.id
        new_actor = ActorFactory()
        new_name = new_actor.name
        new_first_name = new_actor.first_name
        new_last_name = new_actor.last_name
        new_middle_name = new_actor.middle_name
        new_type = new_actor.type
        actor_dict = actor.to_dict()
        actor_dict["name"] = new_name
        actor_dict["type"] = new_type
        actor_dict["first_name"] = new_first_name
        actor_dict["last_name"] = new_last_name
        actor_dict["middle_name"] = new_middle_name
        actor_dict["id_number"] = actor.id_number
        response = client_.put(
            f"/admin/api/actor/{actor_id}",
            headers={"content-type": "application/json"},
            json={"item": actor_dict},
        )
        assert response.status_code == expected_status
        found_actor = Actor.query.filter(Actor.id == actor_id).first()
        if expected_status == 200:
            assert found_actor.name == new_name
        else:
            assert found_actor.name != new_name


##### PUT /admin/api/actor/assign/<int:id> #####

put_actor_assign_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
    ("admin_sa_client", 200),
    ("da_sa_client", 200),
    ("mod_sa_client", 403),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_actor_assign_endpoint_roles)
def test_put_actor_assign_endpoint(
    clean_slate_actors, create_simple_actor, request, client_fixture, expected_status
):
    """
    Test the PUT actor assignment endpoint in non-restrictive mode with no roles specified.
    Users without self-assignment permissions won't be able to assign the actor to themselves.
    """
    with patch.object(cfg, "ACCESS_CONTROL_RESTRICTIVE", False):
        client_ = request.getfixturevalue(client_fixture)
        actor = get_first_or_fail(Actor)
        actor_id = actor.id
        response = client_.put(
            f"/admin/api/actor/assign/{actor_id}",
            headers={"content-type": "application/json"},
            json={"actor": {"comments": "mandatory"}},
        )
        assert response.status_code == expected_status
        if expected_status == 200:
            found_actor = Actor.query.filter(Actor.id == actor_id).first()
            assert found_actor.assigned_to is not None


##### PUT /admin/api/actor/review/<int:id> #####

put_actor_review_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_actor_review_endpoint_roles)
def test_put_actor_review_endpoint(
    clean_slate_actors, create_full_actor, request, client_fixture, expected_status
):
    """
    Test the PUT actor review endpoint in non-restrictive mode with no roles specified.
    """
    with patch.object(cfg, "ACCESS_CONTROL_RESTRICTIVE", False):
        client_ = request.getfixturevalue(client_fixture)
        nb = ActorFactory()
        actor = get_first_or_fail(Actor)
        id = actor.id
        assert actor.review != nb.review
        nb_dict = nb.to_dict()
        nb_dict["id_number"] = nb.id_number
        response = client_.put(
            f"/admin/api/actor/review/{id}",
            headers={"content-type": "application/json"},
            json={"item": nb_dict},
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
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_actor_bulk_endpoint_roles)
def test_put_actor_bulk_endpoint(
    clean_slate_actors, create_simple_actor, request, client_fixture, expected_status
):
    """
    Test the PUT actor bulk endpoint in non-restrictive mode with no roles specified.
    """
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
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", get_actor_relations_endpoint_roles)
def test_get_actor_relations_endpoint(
    clean_slate_actors, create_related_actor, request, client_fixture, expected_status
):
    """
    Test the GET actor relations endpoint in non-restrictive mode with no roles specified.
    """
    client_ = request.getfixturevalue(client_fixture)
    a1, a2, a3 = create_related_actor
    id = a1.id
    response = client_.get(
        f"/admin/api/actor/relations/{id}?class=actor",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        assert all(
            [
                x["actor"]["id"] in [a2.id, a3.id]
                for x in convert_empty_strings_to_none(response.json)["data"]["items"]
            ]
        )
