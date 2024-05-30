import pytest
from enferno.admin.models import Bulletin, Btob
from enferno.user.models import User
from tests.factories import (
    BulletinFactory,
    create_source,
    create_location,
    create_label_for,
    create_ver_label_for,
    create_eventtype_for,
    create_event_for,
)
from tests.admin.data.generators import (
    create_simple_bulletin,
    create_related_bulletin,
    create_full_bulletin,
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
    session.query(Bulletin).delete(synchronize_session=False)
    session.commit()
    yield


##### GET /admin/api/bulletins #####

bulletins_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", bulletins_endpoint_roles)
def test_bulletins_endpoint(
    clean_slate_bulletins, create_full_bulletin, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get(
        "/admin/api/bulletins?page=1&per_page=10&cache=1",
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
    ("client", 302),
]


@pytest.mark.parametrize("client_fixture, expected_status", bulletin_endpoint_roles)
def test_bulletin_endpoint(
    clean_slate_bulletins, create_full_bulletin, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    bulletin = get_first_or_fail(Bulletin)
    response = client_.get(f"/admin/api/bulletin/{bulletin.id}")
    assert response.status_code == expected_status
    # Additional checks
    if expected_status == 200:
        data = convert_empty_strings_to_none(load_data(response))
        conform_to_schema_or_fail(data, BulletinItemMode3PlusModel)
        # Mode 1
        response = client_.get(f"/admin/api/bulletin/{bulletin.id}?mode=1")
        data = convert_empty_strings_to_none(load_data(response))
        assert "ref" not in dict.keys(data)
        conform_to_schema_or_fail(data, BulletinItemMinModel)
        # Mode 2
        response = client_.get(f"/admin/api/bulletin/{bulletin.id}?mode=2")
        data = convert_empty_strings_to_none(load_data(response))
        assert "ref" not in dict.keys(data)
        conform_to_schema_or_fail(data, BulletinItemMode2Model)
        # Mode 3
        response = client_.get(f"/admin/api/bulletin/{bulletin.id}?mode=3")
        data = convert_empty_strings_to_none(load_data(response))
        assert "ref" in dict.keys(data)
        conform_to_schema_or_fail(data, BulletinItemMode3Model)
    elif expected_status == 302:
        assert "login" in response.headers["Location"]


##### POST /admin/api/bulletin #####

post_bulletin_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 403),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_bulletin_endpoint_roles)
def test_post_bulletin_endpoint(clean_slate_bulletins, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    bulletin = BulletinFactory()
    response = client_.post(
        "/admin/api/bulletin",
        headers={"content-type": "application/json"},
        json={"item": {"title": bulletin.title}},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    found_bulletin = Bulletin.query.filter(Bulletin.title == bulletin.title).first()
    if expected_status == 200:
        assert found_bulletin
    else:
        assert found_bulletin is None


##### PUT /admin/api/bulletin/<int:id> #####

put_bulletin_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_bulletin_endpoint_roles)
def test_put_bulletin_endpoint(
    clean_slate_bulletins, create_simple_bulletin, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    bulletin = get_first_or_fail(Bulletin)
    bulletin_id = bulletin.id
    new_title = BulletinFactory().title
    response = client_.put(
        f"/admin/api/bulletin/{bulletin_id}",
        headers={"content-type": "application/json"},
        json={"item": {"title": new_title}},
    )
    assert response.status_code == expected_status
    found_bulletin = Bulletin.query.filter(Bulletin.id == bulletin_id).first()
    if expected_status == 200:
        assert found_bulletin.title == new_title
    else:
        assert found_bulletin.title != new_title


put_bulletin_endpoint_roles2 = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 403),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_bulletin_endpoint_roles2)
def test_put_bulletin_endpoint(
    users, create_full_bulletin, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    bulletin = get_first_or_fail(Bulletin)
    uid = get_uid_from_client(users, client_fixture)
    bulletin.assigned_to = User.query.filter(User.id == uid).first()
    bulletin.save()
    bulletin_id = bulletin.id
    new_title = BulletinFactory().title
    response = client_.put(
        f"/admin/api/bulletin/{bulletin_id}",
        headers={"content-type": "application/json"},
        json={"item": {"title": new_title}},
    )
    assert response.status_code == expected_status
    found_bulletin = Bulletin.query.filter(Bulletin.id == bulletin_id).first()
    if expected_status == 200:
        assert found_bulletin.title == new_title
    else:
        assert found_bulletin.title != new_title


##### PUT /admin/api/bulletin/review/<int:id> #####

put_bulletin_review_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 403),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_bulletin_review_endpoint_roles)
def test_put_bulletin_review_endpoint(
    clean_slate_bulletins, create_full_bulletin, request, client_fixture, expected_status
):
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
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_bulletin_bulk_endpoint_roles)
def test_put_bulletin_bulk_endpoint(
    clean_slate_bulletins, create_full_bulletin, request, client_fixture, expected_status
):
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
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", get_bulletin_relations_endpoint_roles)
def test_get_bulletin_relations_endpoint(
    clean_slate_bulletins, create_related_bulletin, request, client_fixture, expected_status
):
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
    ("admin_client", 400),
    ("da_client", 400),
    ("mod_client", 403),
    ("client", 401),
    ("admin_sa_client", 200),
    ("da_sa_client", 200),
    ("mod_sa_client", 403),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_bulletin_assign_endpoint_roles)
def test_put_bulletin_assign_endpoint(
    clean_slate_bulletins, create_simple_bulletin, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    bulletin = get_first_or_fail(Bulletin)
    bulletin_id = bulletin.id
    response = client_.put(
        f"/admin/api/bulletin/assign/{bulletin_id}",
        headers={"content-type": "application/json"},
        json={"bulletin": {"comments": ""}},
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        found_bulletin = Bulletin.query.filter(Bulletin.id == bulletin_id).first()
        assert found_bulletin.assigned_to is not None
