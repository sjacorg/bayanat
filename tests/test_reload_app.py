import os
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


@pytest.mark.parametrize("as_list", [False, True])
def test_touches_the_file_uwsgi_watches(fake_uwsgi, tmp_path, as_list):
    # uWSGI pre-creates the file; a reload fires only when its mtime moves
    target = tmp_path / "reload.ini"
    target.touch()
    os.utime(target, (0, 0))
    value = str(target).encode()
    fake_uwsgi.opt["touch-reload"] = [value] if as_list else value
    assert reload_app() is True
    assert target.stat().st_mtime > 0


def test_relative_path_resolves_against_working_directory(fake_uwsgi, tmp_path, monkeypatch):
    # Legacy layout: touch-reload=reload.ini with WorkingDirectory set to the release
    monkeypatch.chdir(tmp_path)
    fake_uwsgi.opt["touch-reload"] = b"reload.ini"
    assert reload_app() is True
    assert (tmp_path / "reload.ini").exists()


def test_unwritable_reload_file_reports_failure(fake_uwsgi, tmp_path):
    fake_uwsgi.opt["touch-reload"] = str(tmp_path / "missing-dir" / "reload.ini").encode()
    assert reload_app() is False


def test_no_touch_reload_configured(fake_uwsgi):
    assert reload_app() is False
