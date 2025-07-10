import pytest

from enferno.admin.models import ItoiInfo
from enferno.utils.validation_utils import convert_empty_strings_to_none
from tests.factories import ItoiInfoFactory
from tests.test_utils import (
    conform_to_schema_or_fail,
    get_first_or_fail,
)

#### PYDANTIC MODELS #####

from tests.models.admin import ItoiInfosResponseModel

##### FIXTURES #####


@pytest.fixture(scope="function")
def create_itoi_info(session):
    itoi_info = ItoiInfoFactory()
    session.add(itoi_info)
    session.commit()
    yield itoi_info
    try:
        session.query(ItoiInfo).filter(ItoiInfo.id == itoi_info.id).delete(
            synchronize_session=False
        )
        session.commit()
    except:
        pass


@pytest.fixture(scope="function")
def clean_slate_itoi_infos(session):
    session.query(ItoiInfo).delete(synchronize_session=False)
    session.commit()
    yield


##### GET /admin/api/itoiinfos #####

itoiinfos_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", itoiinfos_endpoint_roles)
def test_itoiinfos_endpoint(
    clean_slate_itoi_infos, create_itoi_info, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get(
        "/admin/api/itoiinfos",
        headers={"Content-Type": "application/json"},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), ItoiInfosResponseModel
        )


##### POST /admin/api/itoiinfo #####

post_itoiinfo_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_itoiinfo_endpoint_roles)
def test_post_itoiinfo_endpoint(clean_slate_itoi_infos, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    itoi_info = ItoiInfoFactory()
    response = client_.post(
        "/admin/api/itoiinfo",
        headers={"Content-Type": "application/json"},
        json={"item": itoi_info.to_dict()},
    )
    assert response.status_code == expected_status
    found_itoi_info = ItoiInfo.query.filter(
        ItoiInfo.title == itoi_info.title and ItoiInfo.reverse_title == itoi_info.reverse_title
    ).first()
    if expected_status == 200:
        assert found_itoi_info
    else:
        assert found_itoi_info is None


##### PUT /admin/api/itoiinfo/<int:id> #####

put_itoiinfo_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_itoiinfo_endpoint_roles)
def test_put_itoiinfo_endpoint(
    clean_slate_itoi_infos, create_itoi_info, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    new_itoi_info = ItoiInfoFactory()
    itoi_info = get_first_or_fail(ItoiInfo)
    itoi_id = itoi_info.id
    response = client_.put(
        f"/admin/api/itoiinfo/{itoi_id}",
        headers={"Content-Type": "application/json"},
        json={"item": new_itoi_info.to_dict()},
    )
    assert response.status_code == expected_status
    found_itoi_info = ItoiInfo.query.filter(ItoiInfo.id == itoi_id).first()
    if expected_status == 200:
        assert (
            found_itoi_info.title == new_itoi_info.title
            and found_itoi_info.reverse_title == new_itoi_info.reverse_title
        )
    else:
        assert (
            found_itoi_info.title != new_itoi_info.title
            and found_itoi_info.reverse_title != new_itoi_info.reverse_title
        )


##### DELETE /admin/api/itoiinfo/<int:id> #####

delete_itoiinfo_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", delete_itoiinfo_endpoint_roles)
def test_delete_itoiinfo_endpoint(
    clean_slate_itoi_infos, create_itoi_info, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    itoi_info = get_first_or_fail(ItoiInfo)
    itoi_id = itoi_info.id
    response = client_.delete(
        f"/admin/api/itoiinfo/{itoi_id}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == expected_status
    found_itoi_info = ItoiInfo.query.filter(ItoiInfo.id == itoi_id).first()
    if expected_status == 200:
        assert found_itoi_info is None
    else:
        assert found_itoi_info
