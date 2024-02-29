import pytest

from enferno.admin.models import AppConfig
from tests.factories import AppConfigFactory
from tests.test_utils import (
    conform_to_schema_or_fail,
    convert_empty_strings_to_none,
    get_uid_from_client,
)

##### PYDANTIC MODELS #####

from tests.models.admin import AppConfigsResponseModel

##### FIXTURES #####


@pytest.fixture(scope="function")
def create_appconfig(session):
    cfg = AppConfigFactory()
    session.add(cfg)
    session.commit()
    yield cfg
    session.delete(cfg)
    session.commit()


@pytest.fixture(scope="function")
def clean_slate_appconfigs(session):
    session.query(AppConfig).delete(synchronize_session=False)
    session.commit()
    yield


##### UTILITIES #####


def update_config_user(cid, uid):
    cfg = AppConfig.query.filter(AppConfig.id == cid).first()
    cfg.user_id = uid
    cfg.save()


##### GET /admin/api/appconfig/ #####

appconfig_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", appconfig_endpoint_roles)
def test_appconfig_endpoint(
    clean_slate_appconfigs, users, create_appconfig, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    uid = get_uid_from_client(users, client_fixture)
    update_config_user(create_appconfig.id, uid)
    response = client_.get("/admin/api/appconfig/", headers={"Content-Type": "application/json"})
    assert response.status_code == expected_status
    if expected_status == 200:
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json), AppConfigsResponseModel
        )
