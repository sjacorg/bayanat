import pytest

from enferno.admin.models import Ethnography
from enferno.utils.validation_utils import convert_empty_strings_to_none
from tests.factories import EthnographyFactory
from tests.test_utils import (
    conform_to_schema_or_fail,
    get_first_or_fail,
)

#### PYDANTIC MODELS #####

from tests.models.admin import EthnographiesResponseModel, EthnographyCreatedResponseModel

##### FIXTURES #####


@pytest.fixture(scope="function")
def create_ethnography(session):
    ethnography = EthnographyFactory()
    session.add(ethnography)
    session.commit()
    yield ethnography
    try:
        session.query(Ethnography).filter(Ethnography.id == ethnography.id).delete(
            synchronize_session=False
        )
        session.commit()
    except:
        pass


@pytest.fixture(scope="function")
def clean_slate_ethnographies(session):
    session.query(Ethnography).delete(synchronize_session=False)
    session.commit()
    yield


##### GET /admin/api/ethnographies #####

ethnographies_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", ethnographies_endpoint_roles)
def test_ethnographies_endpoint(
    clean_slate_ethnographies, create_ethnography, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get(
        "/admin/api/ethnographies",
        headers={"Content-Type": "application/json"},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), EthnographiesResponseModel
        )


##### POST /admin/api/ethnography #####

post_ethnography_roles = [
    ("admin_client", 201),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_ethnography_roles)
def test_post_ethnography(clean_slate_ethnographies, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    ethnography = EthnographyFactory()
    response = client_.post(
        "/admin/api/ethnography",
        headers={"Content-Type": "application/json"},
        json={"item": ethnography.to_dict()},
    )
    assert response.status_code == expected_status
    found_ethnography = Ethnography.query.filter(Ethnography.title == ethnography.title).first()
    if expected_status == 201:
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), EthnographyCreatedResponseModel
        )
        assert found_ethnography
    else:
        assert found_ethnography is None


##### PUT /admin/api/ethnography/<int:id> #####

put_ethnography_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_ethnography_roles)
def test_put_ethnography(
    clean_slate_ethnographies, create_ethnography, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    ethnography = get_first_or_fail(Ethnography)
    ethno_id = ethnography.id
    new_ethnography = EthnographyFactory()
    new_ethnography.id = ethno_id
    response = client_.put(
        f"/admin/api/ethnography/{ethno_id}",
        headers={"Content-Type": "application/json"},
        json={"item": new_ethnography.to_dict()},
    )
    assert response.status_code == expected_status
    found_ethnography = Ethnography.query.filter(Ethnography.id == ethno_id).first()
    if expected_status == 200:
        assert found_ethnography.title == new_ethnography.title
    else:
        assert found_ethnography.title != new_ethnography.title


##### DELETE /admin/api/ethnography/<int:id> #####

delete_ethnography_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", delete_ethnography_roles)
def test_delete_ethnography(
    clean_slate_ethnographies, create_ethnography, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    ethnography = get_first_or_fail(Ethnography)
    ethno_id = ethnography.id
    response = client_.delete(
        f"/admin/api/ethnography/{ethno_id}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == expected_status
    found_ethnography = Ethnography.query.filter(Ethnography.id == ethno_id).first()
    if expected_status == 200:
        assert found_ethnography is None
    else:
        assert found_ethnography
