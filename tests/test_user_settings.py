import pytest

from enferno.user.models import User


def _seed(session, user, settings):
    User.query.get(user.id).settings = settings
    session.commit()


def _saved(session, user):
    session.expire_all()
    return User.query.get(user.id).settings


def test_partial_save_keeps_saved_language(admin_client, session, users):
    _seed(session, users[0], {"language": "ar"})
    resp = admin_client.put("/settings/save", json={"settings": {"dark": True, "language": None}})
    assert resp.status_code == 200
    assert _saved(session, users[0]) == {"language": "ar", "dark": True}


@pytest.mark.parametrize("language", ["xx", ["ar"]])
def test_unsupported_language_is_ignored(admin_client, session, users, language):
    _seed(session, users[0], {"language": "ar"})
    resp = admin_client.put("/settings/save", json={"settings": {"language": language}})
    assert resp.status_code == 200
    assert _saved(session, users[0])["language"] == "ar"


@pytest.mark.parametrize("payload", [{"settings": "x"}, ["settings"]])
def test_malformed_payload_is_rejected(admin_client, payload):
    assert admin_client.put("/settings/save", json=payload).status_code == 400


def test_unknown_stored_language_falls_back_to_default(app, monkeypatch):
    from types import SimpleNamespace

    from enferno.app import get_locale

    user = SimpleNamespace(is_authenticated=True, settings={"language": "xx"})
    monkeypatch.setattr("enferno.app.current_user", user)
    with app.test_request_context("/"):
        assert get_locale() == app.config.get("BABEL_DEFAULT_LOCALE", "en")
