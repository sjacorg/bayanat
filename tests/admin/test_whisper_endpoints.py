import pytest
from enferno.admin.constants import Constants


get_whisper_models_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 302),
]


@pytest.mark.parametrize("client_fixture, expected_status", get_whisper_models_endpoint_roles)
def test_get_whisper_models_endpoint(request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get("/import/api/whisper/models/")
    assert response.status_code == expected_status
    if expected_status == 200:
        assert response.json["data"] == {"models": Constants.WHISPER_MODEL_OPTS}
    elif expected_status == 302:
        assert response.headers["Location"].startswith("/login")


get_whisper_languages_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 302),
]


@pytest.mark.parametrize("client_fixture, expected_status", get_whisper_languages_endpoint_roles)
def test_get_whisper_languages_endpoint(request, client_fixture, expected_status):
    # Skip test if whisper not available
    pytest.importorskip("whisper", reason="whisper not installed - run with AI extras")

    client_ = request.getfixturevalue(client_fixture)
    response = client_.get("/import/api/whisper/languages/")
    assert response.status_code == expected_status
    if expected_status == 200:
        assert "languages" in response.json["data"]
        assert len(response.json["data"]["languages"]) > 0
    elif expected_status == 302:
        assert response.headers["Location"].startswith("/login")
