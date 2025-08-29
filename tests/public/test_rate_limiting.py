import pytest
from enferno.extensions import limiter


def test_csrf_rate_limiting(session, anonymous_client):
    """Test rate limiting on the CSRF endpoint."""
    # Clear any existing rate limit state
    limiter.reset()

    # Make 15 requests (within the per-minute limit)
    responses = []
    for _ in range(15):
        response = anonymous_client.get("/csrf")
        responses.append(response)

    # All should succeed with 200
    assert all(r.status_code == 200 for r in responses)

    # Make one more request (exceeding the limit)
    response = anonymous_client.get("/csrf")
    assert response.status_code == 429  # Too Many Requests
    # Verify error response format
    error_json = response.json
    assert error_json["error"] == "Too Many Requests"
    assert error_json["message"] == "15 per 1 minute"

    # Verify rate limit headers
    assert "Retry-After" in response.headers
    assert int(response.headers["Retry-After"]) > 0

    # Verify response format for successful requests
    for response in responses:
        assert "csrf_token" in response.json
        assert isinstance(response.json["csrf_token"], str)
