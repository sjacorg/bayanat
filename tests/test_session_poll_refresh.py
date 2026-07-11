"""Verify the notification poll no longer slides the server-side session TTL.

A request carrying X-Silent-Poll must NOT refresh the session expiry, so an idle
user is eventually logged out. A normal request must still refresh it.
"""


def _session_key(app):
    client = app.session_interface.client
    keys = [k for k in client.keys() if b"session" in k or k.startswith(b"session:")]
    assert keys, f"no session key in store; keys={client.keys()}"
    return client, keys[0]


def test_silent_poll_does_not_refresh_ttl(app, admin_client):
    admin_client.get("/admin/api/notifications")
    client, key = _session_key(app)

    # Simulate idle time passing: 100s from expiring.
    client.expire(key, 100)
    assert client.ttl(key) <= 100

    # Background poll carries the silent header.
    resp = admin_client.get("/admin/api/notifications", headers={"X-Silent-Poll": "1"})
    assert resp.status_code == 200

    refreshed = client.ttl(key)
    print(f"\nTTL after silent poll (was forced to <=100): {refreshed}")
    assert refreshed <= 100, "silent poll still refreshed the session TTL"


def test_normal_request_still_refreshes_ttl(app, admin_client):
    admin_client.get("/admin/api/notifications")
    client, key = _session_key(app)

    client.expire(key, 100)
    assert client.ttl(key) <= 100

    # Normal (non-silent) request: a real user action.
    resp = admin_client.get("/admin/api/notifications")
    assert resp.status_code == 200

    refreshed = client.ttl(key)
    print(f"\nTTL after normal request (was forced to <=100): {refreshed}")
    assert refreshed > 100, "normal request should still refresh the session TTL"
