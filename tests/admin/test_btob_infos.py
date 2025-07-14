import pytest

from enferno.admin.models import BtobInfo
from enferno.admin.validation.util import convert_empty_strings_to_none
from tests.factories import BtobInfoFactory
from tests.test_utils import (
    conform_to_schema_or_fail,
    get_first_or_fail,
)

#### PYDANTIC MODELS #####

from tests.models.admin import BtobInfoCreatedResponseModel, BtobInfosResponseModel

##### FIXTURES #####


@pytest.fixture(scope="function")
def create_btob_info(session):
    btob_info = BtobInfoFactory()
    session.add(btob_info)
    session.commit()
    yield btob_info
    try:
        session.query(BtobInfo).filter(BtobInfo.id == btob_info.id).delete(
            synchronize_session=False
        )
        session.commit()
    except:
        pass


@pytest.fixture(scope="function")
def clean_slate_btob_infos(session):
    session.query(BtobInfo).delete(synchronize_session=False)
    session.commit()
    yield


##### GET /admin/api/btobinfos #####

btobinfos_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", btobinfos_endpoint_roles)
def test_btobinfos_endpoint(
    clean_slate_btob_infos, create_btob_info, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get(
        "/admin/api/btobinfos",
        headers={"Content-Type": "application/json"},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), BtobInfosResponseModel
        )


##### POST /admin/api/btobinfo #####

post_btobinfo_endpoint_roles = [
    ("admin_client", 201),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_btobinfo_endpoint_roles)
def test_post_btobinfo_endpoint(clean_slate_btob_infos, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    btob_info = BtobInfoFactory()
    response = client_.post(
        "/admin/api/btobinfo",
        headers={"Content-Type": "application/json"},
        json={"item": btob_info.to_dict()},
    )
    assert response.status_code == expected_status
    found_btob_info = BtobInfo.query.filter(
        BtobInfo.title == btob_info.title and BtobInfo.reverse_title == btob_info.reverse_title
    ).first()
    if expected_status == 201:
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), BtobInfoCreatedResponseModel
        )
        assert found_btob_info
    else:
        assert found_btob_info is None


##### PUT /admin/api/btobinfo/<int:id> #####

put_btobinfo_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_btobinfo_endpoint_roles)
def test_put_btobinfo_endpoint(
    clean_slate_btob_infos, create_btob_info, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    new_btob_info = BtobInfoFactory()
    btob_info = get_first_or_fail(BtobInfo)
    btob_id = btob_info.id
    response = client_.put(
        f"/admin/api/btobinfo/{btob_id}",
        headers={"Content-Type": "application/json"},
        json={"item": new_btob_info.to_dict()},
    )
    assert response.status_code == expected_status
    found_btob_info = BtobInfo.query.filter(BtobInfo.id == btob_id).first()
    if expected_status == 200:
        assert (
            found_btob_info.title == new_btob_info.title
            and found_btob_info.reverse_title == new_btob_info.reverse_title
        )
    else:
        assert (
            found_btob_info.title != new_btob_info.title
            and found_btob_info.reverse_title != new_btob_info.reverse_title
        )


##### DELETE /admin/api/btobinfo/<int:id> #####

delete_btobinfo_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", delete_btobinfo_endpoint_roles)
def test_delete_btobinfo_endpoint(
    clean_slate_btob_infos, create_btob_info, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    btob_info = get_first_or_fail(BtobInfo)
    btob_id = btob_info.id
    response = client_.delete(
        f"/admin/api/btobinfo/{btob_id}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == expected_status
    found_btob_info = BtobInfo.query.filter(BtobInfo.id == btob_id).first()
    if expected_status == 200:
        assert found_btob_info is None
    else:
        assert found_btob_info
