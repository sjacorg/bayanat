import pytest

from enferno.admin.models import AtobInfo
from enferno.utils.validation_utils import convert_empty_strings_to_none
from tests.factories import AtobInfoFactory
from tests.test_utils import (
    conform_to_schema_or_fail,
    get_first_or_fail,
)

#### PYDANTIC MODELS #####

from tests.models.admin import AtobInfoCreatedResponseModel, AtobInfosResponseModel

##### FIXTURES #####


@pytest.fixture(scope="function")
def create_atob_info(session):
    atob_info = AtobInfoFactory()
    session.add(atob_info)
    session.commit()
    yield atob_info
    try:
        session.query(AtobInfo).filter(AtobInfo.id == atob_info.id).delete(
            synchronize_session=False
        )
        session.commit()
    except:
        pass


@pytest.fixture(scope="function")
def clean_slate_atob_infos(session):
    session.query(AtobInfo).delete(synchronize_session=False)
    session.commit()
    yield


##### GET /admin/api/atobinfos #####

atobinfos_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", atobinfos_endpoint_roles)
def test_atobinfos_endpoint(
    clean_slate_atob_infos, create_atob_info, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get(
        "/admin/api/atobinfos",
        headers={"Content-Type": "application/json"},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), AtobInfosResponseModel
        )


##### POST /admin/api/atobinfo #####

post_atobinfo_endpoint_roles = [
    ("admin_client", 201),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_atobinfo_endpoint_roles)
def test_post_atobinfo_endpoint(clean_slate_atob_infos, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    atob_info = AtobInfoFactory()
    response = client_.post(
        "/admin/api/atobinfo",
        headers={"Content-Type": "application/json"},
        json={"item": atob_info.to_dict()},
    )
    assert response.status_code == expected_status
    found_atob_info = AtobInfo.query.filter(
        AtobInfo.title == atob_info.title and AtobInfo.reverse_title == atob_info.reverse_title
    ).first()
    if expected_status == 201:
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), AtobInfoCreatedResponseModel
        )
        assert found_atob_info
    else:
        assert found_atob_info is None


##### PUT /admin/api/atobinfo/<int:id> #####

put_atobinfo_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_atobinfo_endpoint_roles)
def test_put_atobinfo_endpoint(
    clean_slate_atob_infos, create_atob_info, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    new_atob_info = AtobInfoFactory()
    atob_info = get_first_or_fail(AtobInfo)
    atob_id = atob_info.id
    response = client_.put(
        f"/admin/api/atobinfo/{atob_id}",
        headers={"Content-Type": "application/json"},
        json={"item": new_atob_info.to_dict()},
    )
    assert response.status_code == expected_status
    found_atob_info = AtobInfo.query.filter(AtobInfo.id == atob_id).first()
    if expected_status == 200:
        assert (
            found_atob_info.title == new_atob_info.title
            and found_atob_info.reverse_title == new_atob_info.reverse_title
        )
    else:
        assert (
            found_atob_info.title != new_atob_info.title
            and found_atob_info.reverse_title != new_atob_info.reverse_title
        )


##### DELETE /admin/api/atobinfo/<int:id> #####

delete_atobinfo_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", delete_atobinfo_endpoint_roles)
def test_delete_atobinfo_endpoint(
    clean_slate_atob_infos, create_atob_info, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    atob_info = get_first_or_fail(AtobInfo)
    atob_id = atob_info.id
    response = client_.delete(
        f"/admin/api/atobinfo/{atob_id}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == expected_status
    found_atob_info = AtobInfo.query.filter(AtobInfo.id == atob_id).first()
    if expected_status == 200:
        assert found_atob_info is None
    else:
        assert found_atob_info
