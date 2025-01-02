import pytest

from enferno.admin.models import AtoaInfo
from enferno.admin.validation.util import convert_empty_strings_to_none
from tests.factories import AtoaInfoFactory
from tests.test_utils import (
    conform_to_schema_or_fail,
    get_first_or_fail,
)

#### PYDANTIC MODELS #####

from tests.models.admin import AtoaInfosResponseModel

##### FIXTURES #####


@pytest.fixture(scope="function")
def create_atoa_info(session):
    atoa_info = AtoaInfoFactory()
    session.add(atoa_info)
    session.commit()
    yield atoa_info
    try:
        session.query(AtoaInfo).filter(AtoaInfo.id == atoa_info.id).delete(
            synchronize_session=False
        )
        session.commit()
    except:
        pass


@pytest.fixture(scope="function")
def clean_slate_atoa_infos(session):
    session.query(AtoaInfo).delete(synchronize_session=False)
    session.commit()
    yield


##### GET /admin/api/atoainfos #####

atoainfos_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", atoainfos_endpoint_roles)
def test_atoainfos_endpoint(
    clean_slate_atoa_infos, create_atoa_info, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get(
        "/admin/api/atoainfos",
        headers={"Content-Type": "application/json"},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), AtoaInfosResponseModel
        )


##### POST /admin/api/atoainfo #####

post_atoainfo_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_atoainfo_endpoint_roles)
def test_post_atoainfo_endpoint(clean_slate_atoa_infos, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    atoa_info = AtoaInfoFactory()
    response = client_.post(
        "/admin/api/atoainfo",
        headers={"Content-Type": "application/json"},
        json={"item": atoa_info.to_dict()},
    )
    assert response.status_code == expected_status
    found_atoa_info = AtoaInfo.query.filter(
        AtoaInfo.title == atoa_info.title and AtoaInfo.reverse_title == atoa_info.reverse_title
    ).first()
    if expected_status == 200:
        assert found_atoa_info
    else:
        assert found_atoa_info is None


##### PUT /admin/api/atoainfo/<int:id> #####

put_atoainfo_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_atoainfo_endpoint_roles)
def test_put_atoainfo_endpoint(
    clean_slate_atoa_infos, create_atoa_info, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    new_atoa_info = AtoaInfoFactory()
    atoa_info = get_first_or_fail(AtoaInfo)
    atoa_id = atoa_info.id
    response = client_.put(
        f"/admin/api/atoainfo/{atoa_id}",
        headers={"Content-Type": "application/json"},
        json={"item": new_atoa_info.to_dict()},
    )
    assert response.status_code == expected_status
    found_atoa_info = AtoaInfo.query.filter(AtoaInfo.id == atoa_id).first()
    if expected_status == 200:
        assert (
            found_atoa_info.title == new_atoa_info.title
            and found_atoa_info.reverse_title == new_atoa_info.reverse_title
        )
    else:
        assert (
            found_atoa_info.title != new_atoa_info.title
            and found_atoa_info.reverse_title != new_atoa_info.reverse_title
        )


##### DELETE /admin/api/atoainfo/<int:id> #####

delete_atoainfo_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", delete_atoainfo_endpoint_roles)
def test_delete_atoainfo_endpoint(
    clean_slate_atoa_infos, create_atoa_info, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    atoa_info = get_first_or_fail(AtoaInfo)
    atoa_id = atoa_info.id
    response = client_.delete(
        f"/admin/api/atoainfo/{atoa_id}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == expected_status
    found_atoa_info = AtoaInfo.query.filter(AtoaInfo.id == atoa_id).first()
    if expected_status == 200:
        assert found_atoa_info is None
    else:
        assert found_atoa_info
