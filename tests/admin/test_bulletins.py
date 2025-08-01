import pytest
from unittest.mock import patch
from enferno.admin.models import Activity, Bulletin, Btob, GeoLocation, Location
from enferno.utils.validation_utils import convert_empty_strings_to_none
from enferno.user.models import User
from enferno.settings import Config as cfg
from tests.factories import (
    BulletinFactory,
    create_source,
    create_location,
    create_label_for,
    create_ver_label_for,
    create_eventtype_for,
    create_event_for,
    create_geolocation,
    restrict_to_roles,
)
from tests.admin.data.generators import (
    create_simple_bulletin,
    create_related_bulletin,
    create_full_bulletin,
)

from tests.test_utils import (
    conform_to_schema_or_fail,
    get_first_or_fail,
    load_data,
    get_uid_from_client,
)

##### PYDANTIC MODELS #####

from tests.models.admin import (
    BulletinsResponseModel,
    BulletinItemMode3PlusModel,
    BulletinItemMode3Model,
    BulletinItemMinModel,
    BulletinItemMode2Model,
)

##### FIXTURES #####


@pytest.fixture(scope="function")
def clean_slate_bulletins(session):
    from enferno.admin.models import BulletinHistory

    session.query(Btob).delete(synchronize_session=False)
    session.query(BulletinHistory).delete(synchronize_session=False)
    session.query(GeoLocation).delete(synchronize_session=False)
    session.query(Location).delete(synchronize_session=False)
    session.query(Bulletin).delete(synchronize_session=False)
    session.commit()
    yield


##### GET /admin/api/bulletins #####

bulletins_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", bulletins_endpoint_roles)
def test_bulletins_endpoint(
    clean_slate_bulletins, create_full_bulletin, request, client_fixture, expected_status
):
    """
    Test the GET bulletins endpoint in non-restrictive mode with no roles specified.
    """
    with patch.object(cfg, "ACCESS_CONTROL_RESTRICTIVE", False):
        client_ = request.getfixturevalue(client_fixture)
        response = client_.get(
            "/admin/api/bulletins",
            json={"q": [{}]},
            headers={"Content-Type": "application/json"},
            follow_redirects=True,
        )
        assert response.status_code == expected_status
        if expected_status == 200:
            data = convert_empty_strings_to_none(response.json)
            conform_to_schema_or_fail(data, BulletinsResponseModel)


##### GET /admin/api/bulletin/<int:id> #####

bulletin_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", bulletin_endpoint_roles)
def test_bulletin_endpoint(
    clean_slate_bulletins, create_full_bulletin, request, client_fixture, expected_status
):
    """
    Test the GET bulletin endpoint in non-restrictive mode with no roles specified.
    """
    with patch.object(cfg, "ACCESS_CONTROL_RESTRICTIVE", False):
        client_ = request.getfixturevalue(client_fixture)
        bulletin = get_first_or_fail(Bulletin)
        response = client_.get(
            f"/admin/api/bulletin/{bulletin.id}", headers={"Accept": "application/json"}
        )
        assert response.status_code == expected_status
        # Additional checks
        if expected_status == 200:
            data = convert_empty_strings_to_none(load_data(response))
            conform_to_schema_or_fail(data, BulletinItemMode3PlusModel)
            # Mode 1
            response = client_.get(f"/admin/api/bulletin/{bulletin.id}?mode=1")
            data = convert_empty_strings_to_none(load_data(response))
            assert "tags" not in dict.keys(data)
            conform_to_schema_or_fail(data, BulletinItemMinModel)
            # Mode 2
            response = client_.get(f"/admin/api/bulletin/{bulletin.id}?mode=2")
            data = convert_empty_strings_to_none(load_data(response))
            assert "tags" not in dict.keys(data)
            conform_to_schema_or_fail(data, BulletinItemMode2Model)
            # Mode 3
            response = client_.get(f"/admin/api/bulletin/{bulletin.id}?mode=3")
            data = convert_empty_strings_to_none(load_data(response))
            assert "tags" in dict.keys(data)
            conform_to_schema_or_fail(data, BulletinItemMode3Model)


bulletin_endpoint_roles_roled = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("roled_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", bulletin_endpoint_roles_roled)
def test_bulletin_endpoint_roled_normal(
    clean_slate_bulletins,
    create_test_role,
    restrict_to_roles,
    create_full_bulletin,
    request,
    client_fixture,
    expected_status,
):
    """
    Test the GET bulletin endpoint in non-restrictive mode with roles specified.
    """
    # Restrict role to TestRole in normal mode
    # Expectations:
    # - Admin: Full access
    # - DA: No access
    # - Mod: No access
    # - TestRole: Full access

    bulletin = restrict_to_roles(create_full_bulletin, ["TestRole"])
    client_ = request.getfixturevalue(client_fixture)
    bulletin = get_first_or_fail(Bulletin)
    response = client_.get(
        f"/admin/api/bulletin/{bulletin.id}", headers={"Accept": "application/json"}
    )
    assert response.status_code == expected_status


