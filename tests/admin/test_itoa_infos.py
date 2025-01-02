import pytest

from enferno.admin.models import ItoaInfo
from enferno.admin.validation.util import convert_empty_strings_to_none
from tests.factories import ItoaInfoFactory
from tests.test_utils import (
    conform_to_schema_or_fail,
    get_first_or_fail,
)

#### PYDANTIC MODELS #####

from tests.models.admin import ItoaInfosResponseModel

##### FIXTURES #####


@pytest.fixture(scope="function")
def create_itoa_info(session):
    itoa_info = ItoaInfoFactory()
    session.add(itoa_info)
    session.commit()
    yield itoa_info
    try:
        session.query(ItoaInfo).filter(ItoaInfo.id == itoa_info.id).delete(
            synchronize_session=False
        )
        session.commit()
    except:
        pass


@pytest.fixture(scope="function")
def clean_slate_itoa_infos(session):
    session.query(ItoaInfo).delete(synchronize_session=False)
    session.commit()
    yield


##### GET /admin/api/itoainfos #####

itoainfos_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", itoainfos_endpoint_roles)
def test_itoainfos_endpoint(
    clean_slate_itoa_infos, create_itoa_info, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get(
        "/admin/api/itoainfos",
        headers={"Content-Type": "application/json"},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), ItoaInfosResponseModel
        )


##### POST /admin/api/itoainfo #####

post_itoainfo_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_itoainfo_endpoint_roles)
def test_post_itoainfo_endpoint(clean_slate_itoa_infos, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    itoa_info = ItoaInfoFactory()
    response = client_.post(
        "/admin/api/itoainfo",
        headers={"Content-Type": "application/json"},
        json={"item": itoa_info.to_dict()},
    )
    assert response.status_code == expected_status
    found_itoa_info = ItoaInfo.query.filter(
        ItoaInfo.title == itoa_info.title and ItoaInfo.reverse_title == itoa_info.reverse_title
    ).first()
    if expected_status == 200:
        assert found_itoa_info
    else:
        assert found_itoa_info is None


##### PUT /admin/api/itoainfo/<int:id> #####

put_itoainfo_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_itoainfo_endpoint_roles)
def test_put_itoainfo_endpoint(
    clean_slate_itoa_infos, create_itoa_info, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    new_itoa_info = ItoaInfoFactory()
    itoa_info = get_first_or_fail(ItoaInfo)
    itoa_id = itoa_info.id
    response = client_.put(
        f"/admin/api/itoainfo/{itoa_id}",
        headers={"Content-Type": "application/json"},
        json={"item": new_itoa_info.to_dict()},
    )
    assert response.status_code == expected_status
    found_itoa_info = ItoaInfo.query.filter(ItoaInfo.id == itoa_id).first()
    if expected_status == 200:
        assert (
            found_itoa_info.title == new_itoa_info.title
            and found_itoa_info.reverse_title == new_itoa_info.reverse_title
        )
    else:
        assert (
            found_itoa_info.title != new_itoa_info.title
            and found_itoa_info.reverse_title != new_itoa_info.reverse_title
        )


##### DELETE /admin/api/itoainfo/<int:id> #####

delete_itoainfo_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", delete_itoainfo_endpoint_roles)
def test_delete_itoainfo_endpoint(
    clean_slate_itoa_infos, create_itoa_info, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    itoa_info = get_first_or_fail(ItoaInfo)
    itoa_id = itoa_info.id
    response = client_.delete(
        f"/admin/api/itoainfo/{itoa_id}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == expected_status
    found_itoa_info = ItoaInfo.query.filter(ItoaInfo.id == itoa_id).first()
    if expected_status == 200:
        assert found_itoa_info is None
    else:
        assert found_itoa_info
