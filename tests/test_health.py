def test_health_returns_ok(anonymous_client):
    resp = anonymous_client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert "version" in data


def test_health_is_exempt_from_rate_limit(anonymous_client):
    # 20 rapid requests should all succeed (limiter.exempt).
    for _ in range(20):
        resp = anonymous_client.get("/health")
        assert resp.status_code == 200
