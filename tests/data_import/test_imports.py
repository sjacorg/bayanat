import os
import shutil
from sqlalchemy import select
from flask import current_app
import pytest
from unittest.mock import patch
from enferno.admin.validation.util import convert_empty_strings_to_none
from enferno.settings import TestConfig as cfg
from enferno.data_import.models import DataImport, Mapping
from enferno.user.models import Role, User
from tests.factories import DataImportFactory, MappingFactory, UserFactory
from tests.models.data_import import (
    CsvImportResponseModel,
    DataImportItemModel,
    DataImportResponseModel,
    MediaPathItemModel,
)
from tests.test_utils import (
    conform_to_schema_or_fail,
    create_csv_for_entities,
    create_xls_file,
    get_first_or_fail,
    load_data,
)

##### FIXTURES #####


@pytest.fixture(scope="function")
def create_import(session, users):
    import_ = DataImportFactory()
    import_.user = User.query.first()
    session.add(import_)
    session.commit()
    yield import_
    session.delete(import_)
    session.commit()


@pytest.fixture(scope="function")
def clean_slate_imports(session):
    session.query(DataImport).delete(synchronize_session=False)
    session.commit()
    yield


@pytest.fixture(scope="function")
def create_dummy_csv():
    headers = ["file", "file_format"]
    e1 = DataImportFactory()
    e2 = DataImportFactory()
    yield from create_csv_for_entities([e1, e2], headers)


@pytest.fixture(scope="function")
def create_upload_file():
    headers = ["file", "file_format"]
    e1 = DataImportFactory()
    e2 = DataImportFactory()
    for temp_file in create_csv_for_entities([e1, e2], headers):
        if not os.path.exists(cfg.IMPORT_DIR):
            os.makedirs(cfg.IMPORT_DIR)
        dest_file = os.path.join(cfg.IMPORT_DIR, os.path.basename(temp_file))
        shutil.copy(temp_file, dest_file)
        yield os.path.basename(dest_file)
        if os.path.exists(dest_file):
            os.remove(dest_file)


@pytest.fixture(scope="function")
def create_dummy_xls():
    data = {"Name": ["Alice", "Bob"], "Age": [25, 30], "City": ["New York", "Los Angeles"]}
    yield from create_xls_file(data)


@pytest.fixture(scope="function")
def create_upload_xls():
    data = {"Name": ["Alice", "Bob"], "Age": [25, 30], "City": ["New York", "Los Angeles"]}
    for temp_file in create_xls_file(data):
        if not os.path.exists(cfg.IMPORT_DIR):
            os.makedirs(cfg.IMPORT_DIR)
        dest_file = os.path.join(cfg.IMPORT_DIR, os.path.basename(temp_file))
        shutil.copy(temp_file, dest_file)
        yield os.path.basename(dest_file)
        if os.path.exists(dest_file):
            os.remove(dest_file)


@pytest.fixture(scope="function")
def create_mapping(session):
    mapping = MappingFactory()
    session.add(mapping)
    session.commit()
    yield mapping
    try:
        session.delete(mapping)
        session.commit()
    except:
        pass


@pytest.fixture(scope="function")
def create_mapping_for_user(request, session):
    def _create_mapping_for_user(uid):
        mapping = MappingFactory()
        mapping.user_id = uid
        session.add(mapping)
        session.commit()
        request.addfinalizer(lambda: session.delete(mapping))
        return mapping

    return _create_mapping_for_user


import_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]

##### GET /import/api/import/<int:id> #####


