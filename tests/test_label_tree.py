import pytest

from enferno.admin.models import Label


@pytest.mark.parametrize(
    ("client_fixture", "expected_status"),
    [
        ("admin_client", 200),
        ("mod_client", 200),
        ("da_client", 200),
        ("roled_client", 403),
        ("anonymous_client", 302),
    ],
)
def test_label_tree_access_by_role(request, client_fixture, expected_status):
    client = request.getfixturevalue(client_fixture)

    response = client.get("/admin/api/labels/tree")

    assert response.status_code == expected_status
    if expected_status == 200:
        assert isinstance(response.json["data"]["items"], list)


def test_label_tree_includes_arabic_titles(admin_client, session):
    label = Label(title="Detention", title_ar="الاحتجاز")
    session.add(label)
    session.commit()
    label_id = label.id

    response = admin_client.get("/admin/api/labels/tree")

    assert response.status_code == 200
    item = next(item for item in response.json["data"]["items"] if item["id"] == label_id)
    assert item["title_ar"] == "الاحتجاز"


@pytest.mark.parametrize(
    ("client_fixture", "can_manage"),
    [
        ("admin_client", "true"),
        ("mod_client", "true"),
        ("da_client", "false"),
    ],
)
def test_label_navigator_is_rendered_for_label_assignment_roles(
    request, client_fixture, can_manage
):
    client = request.getfixturevalue(client_fixture)

    response = client.get("/", follow_redirects=True)

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "<label-structure-navigator" in html
    assert f':can-manage="{can_manage}"' in html


def test_label_navigator_is_hidden_from_other_roles(roled_client):
    response = roled_client.get("/", follow_redirects=True)

    assert response.status_code == 200
    assert "<label-structure-navigator" not in response.get_data(as_text=True)


def test_label_search_ranks_exact_match_before_descendants(admin_client, session):
    arms = Label(title="Arms", verified=True)
    session.add(arms)
    session.flush()
    session.add_all(
        Label(title=f"Weapons type {i}", parent_label_id=arms.id, verified=True) for i in range(150)
    )
    session.flush()
    weapons = Label(title="Weapons", verified=True)
    session.add(weapons)
    session.commit()

    response = admin_client.get("/admin/api/labels/?q=weapons&fltr=verified&per_page=100")

    assert response.status_code == 200
    assert response.json["data"]["items"][0]["id"] == weapons.id
    assert response.json["data"]["total"] == 151
