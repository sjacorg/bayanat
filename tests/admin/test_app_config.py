import json
from unittest.mock import patch

import pytest

from enferno.admin.models import AppConfig
from enferno.admin.validation.models import FullConfigValidationModel
from enferno.utils.validation_utils import convert_empty_strings_to_none
from enferno.settings import TestConfig
from enferno.utils.config_utils import ConfigManager
from tests.factories import AppConfigFactory

##### PYDANTIC MODELS #####
from tests.models.admin import AppConfigsResponseModel
from tests.test_utils import (
    conform_to_schema_or_fail,
    get_uid_from_client,
)


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
    ("anonymous_client", 401),
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


##### GET /admin/api/configuration/ #####
@pytest.mark.parametrize("client_fixture, expected_status", appconfig_endpoint_roles)
def test_configuration(request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    with patch.object(ConfigManager, "serialize", return_value={"key": "value"}):
        response = client_.get(
            "/admin/api/configuration/", headers={"Content-Type": "application/json"}
        )
        assert response.status_code == expected_status


##### PUT /admin/api/configuration/ #####
@pytest.mark.parametrize("client_fixture, expected_status", appconfig_endpoint_roles)
def test_put_configuration(request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    updated_etl_vid_ext = ["mov", "mp4", "test"]

    with patch("enferno.settings.Config", TestConfig):
        current_conf = ConfigManager.serialize()
        if "LANGUAGES" in current_conf:
            current_conf.pop("LANGUAGES")
        updated_conf = {
            **current_conf,
            "ETL_VID_EXT": updated_etl_vid_ext,
        }
        with patch.object(ConfigManager, "write_config", return_value=True) as mock_write_config:
            response = client_.put(
                "/admin/api/configuration/",
                headers={"Content-Type": "application/json"},
                json={"conf": updated_conf},
            )
            assert response.status_code == expected_status
            if expected_status == 200:
                called_conf_write_argument = FullConfigValidationModel(
                    **convert_empty_strings_to_none(updated_conf)
                ).model_dump(by_alias=True)
                mock_write_config.assert_called_once_with(called_conf_write_argument)
