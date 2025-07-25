import pytest

from enferno.admin.models import PotentialViolation
from enferno.utils.validation_utils import convert_empty_strings_to_none
from tests.factories import PotentialViolationFactory
from tests.test_utils import (
    conform_to_schema_or_fail,
    create_csv_for_entities,
    get_first_or_fail,
)

#### PYDANTIC MODELS #####

from tests.models.admin import (
    PotentialViolationCreatedResponseModel,
    PotentialViolationsResponseModel,
)

##### FIXTURES #####


@pytest.fixture(scope="function")
def create_pv(session):
    pv = PotentialViolationFactory()
    session.add(pv)
    session.commit()
    yield pv
    try:
        session.query(PotentialViolation).filter(PotentialViolation.id == pv.id).delete(
            synchronize_session=False
        )
        session.commit()
    except:
        pass


@pytest.fixture(scope="function")
def clean_slate_pvs(session):
    session.query(PotentialViolation).delete(synchronize_session=False)
    session.commit()
    yield


@pytest.fixture(scope="function")
def create_pv_csv():
    pv1 = PotentialViolationFactory()
    pv2 = PotentialViolationFactory()
    headers = ["title", "title_ar"]
    yield from create_csv_for_entities([pv1, pv2], headers)


##### GET /admin/api/potentialviolation #####

pvs_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", pvs_endpoint_roles)
def test_pvs_endpoint(clean_slate_pvs, create_pv, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get(
        "/admin/api/potentialviolation",
        headers={"Content-Type": "application/json"},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        assert len(response.json["data"]["items"]) > 0
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), PotentialViolationsResponseModel
        )


##### POST /admin/api/potentialviolation #####

post_pv_endpoint_roles = [
    ("admin_client", 201),
    ("da_client", 403),
    ("mod_client", 201),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_pv_endpoint_roles)
def test_post_pv_endpoint(clean_slate_pvs, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    pv = PotentialViolationFactory()
    response = client_.post(
        "/admin/api/potentialviolation",
        headers={"Content-Type": "application/json"},
        json={"item": pv.to_dict()},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    found_pv = PotentialViolation.query.filter(PotentialViolation.title == pv.title).first()
    if expected_status == 201:
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), PotentialViolationCreatedResponseModel
        )
        assert found_pv
    else:
        assert found_pv is None


##### PUT /admin/api/potentialviolation/<int:id> #####

put_pv_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_pv_endpoint_roles)
def test_put_pv_endpoint(clean_slate_pvs, create_pv, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    pv = get_first_or_fail(PotentialViolation)
    new_pv = PotentialViolationFactory()
    response = client_.put(
        f"/admin/api/potentialviolation/{pv.id}",
        headers={"Content-Type": "application/json"},
        json={"item": new_pv.to_dict()},
    )
    assert response.status_code == expected_status
    found_pv = PotentialViolation.query.filter(PotentialViolation.id == pv.id).first()
    if expected_status == 200:
        assert found_pv.title == new_pv.title
    else:
        assert found_pv.title != new_pv.title


##### DELETE /admin/api/potentialviolation/<int:id> #####

delete_pv_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", delete_pv_endpoint_roles)
def test_delete_pv_endpoint(clean_slate_pvs, create_pv, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    pv = PotentialViolation.query.first()
    response = client_.delete(
        f"/admin/api/potentialviolation/{pv.id}", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == expected_status
    found_pv = PotentialViolation.query.filter(PotentialViolation.id == pv.id).first()
    if expected_status == 200:
        assert found_pv is None
    else:
        assert found_pv


##### POST /admin/api/potentialviolation/import #####

import_pv_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", import_pv_endpoint_roles)
def test_import_pv_endpoint(
    clean_slate_pvs, create_pv_csv, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    with open(create_pv_csv, "rb") as f:
        data = {"csv": (f, "test.csv")}
        response = client_.post(
            "/admin/api/potentialviolation/import",
            content_type="multipart/form-data",
            data=data,
            follow_redirects=True,
            headers={"Accept": "application/json"},
        )
        assert response.status_code == expected_status
        pvs = PotentialViolation.query.all()
        if expected_status == 200:
            assert len(pvs) == 2
        else:
            assert len(pvs) == 0
