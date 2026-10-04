import sys
import types

import pytest

from enferno.tasks.maintenance import reload_app


@pytest.fixture
def fake_uwsgi(monkeypatch):
    mod = types.ModuleType("uwsgi")
    mod.opt = {}
    monkeypatch.setitem(sys.modules, "uwsgi", mod)
    return mod


def test_touches_the_file_uwsgi_watches(fake_uwsgi, tmp_path):
    target = tmp_path / "reload.ini"
    fake_uwsgi.opt["touch-reload"] = str(target).encode()
    assert reload_app() is True
    assert target.exists()


def test_unwritable_reload_file_reports_failure(fake_uwsgi, tmp_path):
    fake_uwsgi.opt["touch-reload"] = str(tmp_path / "missing-dir" / "reload.ini").encode()
    assert reload_app() is False


def test_no_touch_reload_configured(fake_uwsgi):
    assert reload_app() is False
