import pytest

from enferno.admin.models import Source
from tests.factories import SourceFactory
from tests.test_utils import (
    conform_to_schema_or_fail,
    convert_empty_strings_to_none,
    create_csv_for_entities,
    get_first_or_fail,
)

#### PYDANTIC MODELS #####

from tests.models.admin import SourcesResponseModel

##### FIXTURES #####


@pytest.fixture(scope="function")
def create_source(session):
    source = SourceFactory()
    session.add(source)
    session.commit()
    yield source
    try:
        session.query(Source).filter(Source.id == source.id).delete(synchronize_session=False)
        session.commit()
    except:
        pass


@pytest.fixture(scope="function")
def clean_slate_sources(session):
    session.query(Source).delete(synchronize_session=False)
    session.commit()
    yield


@pytest.fixture(scope="function")
def create_source_csv():
    s1 = Source()
    s2 = Source()
    headers = ["title", "title_ar", "comments"]
    yield from create_csv_for_entities([s1, s2], headers)


##### GET /admin/api/sources #####

sources_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", sources_endpoint_roles)
def test_sources_endpoint(
    clean_slate_sources, create_source, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get(
        "/admin/api/sources",
        headers={"Content-Type": "application/json"},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        assert len(response.json["items"]) > 0
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), SourcesResponseModel
        )


##### POST /admin/api/source #####

post_source_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 200),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_source_endpoint_roles)
def test_post_source_endpoint(clean_slate_sources, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    source = SourceFactory()
    response = client_.post(
        "/admin/api/source",
        headers={"Content-Type": "application/json"},
        json={"item": source.to_dict()},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    found_source = Source.query.filter(Source.title == source.title).first()
    if expected_status == 200:
        assert found_source
    else:
        assert found_source is None


##### PUT /admin/api/source/<int:id> #####

put_source_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 200),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_source_endpoint_roles)
def test_put_source_endpoint(
    clean_slate_sources, create_source, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    source = get_first_or_fail(Source)
    new_source = SourceFactory()
    response = client_.put(
        f"/admin/api/source/{source.id}",
        headers={"Content-Type": "application/json"},
        json={"item": new_source.to_dict()},
    )
    assert response.status_code == expected_status
    found_source = Source.query.filter(Source.id == source.id).first()
    if expected_status == 200:
        assert found_source.title == new_source.title
    else:
        assert found_source.title != new_source.title


##### DELETE /admin/api/source/<int:id> #####

delete_source_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", delete_source_endpoint_roles)
def test_delete_source_endpoint(
    clean_slate_sources, create_source, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    source = Source.query.first()
    response = client_.delete(
        f"/admin/api/source/{source.id}", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == expected_status
    found_source = Source.query.filter(Source.id == source.id).first()
    if expected_status == 200:
        assert found_source is None
    else:
        assert found_source


##### POST /admin/api/source/import #####

import_source_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("client", 200),
]


@pytest.mark.parametrize("client_fixture, expected_status", import_source_endpoint_roles)
def test_import_source_endpoint(
    clean_slate_sources, create_source_csv, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    with open(create_source_csv, "rb") as f:
        data = {"csv": (f, "test.csv")}
        response = client_.post(
            "/admin/api/source/import",
            content_type="multipart/form-data",
            data=data,
            follow_redirects=True,
        )
        assert response.status_code == expected_status
        sources = Source.query.all()
        if expected_status == 200 and client_fixture != "client":
            # unauthenticated client redirects to login page with 200
            assert len(sources) == 2
        else:
            assert len(sources) == 0
