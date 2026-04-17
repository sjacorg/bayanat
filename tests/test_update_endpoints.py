import json
from unittest.mock import patch


def test_available_returns_cached(admin_client):
    from enferno.extensions import rds

    rds.set(
        "bayanat:update:available",
        json.dumps(
            {
                "latest": "4.1.1",
                "release_notes_url": "https://example.com",
                "checked_at": "2026-04-16T00:00:00+00:00",
            }
        ),
    )
    resp = admin_client.get("/admin/api/updates/available")
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["latest"] == "4.1.1"
    assert data["release_notes_url"] == "https://example.com"


def test_available_returns_empty_when_no_cache(admin_client):
    from enferno.extensions import rds

    rds.delete("bayanat:update:available")
    resp = admin_client.get("/admin/api/updates/available")
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["latest"] is None


def test_status_idle_when_no_state_file(admin_client, tmp_path, monkeypatch):
    monkeypatch.setattr(
        "enferno.admin.views.system.UPDATE_STATE_FILE",
        str(tmp_path / "missing.json"),
    )
    resp = admin_client.get("/admin/api/updates/status")
    assert resp.status_code == 200
    data = resp.get_json()["data"]
    assert data["phase"] == "IDLE"
    assert data["running"] is False


def test_status_running_when_midway(admin_client, tmp_path, monkeypatch):
    state = tmp_path / "update.json"
    state.write_text(json.dumps({"phase": "MIGRATE", "target": "4.1.1"}))
    monkeypatch.setattr("enferno.admin.views.system.UPDATE_STATE_FILE", str(state))
    resp = admin_client.get("/admin/api/updates/status")
    data = resp.get_json()["data"]
    assert data["phase"] == "MIGRATE"
    assert data["running"] is True


def test_status_terminal_when_success(admin_client, tmp_path, monkeypatch):
    state = tmp_path / "update.json"
    state.write_text(json.dumps({"phase": "SUCCESS", "target": "4.1.1"}))
    monkeypatch.setattr("enferno.admin.views.system.UPDATE_STATE_FILE", str(state))
    resp = admin_client.get("/admin/api/updates/status")
    data = resp.get_json()["data"]
    assert data["running"] is False


def test_start_calls_wrapper(admin_client):
    with patch("enferno.admin.views.system.subprocess.run") as run:
        resp = admin_client.post("/admin/api/updates/start")
        assert resp.status_code == 200
        run.assert_called_once()
        args = run.call_args.args[0]
        assert args == ["sudo", "-n", "/usr/local/sbin/bayanat-start-update"]


def test_non_admin_cannot_start(da_client):
    resp = da_client.post("/admin/api/updates/start")
    # roles_required returns 403 (Forbidden) for wrong-role users
    assert resp.status_code in (401, 403)