bulletin_endpoint_roles_restricted = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("roled_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", bulletin_endpoint_roles_restricted)
def test_bulletin_endpoint_no_roles_restricted(
    clean_slate_bulletins, create_full_bulletin, request, client_fixture, expected_status
):
    """
    Test the GET bulletin endpoint in restrictive mode with no roles specified.
    """
    # No roles specified in restrictive mode
    # Expectations:
    # - Admin: Full access
    # - DA: No access
    # - Mod: No access
    # - TestRole: No access

    client_ = request.getfixturevalue(client_fixture)
    bulletin = get_first_or_fail(Bulletin)
    with patch.object(cfg, "ACCESS_CONTROL_RESTRICTIVE", True):
        response = client_.get(
            f"/admin/api/bulletin/{bulletin.id}", headers={"Accept": "application/json"}
        )
        assert response.status_code == expected_status


@pytest.mark.parametrize("client_fixture, expected_status", bulletin_endpoint_roles_roled)
def test_bulletin_endpoint_roled_restricted(
    clean_slate_bulletins,
    create_test_role,
    restrict_to_roles,
    create_full_bulletin,
    request,
    client_fixture,
    expected_status,
):
    """
    Test the GET bulletin endpoint in restrictive mode with roles specified.
    """
    # Restrict role to TestRole in restrictive mode
    # Expectations:
    # - Admin: Full access
    # - DA: No access
    # - Mod: No access
    # - TestRole: Full access

    bulletin = restrict_to_roles(create_full_bulletin, ["TestRole"])
    client_ = request.getfixturevalue(client_fixture)
    bulletin = get_first_or_fail(Bulletin)
    with patch.object(cfg, "ACCESS_CONTROL_RESTRICTIVE", True):
        response = client_.get(
            f"/admin/api/bulletin/{bulletin.id}", headers={"Accept": "application/json"}
        )
        assert response.status_code == expected_status


##### POST /admin/api/bulletin #####

post_bulletin_endpoint_roles = [
    ("admin_client", 201),
    ("da_client", 201),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_bulletin_endpoint_roles)
def test_post_bulletin_endpoint(clean_slate_bulletins, request, client_fixture, expected_status):
    """
    Test the POST bulletin endpoint in non-restrictive mode with no roles specified.
    """
    client_ = request.getfixturevalue(client_fixture)
    bulletin = BulletinFactory()
    bdict = bulletin.to_dict()
    bdict.pop("roles")
    response = client_.post(
        "/admin/api/bulletin",
        headers={"content-type": "application/json"},
        json={"item": bdict},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    found_bulletin = Bulletin.query.filter(Bulletin.title == bulletin.title).first()
    if expected_status == 201:
        assert found_bulletin
    else:
        assert found_bulletin is None


##### PUT /admin/api/bulletin/<int:id> #####

put_bulletin_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_bulletin_endpoint_roles)
def test_put_bulletin_endpoint(
    clean_slate_bulletins, create_simple_bulletin, request, client_fixture, expected_status
):
    """
    Test the PUT bulletin endpoint in non-restrictive mode with no roles specified.
    """
    client_ = request.getfixturevalue(client_fixture)
    bulletin = get_first_or_fail(Bulletin)
    bulletin_id = bulletin.id
    bdict = bulletin.to_dict()
    bdict["title"] = BulletinFactory().title
    assert bdict["title"] != bulletin.title
    bdict.pop("roles")
    response = client_.put(
        f"/admin/api/bulletin/{bulletin_id}",
        headers={"content-type": "application/json"},
        json={"item": bdict},
    )
    assert response.status_code == expected_status
    found_bulletin = Bulletin.query.filter(Bulletin.id == bulletin_id).first()
    if expected_status == 200:
        assert found_bulletin.title == bdict["title"]
    else:
        assert found_bulletin.title != bdict["title"]


