import pytest

from enferno.admin.models import ClaimedViolation
from tests.factories import ClaimedViolationFactory
from tests.test_utils import (
    conform_to_schema_or_fail,
    convert_empty_strings_to_none,
    create_csv_for_entities,
    get_first_or_fail,
)

#### PYDANTIC MODELS #####

from tests.models.admin import ClaimedViolationsResponseModel

##### FIXTURES #####


@pytest.fixture(scope="function")
def create_cv(session):
    cv = ClaimedViolationFactory()
    session.add(cv)
    session.commit()
    yield cv
    try:
        session.query(ClaimedViolation).filter(ClaimedViolation.id == cv.id).delete(
            synchronize_session=False
        )
        session.commit()
    except:
        pass


@pytest.fixture(scope="function")
def clean_slate_cvs(session):
    session.query(ClaimedViolation).delete(synchronize_session=False)
    session.commit()
    yield


@pytest.fixture(scope="function")
def create_cv_csv():
    cv1 = ClaimedViolationFactory()
    cv2 = ClaimedViolationFactory()
    headers = ["title", "title_ar"]
    yield from create_csv_for_entities([cv1, cv2], headers)


##### GET /admin/api/claimedviolation #####

cvs_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", cvs_endpoint_roles)
def test_cvs_endpoint(clean_slate_cvs, create_cv, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get(
        "/admin/api/claimedviolation",
        headers={"Content-Type": "application/json"},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        assert len(response.json["items"]) > 0
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), ClaimedViolationsResponseModel
        )


##### POST /admin/api/claimedviolation #####

post_cv_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_cv_endpoint_roles)
def test_post_cv_endpoint(clean_slate_cvs, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    cv = ClaimedViolationFactory()
    response = client_.post(
        "/admin/api/claimedviolation",
        headers={"Content-Type": "application/json"},
        json={"item": cv.to_dict()},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    found_cv = ClaimedViolation.query.filter(ClaimedViolation.title == cv.title).first()
    if expected_status == 200:
        assert found_cv
    else:
        assert found_cv is None


##### PUT /admin/api/claimedviolation/<int:id> #####

put_cv_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_cv_endpoint_roles)
def test_put_cv_endpoint(clean_slate_cvs, create_cv, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    cv = get_first_or_fail(ClaimedViolation)
    new_cv = ClaimedViolationFactory()
    response = client_.put(
        f"/admin/api/claimedviolation/{cv.id}",
        headers={"Content-Type": "application/json"},
        json={"item": new_cv.to_dict()},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    found_cv = ClaimedViolation.query.filter(ClaimedViolation.id == cv.id).first()
    if expected_status == 200:
        assert found_cv.title == new_cv.title
    else:
        assert found_cv.title != new_cv.title


##### DELETE /admin/api/claimedviolation/<int:id> #####

delete_cv_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", delete_cv_endpoint_roles)
def test_delete_cv_endpoint(clean_slate_cvs, create_cv, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    cv = ClaimedViolation.query.first()
    response = client_.delete(
        f"/admin/api/claimedviolation/{cv.id}", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == expected_status
    found_cv = ClaimedViolation.query.filter(ClaimedViolation.id == cv.id).first()
    if expected_status == 200:
        assert found_cv is None
    else:
        assert found_cv


##### POST /admin/api/claimedviolation/import #####

import_cv_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 200),
]


@pytest.mark.parametrize("client_fixture, expected_status", import_cv_endpoint_roles)
def test_import_cv_endpoint(
    clean_slate_cvs, create_cv_csv, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    with open(create_cv_csv, "rb") as f:
        data = {"csv": (f, "test.csv")}
        response = client_.post(
            "/admin/api/claimedviolation/import",
            content_type="multipart/form-data",
            data=data,
            follow_redirects=True,
        )
        assert response.status_code == expected_status
        cvs = ClaimedViolation.query.all()
        if expected_status == 200 and client_fixture == "admin_client":
            # unauthenticated client redirects to login page with 200
            assert len(cvs) == 2
        else:
            assert len(cvs) == 0