@pytest.mark.parametrize("client_fixture, expected_status", import_endpoint_roles)
def test_get_import_endpoint(
    request, clean_slate_imports, create_import, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    iid = create_import.id
    response = client_.get(
        f"/import/api/imports/{iid}", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        conform_to_schema_or_fail(
            convert_empty_strings_to_none(response.json["data"]), DataImportItemModel
        )


##### POST /import/api/imports #####


@pytest.mark.parametrize("client_fixture, expected_status", import_endpoint_roles)
def test_post_imports_endpoint(
    request, clean_slate_imports, create_import, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.post(
        "/import/api/imports/",
        headers={"Content-Type": "application/json"},
        json={"q": {}},
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        data = convert_empty_strings_to_none(response.json)
        assert data["data"]["total"] == 1
        assert len(data["data"]["items"]) == 1
        conform_to_schema_or_fail(data, DataImportResponseModel)


##### POST /import/media/path #####


@pytest.mark.parametrize("client_fixture, expected_status", import_endpoint_roles)
def test_post_media_path_endpoint(
    request, clean_slate_imports, create_import, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    with patch.dict(current_app.config, {"ETL_ALLOWED_PATH": ""}):
        response = client_.post(
            "/import/media/path/",
            headers={"Content-Type": "application/json"},
            json={"recursive": False, "path": ""},
        )
        assert response.status_code == expected_status
        if expected_status == 200:
            conform_to_schema_or_fail(
                convert_empty_strings_to_none(response.json)["data"][0], MediaPathItemModel
            )


##### POST /import/media/process #####


@pytest.mark.parametrize("client_fixture, expected_status", import_endpoint_roles)
def test_post_media_process_endpoint(
    request, clean_slate_imports, create_import, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    filenames = ["file1.txt", "file2.pdf", "file3.jpg"]
    files = [{"filename": filename for filename in filenames}]
    response = client_.post(
        "/import/media/process",
        headers={"Content-Type": "application/json"},
        json={"files": files},
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        assert response.text is not None


##### POST /import/api/csv/upload #####

import_csv_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", import_csv_endpoint_roles)
def test_post_csv_upload_endpoint(
    request, clean_slate_imports, create_dummy_csv, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    with open(create_dummy_csv, "rb") as f:
        data = {"file": (f, "test.csv")}
        response = client_.post(
            "/import/api/csv/upload",
            content_type="multipart/form-data",
            data=data,
            follow_redirects=True,
            headers={"Accept": "application/json"},
        )
        assert response.status_code == expected_status
        if expected_status == 200:
            conform_to_schema_or_fail(
                convert_empty_strings_to_none(response.json), CsvImportResponseModel
            )


##### POST /import/api/csv/analyze #####

import_csv_analyze_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", import_csv_analyze_endpoint_roles)
def test_post_csv_analyze_endpoint(
    request, clean_slate_imports, create_upload_file, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    file = create_upload_file
    response = client_.post("/import/api/csv/analyze", json={"file": {"filename": file}})
    assert response.status_code == expected_status


##### POST /import/api/xls/sheets #####


@pytest.mark.parametrize("client_fixture, expected_status", import_csv_analyze_endpoint_roles)
def test_post_xls_endpoint(
    request, clean_slate_imports, create_upload_xls, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.post(
        "/import/api/xls/sheets",
        content_type="application/json",
        json={"file": {"filename": create_upload_xls}},
        follow_redirects=True,
    )
    assert response.status_code == expected_status


##### POST /import/api/xls/analyze #####
@pytest.mark.parametrize("client_fixture, expected_status", import_csv_analyze_endpoint_roles)
def test_post_analyze_xls_endpoint(
    request, clean_slate_imports, create_upload_xls, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.post(
        "/import/api/xls/analyze",
        content_type="application/json",
        json={"file": {"filename": create_upload_xls}, "sheet": "Sheet1"},
        follow_redirects=True,
    )
    assert response.status_code == expected_status


##### POST /import/api/mapping #####


@pytest.mark.parametrize("client_fixture, expected_status", import_csv_analyze_endpoint_roles)
def test_post_mapping_endpoint(request, clean_slate_imports, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    response = client_.post(
        "/import/api/mapping",
        content_type="application/json",
        json={"name": "test", "data": {"test_key": "test_val"}},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        assert response.text is not None


##### PUT /import/api/mapping/<int:id> #####


@pytest.mark.parametrize("client_fixture, expected_status", import_csv_analyze_endpoint_roles)
def test_put_mapping_endpoint(request, clean_slate_imports, users, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    admin_user, _, _, _ = users

    # Create a mapping that belongs to the admin user
    mapping = MappingFactory()
    mapping.user_id = admin_user.id
    session = request.getfixturevalue("session")
    session.add(mapping)
    session.commit()

    map_dict = mapping.to_dict()
    response = client_.put(
        f"/import/api/mapping/{map_dict['id']}",
        content_type="application/json",
        json={"name": "new_name", "data": {"map": map_dict["data"]}},
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    found_map = Mapping.query.get(map_dict["id"]).to_dict()
    if expected_status == 200:
        assert found_map["name"] == "new_name"
    else:
        assert found_map["name"] != "new_name"


##### DELETE /import/api/mapping/<int:id> #####


@pytest.mark.parametrize("client_fixture, expected_status", import_csv_analyze_endpoint_roles)
def test_delete_mapping_endpoint(
    request, session, clean_slate_imports, users, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    admin_user, _, _, _ = users

    # Create a mapping that belongs to the admin user
    mapping = MappingFactory()
    mapping.user_id = admin_user.id
    session.add(mapping)
    session.commit()

    response = client_.delete(
        f"/import/api/mapping/{mapping.id}", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        assert session.get(Mapping, mapping.id) is None
    else:
        assert session.get(Mapping, mapping.id) is not None


different_admin_delete_mapping_endpoint_roles = [
    ("admin_client", 403),
    ("da_client", 403),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize(
    "client_fixture, expected_status", different_admin_delete_mapping_endpoint_roles
)
def test_delete_mapping_endpoint_for_another_user(
    request, session, clean_slate_imports, create_mapping_for_user, client_fixture, expected_status
):
    from uuid import uuid4

    client_ = request.getfixturevalue(client_fixture)
    new_admin = UserFactory()
    new_admin.fs_uniquifier = uuid4().hex  # Ensure unique identifier
    new_admin.roles.append(session.scalar(select(Role).where(Role.name == "Admin")))
    session.add(new_admin)
    session.commit()
    mapping = create_mapping_for_user(new_admin.id)
    response = client_.delete(
        f"/import/api/mapping/{mapping.id}", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == expected_status


##### POST /import/api/xls/process-sheet #####


@pytest.mark.parametrize("client_fixture, expected_status", import_csv_analyze_endpoint_roles)
def test_post_process_sheet_endpoint(
    request, clean_slate_imports, create_upload_xls, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    files = [create_upload_xls]
    map = {"name": "test_map", "data": {"test_key": "test_val"}}
    vmap = {}
    sheet = "Sheet1"
    actor_config = {}
    roles = []
    response = client_.post(
        "/import/api/process-sheet",
        content_type="application/json",
        json={
            "files": files,
            "map": map,
            "vmap": vmap,
            "sheet": sheet,
            "actorConfig": actor_config,
            "roles": roles,
        },
        follow_redirects=True,
    )
    assert response.status_code == expected_status
    if expected_status == 200:
        assert response.text is not None