put_bulletin_endpoint_roles2 = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_bulletin_endpoint_roles2)
def test_put_bulletin_assigned_endpoint(
    users, clean_slate_bulletins, create_full_bulletin, request, client_fixture, expected_status
):
    """
    Test the PUT bulletin endpoint in non-restrictive mode with no roles specified.
    The bulletin is assigned to the user making the request.
    """
    # No roles specified in normal mode
    # Expectations:
    # - Admin: Full access
    # - DA: Full access
    # - Mod: No access
    with patch.object(cfg, "ACCESS_CONTROL_RESTRICTIVE", False):
        client_ = request.getfixturevalue(client_fixture)
        bulletin = get_first_or_fail(Bulletin)
        uid = get_uid_from_client(users, client_fixture)
        bulletin.assigned_to = User.query.filter(User.id == uid).first()
        bulletin.save()
        bulletin_id = bulletin.id
        bdict = bulletin.to_dict()
        bdict.pop("roles")
        bdict["title"] = BulletinFactory().title
        response = client_.put(
            f"/admin/api/bulletin/{bulletin_id}",
            headers={"content-type": "application/json"},
            json={"item": bdict},
        )
        assert response.status_code == expected_status
        found_bulletin = Bulletin.query.filter(Bulletin.id == bulletin_id).first()
        if expected_status == 200:
            assert found_bulletin.title == bdict["title"]
        else:
            assert found_bulletin.title != bdict["title"]


##### PUT /admin/api/bulletin/review/<int:id> #####

put_bulletin_review_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_bulletin_review_endpoint_roles)
def test_put_bulletin_review_endpoint(
    clean_slate_bulletins, create_full_bulletin, request, client_fixture, expected_status
):
    """
    Test the PUT bulletin review endpoint in non-restrictive mode with no roles specified.
    """
    with patch.object(cfg, "ACCESS_CONTROL_RESTRICTIVE", False):
        client_ = request.getfixturevalue(client_fixture)
        nb = BulletinFactory()
        bulletin = get_first_or_fail(Bulletin)
        bulletin_id = bulletin.id
        assert bulletin.review != nb.review
        response = client_.put(
            f"/admin/api/bulletin/review/{bulletin_id}",
            headers={"content-type": "application/json"},
            json={"item": nb.to_dict()},
        )
        assert response.status_code == expected_status
        found_bulletin = Bulletin.query.filter(Bulletin.id == bulletin_id).first()
        if expected_status == 200:
            assert found_bulletin.review == nb.review
        else:
            assert found_bulletin.review != nb.review


##### PUT /admin/api/bulletin/bulk #####

put_bulletin_bulk_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_bulletin_bulk_endpoint_roles)
def test_put_bulletin_bulk_endpoint(
    clean_slate_bulletins, create_full_bulletin, request, client_fixture, expected_status
):
    """
    Test the PUT bulletin bulk endpoint in non-restrictive mode with no roles specified.
    """
    client_ = request.getfixturevalue(client_fixture)
    bulletin = get_first_or_fail(Bulletin)
    ids = [bulletin.id]
    bulk = {"status": "bulk updated"}
    response = client_.put(
        f"/admin/api/bulletin/bulk",
        headers={"content-type": "application/json"},
        json={"items": ids, "bulk": bulk},
        follow_redirects=True,
    )
    assert response.status_code == expected_status


##### GET /admin/api/bulletin/relations/<int:id> #####

get_bulletin_relations_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", get_bulletin_relations_endpoint_roles)
def test_get_bulletin_relations_endpoint(
    clean_slate_bulletins, create_related_bulletin, request, client_fixture, expected_status
):
    """
    Test the GET bulletin relations endpoint in non-restrictive mode with no roles specified.
    """
    client_ = request.getfixturevalue(client_fixture)
    b1, b2, b3 = create_related_bulletin
    bulletin_id = b1.id
    response = client_.get(
        f"/admin/api/bulletin/relations/{bulletin_id}?class=bulletin",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        assert all([x["bulletin"]["id"] in [b2.id, b3.id] for x in load_data(response)["items"]])


##### PUT /admin/api/bulletin/assign/<int:id> #####

put_bulletin_assign_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
    ("admin_sa_client", 200),
    ("da_sa_client", 200),
    ("mod_sa_client", 403),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_bulletin_assign_endpoint_roles)
def test_put_bulletin_assign_endpoint(
    clean_slate_bulletins, create_simple_bulletin, request, client_fixture, expected_status
):
    """
    Test the PUT bulletin assign endpoint in non-restrictive mode with no roles specified.
    Users without self-assign permissions will not be able to assign the bulletin to themselves.
    """
    with patch.object(cfg, "ACCESS_CONTROL_RESTRICTIVE", False):
        client_ = request.getfixturevalue(client_fixture)
        bulletin = get_first_or_fail(Bulletin)
        bulletin_id = bulletin.id
        response = client_.put(
            f"/admin/api/bulletin/assign/{bulletin_id}",
            headers={"content-type": "application/json"},
            json={"bulletin": {"comments": "are now mandatory"}},
        )
        assert response.status_code == expected_status
        if expected_status == 200:
            found_bulletin = Bulletin.query.filter(Bulletin.id == bulletin_id).first()
            assert found_bulletin.assigned_to is not None
