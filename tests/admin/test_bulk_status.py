import pytest

##### GET /admin/api/bulk/status #####

bulk_status_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", bulk_status_endpoint_roles)
def test_bulk_status_endpoint(request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get("/admin/api/bulk/status/", headers={"Content-Type": "application/json"})
    assert response.status_code == expected_status
