from typing import List
import pytest
from pydantic import TypeAdapter

from enferno.admin.models import Query
from enferno.admin.validation.util import convert_empty_strings_to_none
from tests.factories import QueryFactory
from tests.test_utils import (
    conform_to_schema_or_fail,
    get_uid_from_client,
)

#### PYDANTIC MODELS #####

from tests.models.admin import QueriesResponseModel, QueryCreatedResponseModel, QueryItemModel

##### FIXTURES #####


@pytest.fixture(scope="function")
def create_query(session):
    q = QueryFactory()
    session.add(q)
    session.commit()
    yield q
    try:
        session.delete(q)
        session.commit()
    except:
        pass


@pytest.fixture(scope="function")
def clean_slate_queries(session):
    session.query(Query).delete(synchronize_session=False)
    session.commit()
    yield


##### UTILITIES #####


def update_query_user(qid, uid):
    if not uid:
        return
    q = Query.query.filter(Query.id == qid).first()
    q.user_id = uid
    q.save()


##### GET /admin/api/queries/ #####

queries_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", queries_endpoint_roles)
def test_queries_endpoint(
    clean_slate_queries, users, create_query, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    uid = get_uid_from_client(users, client_fixture)
    update_query_user(create_query.id, uid)
    response = client_.get(
        f"/admin/api/queries/?type={create_query.query_type}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        queries = TypeAdapter(List[QueryItemModel]).validate_python(
            convert_empty_strings_to_none(response.json)["data"]
        )
        conform_to_schema_or_fail({"queries": queries}, QueriesResponseModel)


##### GET /admin/api/query/<string:name>/exists #####

query_exists_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", query_exists_endpoint_roles)
def test_query_exists_endpoint(
    clean_slate_queries, users, create_query, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    uid = get_uid_from_client(users, client_fixture)
    update_query_user(create_query.id, uid)
    existing_name = create_query.name
    new_name = QueryFactory().name
    response = client_.get(
        f"/admin/api/query/{new_name}/exists", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        response = client_.get(
            f"/admin/api/query/{existing_name}/exists", headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 409


##### POST /admin/api/query/ #####
post_query_endpoint_roles = [
    ("admin_client", 201),
    ("da_client", 201),
    ("mod_client", 201),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_query_endpoint_roles)
def test_post_query_endpoint(clean_slate_queries, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    query = QueryFactory()
    response = client_.post(
        "/admin/api/query/",
        headers={"Content-Type": "application/json"},
        json={"q": {"key": "val"}, "type": query.query_type, "name": query.name},
    )
    assert response.status_code == expected_status
    found_q = Query.query.filter(Query.name == query.name).first()
    if expected_status == 201:
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), QueryCreatedResponseModel
        )
        assert found_q
    else:
        assert found_q is None


##### PUT /admin/api/query/<string:name> #####

put_query_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_query_endpoint_roles)
def test_put_query_endpoint(
    clean_slate_queries, users, create_query, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    uid = get_uid_from_client(users, client_fixture)
    update_query_user(create_query.id, uid)
    response = client_.put(
        f"/admin/api/query/{create_query.id}",
        headers={"Content-Type": "application/json"},
        json={"q": {"new_key": "new_val"}},
    )
    assert response.status_code == expected_status
    found_q = Query.query.filter(Query.id == create_query.id).first()
    if expected_status == 200:
        assert found_q.data == {"new_key": "new_val"}
    else:
        assert found_q.data == {"key": "val"}


##### DELETE /admin/api/query/<string:name> #####

delete_query_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", delete_query_endpoint_roles)
def test_delete_query_endpoint(
    clean_slate_queries, users, create_query, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    uid = get_uid_from_client(users, client_fixture)
    update_query_user(create_query.id, uid)
    response = client_.delete(
        f"/admin/api/query/{create_query.id}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == expected_status
    found_q = Query.query.filter(Query.id == create_query.id).first()
    if expected_status == 200:
        assert found_q is None
    else:
        assert found_q
