import pytest

from enferno.admin.models import MediaCategory
from enferno.utils.validation_utils import convert_empty_strings_to_none
from tests.factories import MediaCategoryFactory
from tests.test_utils import (
    conform_to_schema_or_fail,
    get_first_or_fail,
)

#### PYDANTIC MODELS #####

from tests.models.admin import MediaCategoriesResponseModel, MediaCategoryCreatedResponseModel

##### FIXTURES #####


@pytest.fixture(scope="function")
def create_media_category(session):
    cat = MediaCategoryFactory()
    session.add(cat)
    session.commit()
    yield cat
    try:
        session.query(MediaCategory).filter(MediaCategory.id == cat.id).delete(
            synchronize_session=False
        )
        session.commit()
    except:
        pass


@pytest.fixture(scope="function")
def clean_slate_media_categories(session):
    session.query(MediaCategory).delete(synchronize_session=False)
    session.commit()
    yield


##### GET /admin/api/mediacategories #####

mediacategories_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", mediacategories_endpoint_roles)
def test_mediacategories_endpoint(
    clean_slate_media_categories, create_media_category, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get(
        "/admin/api/mediacategories",
        headers={"Content-Type": "application/json"},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        assert len(response.json["data"]["items"]) > 0
        conform_to_schema_or_fail(response.json, MediaCategoriesResponseModel)


##### POST /admin/api/mediacategory #####

post_mediacategory_endpoint_roles = [
    ("admin_client", 201),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_mediacategory_endpoint_roles)
def test_post_mediacategory_endpoint(
    clean_slate_media_categories, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    cat = MediaCategoryFactory()
    response = client_.post(
        "/admin/api/mediacategory",
        headers={"Content-Type": "application/json"},
        json={"item": cat.to_dict()},
    )
    assert response.status_code == expected_status
    found_cat = MediaCategory.query.filter(MediaCategory.title == cat.title).first()
    if expected_status == 201:
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), MediaCategoryCreatedResponseModel
        )
        assert found_cat
    else:
        assert found_cat is None


##### PUT /admin/api/mediacategory/<int:id> #####

put_mediacategory_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_mediacategory_endpoint_roles)
def test_put_mediacategory_endpoint(
    clean_slate_media_categories, create_media_category, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    new_cat = MediaCategoryFactory()
    cat = get_first_or_fail(MediaCategory)
    cat_id = cat.id
    new_cat.id = cat_id
    response = client_.put(
        f"/admin/api/mediacategory/{cat_id}",
        headers={"Content-Type": "application/json"},
        json={"item": new_cat.to_dict()},
    )
    assert response.status_code == expected_status
    found_cat = MediaCategory.query.filter(MediaCategory.id == cat_id).first()
    if expected_status == 200:
        assert found_cat.title == new_cat.title
    else:
        assert found_cat.title != new_cat.title


##### DELETE /admin/api/mediacategory/<int:id> #####

delete_mediacategory_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", delete_mediacategory_endpoint_roles)
def test_delete_mediacategory_endpoint(
    clean_slate_media_categories, create_media_category, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    cat = get_first_or_fail(MediaCategory)
    cat_id = cat.id
    response = client_.delete(
        f"/admin/api/mediacategory/{cat_id}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == expected_status
    found_cat = MediaCategory.query.filter(MediaCategory.id == cat_id).first()
    if expected_status == 200:
        assert found_cat is None
    else:
        assert found_cat
