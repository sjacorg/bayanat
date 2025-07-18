import pytest

from enferno.admin.models import Label
from enferno.utils.validation_utils import convert_empty_strings_to_none
from tests.factories import LabelFactory
from tests.test_utils import (
    conform_to_schema_or_fail,
    create_csv_for_entities,
    get_first_or_fail,
)

#### PYDANTIC MODELS #####

from tests.models.admin import LabelsResponseModel

##### FIXTURES #####


@pytest.fixture(scope="function")
def create_label(session, request):
    label_params = getattr(request, "param", {})
    label = LabelFactory(**label_params)
    session.add(label)
    session.commit()
    yield label
    try:
        session.query(Label).filter(Label.id == label.id).delete(synchronize_session=False)
        session.commit()
    except:
        pass


@pytest.fixture(scope="function")
def clean_slate_labels(session):
    session.query(Label).delete(synchronize_session=False)
    session.commit()
    yield


@pytest.fixture(scope="function")
def create_label_csv():
    l1 = LabelFactory()
    l2 = LabelFactory()
    headers = [
        "title",
        "for_actor",
        "for_bulletin",
        "for_incident",
        "for_offline",
        "verified",
        "order",
        "parent_label_id",
    ]
    yield from create_csv_for_entities([l1, l2], headers)


##### GET /admin/api/labels #####

labels_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", labels_endpoint_roles)
@pytest.mark.parametrize(
    "create_label",
    [{"verified": True, "for_actor": True}, {"for_bulletin": True}, {}],
    indirect=True,
)
def test_labels_endpoint(
    clean_slate_labels, create_label, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.get(
        "/admin/api/labels", headers={"Content-Type": "application/json"}, follow_redirects=True
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        if create_label.verified:
            assert len(response.json["items"]) == 0
            response = client_.get(
                "/admin/api/labels?fltr=all",
                headers={"Content-Type": "application/json"},
                follow_redirects=True,
            )
        label = response.json["items"][0]
        assert label
        if create_label.for_bulletin:
            assert label["for_bulletin"]
        if create_label.for_actor:
            assert label["for_actor"]
        conform_to_schema_or_fail(convert_empty_strings_to_none(response.json), LabelsResponseModel)


##### POST /admin/api/label #####

post_label_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_label_endpoint_roles)
def test_post_label_endpoint(clean_slate_labels, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    label = LabelFactory()
    item = label.to_dict()
    item.pop("id")
    item.pop("updated_at")
    response = client_.post(
        "/admin/api/label",
        headers={"Content-Type": "application/json"},
        json={"item": item},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        found_label = Label.query.filter(Label.title == label.title).first()
        assert found_label


##### PUT /admin/api/label/<int:id> #####

put_label_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 200),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", put_label_endpoint_roles)
def test_put_label_endpoint(
    clean_slate_labels, create_label, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    label = get_first_or_fail(Label)
    assert not label.verified
    item = label.to_dict()
    item["verified"] = True
    response = client_.put(
        f"/admin/api/label/{label.id}",
        headers={"Content-Type": "application/json"},
        json={"item": item},
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        found_label = Label.query.filter(Label.id == label.id).first()
        assert found_label.verified


##### DELETE /admin/api/label/<int:id> #####

delete_label_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", delete_label_endpoint_roles)
def test_delete_label_endpoint(
    clean_slate_labels, create_label, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    label = get_first_or_fail(Label)
    response = client_.delete(
        f"/admin/api/label/{label.id}",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == expected_status
    found_label = Label.query.filter(Label.id == label.id).first()
    if expected_status == 200:
        assert found_label is None
    else:
        assert found_label


##### POST /admin/api/label/import #####

import_label_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", import_label_endpoint_roles)
def test_import_label_endpoint(
    clean_slate_labels, create_label_csv, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    with open(create_label_csv, "rb") as f:
        data = {"csv": (f, "test.csv")}
        response = client_.post(
            "/admin/api/label/import",
            content_type="multipart/form-data",
            data=data,
            follow_redirects=True,
            headers={"Accept": "application/json"},
        )
        assert response.status_code == expected_status
        labels = Label.query.all()
        if expected_status == 200:
            assert len(labels) == 2
        else:
            assert len(labels) == 0
