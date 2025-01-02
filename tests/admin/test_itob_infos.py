import pytest

from enferno.admin.models import ItobInfo
from enferno.admin.validation.util import convert_empty_strings_to_none
from tests.factories import ItobInfoFactory
from tests.test_utils import (
    conform_to_schema_or_fail,
    get_first_or_fail,
)

#### PYDANTIC MODELS #####

from tests.models.admin import ItobInfosResponseModel

##### FIXTURES #####


@pytest.fixture(scope="function")
def create_itob_info(session):
    itob_info = ItobInfoFactory()
    session.add(itob_info)
    session.commit()
    yield itob_info
    try:
        session.query(ItobInfo).filter(ItobInfo.id == itob_info.id).delete(
            synchronize_session=False
        )
        session.commit()
    except:
        pass


@pytest.fixture(scope="function")
def clean_slate_itob_infos(session):
    session.query(ItobInfo).delete(synchronize_session=False)
    session.commit()
    yield


##### GET /admin/api/itobinfos #####

itobinfos_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", itobinfos_endpoint_roles)
def test_itobinfos_endpoint(
    clean_slate_itob_infos, create_itob_info, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get(
        "/admin/api/itobinfos",
        headers={"Content-Type": "application/json"},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), ItobInfosResponseModel
        )


##### POST /admin/api/itobinfo #####

post_itobinfo_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_itobinfo_endpoint_roles)
def test_post_itobinfo_endpoint(clean_slate_itob_infos, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    itob_info = ItobInfoFactory()
    response = client_.post(
        "/admin/api/itobinfo",
        headers={"Content-Type": "application/json"},
        json={"item": itob_info.to_dict()},
    )
    assert response.status_code == expected_status
    found_itob_info = ItobInfo.query.filter(
        ItobInfo.title == itob_info.title and ItobInfo.reverse_title == itob_info.reverse_title
    ).first()
    if expected_status == 200:
        assert found_itob_info
    else:
        assert found_itob_info is None


##### PUT /admin/api/itobinfo/<int:id> #####

put_itobinfo_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_itobinfo_endpoint_roles)
def test_put_itobinfo_endpoint(
    clean_slate_itob_infos, create_itob_info, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    new_itob_info = ItobInfoFactory()
    itob_info = get_first_or_fail(ItobInfo)
    itob_id = itob_info.id
    response = client_.put(
        f"/admin/api/itobinfo/{itob_id}",
        headers={"Content-Type": "application/json"},
        json={"item": new_itob_info.to_dict()},
    )
    assert response.status_code == expected_status
    found_itob_info = ItobInfo.query.filter(ItobInfo.id == itob_id).first()
    if expected_status == 200:
        assert (
            found_itob_info.title == new_itob_info.title
            and found_itob_info.reverse_title == new_itob_info.reverse_title
        )
    else:
        assert (
            found_itob_info.title != new_itob_info.title
            and found_itob_info.reverse_title != new_itob_info.reverse_title
        )


##### DELETE /admin/api/itobinfo/<int:id> #####

delete_itobinfo_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", delete_itobinfo_endpoint_roles)
def test_delete_itobinfo_endpoint(
    clean_slate_itob_infos, create_itob_info, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    itob_info = get_first_or_fail(ItobInfo)
    itob_id = itob_info.id
    response = client_.delete(
        f"/admin/api/itobinfo/{itob_id}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == expected_status
    found_itob_info = ItobInfo.query.filter(ItobInfo.id == itob_id).first()
    if expected_status == 200:
        assert found_itob_info is None
    else:
        assert found_itob_info
