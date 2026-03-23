"""
RBAC tests for specialized endpoints: relation infos, history, locations,
queries, activity, bulk status, whisper, media upload, data imports,
app config, configuration, notification settings, and the combined
relation info endpoint.
"""

import csv
import os
import random
import shutil
import tempfile
from io import BytesIO
from unittest.mock import patch

import pytest
from flask import current_app

from enferno.admin.models import (
    Activity,
    Actor,
    ActorHistory,
    AppConfig,
    AtoaInfo,
    AtobInfo,
    BtobInfo,
    Bulletin,
    BulletinHistory,
    ClaimedViolation,
    Eventtype,
    Incident,
    IncidentHistory,
    ItoaInfo,
    ItobInfo,
    ItoiInfo,
    Label,
    Location,
    LocationAdminLevel,
    LocationHistory,
    PotentialViolation,
    Query,
    Source,
)
from enferno.user.models import User
from tests.factories import (
    ActorFactory,
    ActorHistoryFactory,
    ActivityFactory,
    AppConfigFactory,
    AtoaInfoFactory,
    AtobInfoFactory,
    BtobInfoFactory,
    BulletinFactory,
    BulletinHistoryFactory,
    ClaimedViolationFactory,
    DataImportFactory,
    EventtypeFactory,
    IncidentFactory,
    IncidentHistoryFactory,
    ItoaInfoFactory,
    ItobInfoFactory,
    ItoiInfoFactory,
    LabelFactory,
    LocationAdminLevelFactory,
    LocationFactory,
    LocationHistoryFactory,
    MappingFactory,
    PotentialViolationFactory,
    QueryFactory,
    SourceFactory,
)

HEADERS = {"Content-Type": "application/json"}


# =========================================================================
# RELATION INFO CRUD (6 types)
# =========================================================================

_RELATION_INFO_TABLES = [
    ("atobinfos", "atobinfo", AtobInfo, AtobInfoFactory),
    ("btobinfos", "btobinfo", BtobInfo, BtobInfoFactory),
    ("atoainfos", "atoainfo", AtoaInfo, AtoaInfoFactory),
    ("itobinfos", "itobinfo", ItobInfo, ItobInfoFactory),
    ("itoainfos", "itoainfo", ItoaInfo, ItoaInfoFactory),
    ("itoiinfos", "itoiinfo", ItoiInfo, ItoiInfoFactory),
]


def _relinfo_list_params():
    roles = [
        ("admin_client", 200),
        ("da_client", 200),
        ("mod_client", 200),
        ("anonymous_client", 401),
    ]
    for list_slug, _, _, _ in _RELATION_INFO_TABLES:
        for client_fixture, status in roles:
            yield pytest.param(
                list_slug,
                client_fixture,
                status,
                id=f"list-{list_slug}-{client_fixture}",
            )


def _relinfo_create_params():
    roles = [
        ("admin_client", 201),
        ("da_client", 403),
        ("mod_client", 403),
        ("anonymous_client", 401),
    ]
    for _, single_slug, _, factory_cls in _RELATION_INFO_TABLES:
        for client_fixture, status in roles:
            yield pytest.param(
                single_slug,
                factory_cls,
                client_fixture,
                status,
                id=f"create-{single_slug}-{client_fixture}",
            )


def _relinfo_update_params():
    roles = [
        ("admin_client", 200),
        ("da_client", 403),
        ("mod_client", 403),
        ("anonymous_client", 401),
    ]
    for _, single_slug, model_cls, factory_cls in _RELATION_INFO_TABLES:
        for client_fixture, status in roles:
            yield pytest.param(
                single_slug,
                model_cls,
                factory_cls,
                client_fixture,
                status,
                id=f"update-{single_slug}-{client_fixture}",
            )


def _relinfo_delete_params():
    roles = [
        ("admin_client", 200),
        ("da_client", 403),
        ("mod_client", 403),
        ("anonymous_client", 401),
    ]
    for _, single_slug, model_cls, factory_cls in _RELATION_INFO_TABLES:
        for client_fixture, status in roles:
            yield pytest.param(
                single_slug,
                model_cls,
                factory_cls,
                client_fixture,
                status,
                id=f"delete-{single_slug}-{client_fixture}",
            )


class TestRelationInfoList:
    @pytest.mark.parametrize(
        "list_slug, client_fixture, expected",
        list(_relinfo_list_params()),
    )
    def test_list(self, request, session, list_slug, client_fixture, expected):
        client = request.getfixturevalue(client_fixture)
        resp = client.get(
            f"/admin/api/{list_slug}",
            headers=HEADERS,
            follow_redirects=True,
        )
        assert resp.status_code == expected


class TestRelationInfoCreate:
    @pytest.mark.parametrize(
        "single_slug, factory_cls, client_fixture, expected",
        list(_relinfo_create_params()),
    )
    def test_create(self, request, session, single_slug, factory_cls, client_fixture, expected):
        client = request.getfixturevalue(client_fixture)
        info = factory_cls()
        resp = client.post(
            f"/admin/api/{single_slug}",
            json={"item": info.to_dict()},
            headers=HEADERS,
        )
        assert resp.status_code == expected


class TestRelationInfoUpdate:
    @pytest.mark.parametrize(
        "single_slug, model_cls, factory_cls, client_fixture, expected",
        list(_relinfo_update_params()),
    )
    def test_update(
        self,
        request,
        session,
        single_slug,
        model_cls,
        factory_cls,
        client_fixture,
        expected,
    ):
        item = factory_cls()
        session.add(item)
        session.commit()
        new_item = factory_cls()
        client = request.getfixturevalue(client_fixture)
        resp = client.put(
            f"/admin/api/{single_slug}/{item.id}",
            json={"item": new_item.to_dict()},
            headers=HEADERS,
        )
        assert resp.status_code == expected


class TestRelationInfoDelete:
    @pytest.mark.parametrize(
        "single_slug, model_cls, factory_cls, client_fixture, expected",
        list(_relinfo_delete_params()),
    )
    def test_delete(
        self,
        request,
        session,
        single_slug,
        model_cls,
        factory_cls,
        client_fixture,
        expected,
    ):
        item = factory_cls()
        session.add(item)
        session.commit()
        client = request.getfixturevalue(client_fixture)
        resp = client.delete(
            f"/admin/api/{single_slug}/{item.id}",
            headers=HEADERS,
        )
        assert resp.status_code == expected


# =========================================================================
# HISTORY endpoints
# =========================================================================


class TestBulletinHistory:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 200),
            ("mod_client", 200),
            ("anonymous_client", 401),
        ],
    )
    def test_get_history(self, request, session, client_fixture, expected):
        b = BulletinFactory()
        session.add(b)
        session.commit()
        h = BulletinHistoryFactory()
        h.bulletin_id = b.id
        h.bulletin = b
        session.add(h)
        session.commit()
        client = request.getfixturevalue(client_fixture)
        resp = client.get(
            f"/admin/api/bulletinhistory/{h.id}",
            headers=HEADERS,
        )
        assert resp.status_code == expected


class TestActorHistory:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 200),
            ("mod_client", 200),
            ("anonymous_client", 401),
        ],
    )
    def test_get_history(self, request, session, client_fixture, expected):
        a = ActorFactory()
        session.add(a)
        session.commit()
        h = ActorHistoryFactory()
        h.actor_id = a.id
        h.actor = a
        session.add(h)
        session.commit()
        client = request.getfixturevalue(client_fixture)
        resp = client.get(
            f"/admin/api/actorhistory/{h.id}",
            headers=HEADERS,
        )
        assert resp.status_code == expected


class TestIncidentHistory:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 200),
            ("mod_client", 200),
            ("anonymous_client", 401),
        ],
    )
    def test_get_history(self, request, session, client_fixture, expected):
        i = IncidentFactory()
        session.add(i)
        session.commit()
        h = IncidentHistoryFactory()
        h.incident_id = i.id
        h.incident = i
        session.add(h)
        session.commit()
        client = request.getfixturevalue(client_fixture)
        resp = client.get(
            f"/admin/api/incidenthistory/{h.id}",
            headers=HEADERS,
        )
        assert resp.status_code == expected


class TestLocationHistory:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 200),
            ("mod_client", 200),
            ("anonymous_client", 401),
        ],
    )
    def test_get_history(self, request, session, client_fixture, expected):
        loc = LocationFactory()
        session.add(loc)
        session.commit()
        h = LocationHistoryFactory()
        h.location_id = loc.id
        h.location = loc
        session.add(h)
        session.commit()
        client = request.getfixturevalue(client_fixture)
        resp = client.get(
            f"/admin/api/locationhistory/{h.id}",
            headers=HEADERS,
        )
        assert resp.status_code == expected


# =========================================================================
# LOCATIONS
# =========================================================================


class TestLocationCreate:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 201),
            ("da_client", 403),
            ("mod_client", 201),
            ("anonymous_client", 401),
        ],
    )
    def test_create(self, request, session, client_fixture, expected):
        from enferno.admin.models import LocationType

        loc_type = LocationType(title="Point of Interest")
        session.add(loc_type)
        session.commit()
        loc = LocationFactory()
        loc.location_type = loc_type
        item = loc.to_dict()
        client = request.getfixturevalue(client_fixture)
        resp = client.post(
            "/admin/api/location",
            json={"item": item},
            headers=HEADERS,
            follow_redirects=True,
        )
        assert resp.status_code == expected


class TestLocationList:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 200),
            ("mod_client", 200),
            ("anonymous_client", 401),
        ],
    )
    def test_list(self, request, session, client_fixture, expected):
        loc = LocationFactory()
        session.add(loc)
        session.commit()
        client = request.getfixturevalue(client_fixture)
        resp = client.get(
            "/admin/api/locations",
            json={"q": {}, "options": {}},
            headers=HEADERS,
            follow_redirects=True,
        )
        assert resp.status_code == expected


class TestLocationUpdate:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 200),
            ("anonymous_client", 401),
        ],
    )
    def test_update(self, request, session, client_fixture, expected):
        from enferno.admin.models import LocationType

        loc_type = LocationType(title="Point of Interest")
        session.add(loc_type)
        session.commit()
        loc = LocationFactory()
        session.add(loc)
        session.commit()
        item = loc.to_dict()
        item["title"] = "Updated location"
        item["location_type"] = loc_type.to_dict()
        client = request.getfixturevalue(client_fixture)
        resp = client.put(
            f"/admin/api/location/{loc.id}",
            json={"item": item},
            headers=HEADERS,
        )
        assert resp.status_code == expected


# =========================================================================
# QUERIES
# =========================================================================


class TestQueryCreate:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 201),
            ("da_client", 201),
            ("mod_client", 201),
            ("anonymous_client", 401),
        ],
    )
    def test_create(self, request, session, client_fixture, expected):
        q = QueryFactory()
        client = request.getfixturevalue(client_fixture)
        resp = client.post(
            "/admin/api/query/",
            json={"q": {"key": "val"}, "type": q.query_type, "name": q.name},
            headers=HEADERS,
        )
        assert resp.status_code == expected


class TestQueryList:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 200),
            ("mod_client", 200),
            ("anonymous_client", 401),
        ],
    )
    def test_list(self, request, session, users, client_fixture, expected):
        q = QueryFactory()
        admin_user, _, _, _ = users
        q.user_id = admin_user.id
        session.add(q)
        session.commit()
        client = request.getfixturevalue(client_fixture)
        resp = client.get(
            f"/admin/api/queries/?type={q.query_type}",
            headers=HEADERS,
        )
        assert resp.status_code == expected


class TestQueryUpdate:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 200),
            ("mod_client", 200),
            ("anonymous_client", 401),
        ],
    )
    def test_update(self, request, session, users, client_fixture, expected):
        q = QueryFactory()
        admin_user, da_user, mod_user, _ = users
        # Assign query to requesting user so ownership check passes
        uid = None
        if client_fixture == "admin_client":
            uid = admin_user.id
        elif client_fixture == "da_client":
            uid = da_user.id
        elif client_fixture == "mod_client":
            uid = mod_user.id
        if uid:
            q.user_id = uid
        session.add(q)
        session.commit()
        client = request.getfixturevalue(client_fixture)
        resp = client.put(
            f"/admin/api/query/{q.id}",
            json={"q": {"new_key": "new_val"}},
            headers=HEADERS,
        )
        assert resp.status_code == expected


class TestQueryDelete:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 200),
            ("mod_client", 200),
            ("anonymous_client", 401),
        ],
    )
    def test_delete(self, request, session, users, client_fixture, expected):
        q = QueryFactory()
        admin_user, da_user, mod_user, _ = users
        uid = None
        if client_fixture == "admin_client":
            uid = admin_user.id
        elif client_fixture == "da_client":
            uid = da_user.id
        elif client_fixture == "mod_client":
            uid = mod_user.id
        if uid:
            q.user_id = uid
        session.add(q)
        session.commit()
        client = request.getfixturevalue(client_fixture)
        resp = client.delete(
            f"/admin/api/query/{q.id}",
            headers=HEADERS,
        )
        assert resp.status_code == expected


# =========================================================================
# ACTIVITY (admin only)
# =========================================================================


class TestActivity:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_list(self, request, session, users, client_fixture, expected):
        admin_user, _, _, _ = users
        act = ActivityFactory()
        act.user_id = admin_user.id
        session.add(act)
        session.commit()
        client = request.getfixturevalue(client_fixture)
        resp = client.get(
            "/admin/api/activities/",
            json={"q": {}, "options": {}},
            headers=HEADERS,
        )
        assert resp.status_code == expected


# =========================================================================
# BULK STATUS
# =========================================================================


class TestBulkStatus:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 200),
            ("anonymous_client", 401),
        ],
    )
    def test_bulk_status(self, request, session, client_fixture, expected):
        client = request.getfixturevalue(client_fixture)
        resp = client.get(
            "/admin/api/bulk/status/?type=bulletin",
            headers=HEADERS,
        )
        assert resp.status_code == expected


# =========================================================================
# WHISPER
# =========================================================================


class TestWhisperModels:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 302),
        ],
    )
    def test_models(self, request, session, client_fixture, expected):
        client = request.getfixturevalue(client_fixture)
        resp = client.get("/import/api/whisper/models/")
        assert resp.status_code == expected


class TestWhisperLanguages:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 302),
        ],
    )
    def test_languages(self, request, session, client_fixture, expected):
        pytest.importorskip("whisper", reason="whisper not installed")
        client = request.getfixturevalue(client_fixture)
        resp = client.get("/import/api/whisper/languages/")
        assert resp.status_code == expected


# =========================================================================
# MEDIA UPLOAD
# =========================================================================

ALLOWED_EXTS = ["jpg", "mp4", "doc"]


class TestMediaChunkUpload:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 200),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_chunk_upload(self, request, session, app, client_fixture, expected):
        ext = random.choice(ALLOWED_EXTS)
        content = b"Test file content for upload"
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=f".{ext}") as tmp:
            tmp.write(content)
            tmp.flush()
            tmp_path = tmp.name

        try:
            file_size = os.path.getsize(tmp_path)
            with open(tmp_path, "rb") as f:
                data = {
                    "file": (f, f"test.{ext}"),
                    "dzuuid": "test-uuid",
                    "dzchunkindex": "0",
                    "dztotalchunkcount": "1",
                    "dztotalfilesize": str(file_size),
                }
                client = request.getfixturevalue(client_fixture)
                with patch.dict(
                    current_app.config,
                    {"MEDIA_ALLOWED_EXTENSIONS": ALLOWED_EXTS},
                ):
                    resp = client.post(
                        "/admin/api/media/chunk",
                        content_type="multipart/form-data",
                        data=data,
                        headers={"Referer": "", "Accept": "application/json"},
                    )
                assert resp.status_code == expected
                if expected == 200:
                    media_dir = "enferno/media"
                    for fname in os.listdir(media_dir):
                        if fname.endswith(f"test.{ext}"):
                            os.remove(os.path.join(media_dir, fname))
                            break
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


# =========================================================================
# DATA IMPORTS
# =========================================================================


class TestDataImports:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_post_imports(self, request, session, users, client_fixture, expected):
        from enferno.data_import.models import DataImport

        admin_user, _, _, _ = users
        di = DataImport(
            table="bulletin",
            item_id=1,
            file="test.csv",
            file_format="csv",
            file_hash="abc123",
            batch_id="batch1",
            status="Pending",
            data={"key": "val"},
        )
        di.user = admin_user
        session.add(di)
        session.commit()
        client = request.getfixturevalue(client_fixture)
        resp = client.post(
            "/import/api/imports/",
            json={"q": {}},
            headers=HEADERS,
        )
        assert resp.status_code == expected


# =========================================================================
# COMBINED RELATION INFO ENDPOINT
# =========================================================================


class TestRelationInfoEndpoint:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 200),
            ("mod_client", 200),
            ("anonymous_client", 401),
        ],
    )
    def test_relation_info(self, request, session, client_fixture, expected):
        # Create one of each relation info type
        for factory_cls in [
            AtobInfoFactory,
            BtobInfoFactory,
            AtoaInfoFactory,
            ItobInfoFactory,
            ItoaInfoFactory,
            ItoiInfoFactory,
        ]:
            item = factory_cls()
            session.add(item)
        session.commit()
        client = request.getfixturevalue(client_fixture)
        resp = client.get(
            "/admin/api/relation/info",
            headers=HEADERS,
        )
        assert resp.status_code == expected


# =========================================================================
# LOCATION IMPORT
# =========================================================================


class TestLocationImport:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_import(self, request, session, client_fixture, expected):
        import csv

        # Use high IDs to avoid conflicts with default data.
        # Note: Location.import_csv uses to_sql(engine) which bypasses the
        # savepoint, so we must clean up manually after success.
        loc_ids = [99990, 99991]

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as tmp:
            writer = csv.writer(tmp)
            writer.writerow(["id", "title", "title_ar", "parent_id", "deleted"])
            for lid in loc_ids:
                writer.writerow([lid, f"ImportLoc{lid}", f"ImportLocAr{lid}", "", "False"])
            tmp.flush()
            csv_path = tmp.name

        try:
            with open(csv_path, "rb") as f:
                client = request.getfixturevalue(client_fixture)
                resp = client.post(
                    "/admin/api/location/import/",
                    content_type="multipart/form-data",
                    data={"csv": (f, "test.csv")},
                    follow_redirects=True,
                    headers={"Accept": "application/json"},
                )
            assert resp.status_code == expected
        finally:
            os.unlink(csv_path)
            # Clean up rows written directly to DB (bypasses savepoint)
            if expected == 200:
                from sqlalchemy import text

                with session.get_bind().connect() as conn:
                    conn.execute(
                        text("DELETE FROM location WHERE id IN :ids"), {"ids": tuple(loc_ids)}
                    )
                    conn.commit()


# =========================================================================
# MEDIA UPLOAD (single file)
# =========================================================================


class TestMediaUpload:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 200),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_upload(self, request, session, app, client_fixture, expected):
        ext = random.choice(ALLOWED_EXTS)
        content = b"Test file content for upload"
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=f".{ext}") as tmp:
            tmp.write(content)
            tmp.flush()
            tmp_path = tmp.name

        try:
            with open(tmp_path, "rb") as f:
                client = request.getfixturevalue(client_fixture)
                with patch.dict(
                    current_app.config,
                    {"MEDIA_ALLOWED_EXTENSIONS": ALLOWED_EXTS},
                ):
                    resp = client.post(
                        "/admin/api/media/upload/",
                        content_type="multipart/form-data",
                        data={"file": (f, f"test.{ext}")},
                        headers={"Accept": "application/json"},
                    )
                assert resp.status_code == expected
                if expected == 200:
                    media_dir = "enferno/media"
                    for fname in os.listdir(media_dir):
                        if fname.endswith(f"test.{ext}"):
                            os.remove(os.path.join(media_dir, fname))
                            break
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


# =========================================================================
# MEDIA CHUNKED UPLOAD (multi-chunk)
# =========================================================================


class TestMediaChunkedUpload:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 200),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_chunked_upload(self, request, session, app, client_fixture, expected):
        ext = random.choice(ALLOWED_EXTS)
        content = b"A" * 500  # large enough to split into chunks
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, suffix=f".{ext}") as tmp:
            tmp.write(content)
            tmp.flush()
            tmp_path = tmp.name

        try:
            file_size = os.path.getsize(tmp_path)
            total_chunks = 5
            chunk_size = file_size // total_chunks
            dzuuid = "test-chunked-uuid"

            for chunk_index in range(total_chunks):
                with open(tmp_path, "rb") as f:
                    f.seek(chunk_index * chunk_size)
                    if chunk_index == total_chunks - 1:
                        chunk_data = f.read()  # read remainder
                    else:
                        chunk_data = f.read(chunk_size)

                from werkzeug.datastructures import FileStorage

                data = {
                    "file": FileStorage(stream=BytesIO(chunk_data), filename=f"test-chunk.{ext}"),
                    "dzuuid": dzuuid,
                    "dzchunkindex": str(chunk_index),
                    "dztotalchunkcount": str(total_chunks),
                    "dztotalfilesize": str(file_size),
                }
                client = request.getfixturevalue(client_fixture)
                with patch.dict(
                    current_app.config,
                    {"MEDIA_ALLOWED_EXTENSIONS": ALLOWED_EXTS},
                ):
                    resp = client.post(
                        "/admin/api/media/chunk",
                        content_type="multipart/form-data",
                        data=data,
                        headers={"Referer": "", "Accept": "application/json"},
                    )
                assert resp.status_code == expected

                if chunk_index == total_chunks - 1 and expected == 200:
                    media_dir = "enferno/media"
                    for fname in os.listdir(media_dir):
                        if fname.endswith(f"test-chunk.{ext}"):
                            final_path = os.path.join(media_dir, fname)
                            assert os.path.getsize(final_path) == file_size
                            os.remove(final_path)
                            break
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


# =========================================================================
# APPCONFIG
# =========================================================================


class TestAppConfig:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_get_appconfig(self, request, session, users, client_fixture, expected):
        admin_user, _, _, _ = users
        cfg = AppConfigFactory()
        cfg.user_id = admin_user.id
        session.add(cfg)
        session.commit()
        client = request.getfixturevalue(client_fixture)
        resp = client.get("/admin/api/appconfig/", headers=HEADERS)
        assert resp.status_code == expected


# =========================================================================
# CONFIGURATION (GET and PUT)
# =========================================================================


class TestConfiguration:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_get_configuration(self, request, session, client_fixture, expected):
        from enferno.utils.config_utils import ConfigManager

        client = request.getfixturevalue(client_fixture)
        with patch.object(ConfigManager, "serialize", return_value={"key": "value"}):
            resp = client.get("/admin/api/configuration/", headers=HEADERS)
            assert resp.status_code == expected

    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_put_configuration(self, request, session, client_fixture, expected):
        from enferno.settings import TestConfig
        from enferno.utils.config_utils import ConfigManager

        updated_etl_vid_ext = ["mov", "mp4", "test"]
        with patch("enferno.settings.Config", TestConfig):
            current_conf = ConfigManager.serialize()
            if "LANGUAGES" in current_conf:
                current_conf.pop("LANGUAGES")
            updated_conf = {
                **current_conf,
                "ETL_VID_EXT": updated_etl_vid_ext,
                "YTDLP_COOKIES": "domain\tflag\tpath\tsecure\texpiry\tname\tvalue",
                "YTDLP_PROXY": "socks5://localhost:9050",
            }
            with patch.object(ConfigManager, "write_config", return_value=True) as mock_write:
                client = request.getfixturevalue(client_fixture)
                resp = client.put(
                    "/admin/api/configuration/",
                    json={"conf": updated_conf},
                    headers=HEADERS,
                )
                assert resp.status_code == expected
                if expected == 200:
                    mock_write.assert_called_once()
                    called_conf = mock_write.call_args[0][0]
                    assert called_conf["ETL_VID_EXT"] == updated_etl_vid_ext


# =========================================================================
# NOTIFICATION SETTINGS
# =========================================================================


class TestNotificationSettings:
    def test_get_config_security_events_enforced(self, app):
        from enferno.admin.models.Notification import get_notification_config

        with app.app_context():
            security_events = [
                "LOGIN_NEW_IP",
                "PASSWORD_CHANGE",
                "TWO_FACTOR_CHANGE",
                "RECOVERY_CODES_CHANGE",
                "FORCE_PASSWORD_CHANGE",
            ]
            for event in security_events:
                config = get_notification_config(event)
                assert config["enabled"] is True
                assert config["email"] is True

    def test_config_excludes_security_events(self, request, session):
        client = request.getfixturevalue("admin_client")
        resp = client.get("/admin/api/configuration/")
        current_configuration = resp.json["data"]["config"]
        notifications = current_configuration["NOTIFICATIONS"]
        security_events = [
            "LOGIN_NEW_IP",
            "PASSWORD_CHANGE",
            "TWO_FACTOR_CHANGE",
            "RECOVERY_CODES_CHANGE",
            "FORCE_PASSWORD_CHANGE",
        ]
        for event in security_events:
            assert event not in notifications

    def test_put_config_notification_update(self, request, session):
        import json as json_mod

        client = request.getfixturevalue("admin_client")
        temp = tempfile.NamedTemporaryFile(mode="w", delete=False)
        try:
            json_mod.dump({}, temp)
            temp.close()
            with patch("enferno.utils.config_utils.ConfigManager.CONFIG_FILE_PATH", temp.name):
                resp = client.get("/admin/api/configuration/")
                current_config = resp.json["data"]["config"]
                current_config["NOTIFICATIONS"]["NEW_BATCH"] = {
                    "in_app_enabled": True,
                    "email_enabled": True,
                    "category": "update",
                }
                resp = client.put("/admin/api/configuration/", json={"conf": current_config})
                assert resp.status_code == 200
                with open(temp.name, "r") as f:
                    updated = json_mod.load(f)
                assert updated["NOTIFICATIONS"]["NEW_BATCH"]["in_app_enabled"] is True
                assert updated["NOTIFICATIONS"]["NEW_BATCH"]["email_enabled"] is True
        finally:
            os.unlink(temp.name)


# =========================================================================
# LOCATION GET BY ID
# =========================================================================


class TestLocationGetById:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 200),
            ("mod_client", 200),
            ("anonymous_client", 401),
        ],
    )
    def test_get_location(self, request, session, client_fixture, expected):
        loc = LocationFactory()
        session.add(loc)
        session.commit()
        client = request.getfixturevalue(client_fixture)
        resp = client.get(
            f"/admin/api/location/{loc.id}",
            headers={"Accept": "application/json"},
        )
        assert resp.status_code == expected


# =========================================================================
# LOCATION REGENERATE
# =========================================================================


class TestLocationRegenerate:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_regenerate(self, request, session, client_fixture, expected):
        from enferno.tasks import regenerate_locations

        with patch.object(regenerate_locations, "delay") as mock_delay:
            client = request.getfixturevalue(client_fixture)
            resp = client.post(
                "/admin/api/location/regenerate/",
                headers={"Accept": "application/json"},
            )
            assert resp.status_code == expected
            if expected == 200:
                mock_delay.assert_called_once()
            else:
                mock_delay.assert_not_called()


# =========================================================================
# QUERY EXISTS
# =========================================================================


class TestQueryExists:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 200),
            ("mod_client", 200),
            ("anonymous_client", 401),
        ],
    )
    def test_query_exists(self, request, session, users, client_fixture, expected):
        q = QueryFactory()
        admin_user, da_user, mod_user, _ = users
        uid = None
        if client_fixture == "admin_client":
            uid = admin_user.id
        elif client_fixture == "da_client":
            uid = da_user.id
        elif client_fixture == "mod_client":
            uid = mod_user.id
        if uid:
            q.user_id = uid
        session.add(q)
        session.commit()

        client = request.getfixturevalue(client_fixture)
        # Non-existing name should return expected status
        fresh = QueryFactory()
        resp = client.get(f"/admin/api/query/{fresh.name}/exists", headers=HEADERS)
        assert resp.status_code == expected

        if expected == 200:
            # Existing name should return 409
            resp = client.get(f"/admin/api/query/{q.name}/exists", headers=HEADERS)
            assert resp.status_code == 409


# =========================================================================
# DATA IMPORT DETAIL: GET /import/api/imports/{id}
# =========================================================================


class TestDataImportDetail:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_get_import(self, request, session, users, client_fixture, expected):
        from enferno.data_import.models import DataImport

        admin_user, _, _, _ = users
        di = DataImport(
            table="bulletin",
            item_id=1,
            file="test.csv",
            file_format="csv",
            file_hash="abc123detail",
            batch_id="batch_detail",
            status="Pending",
            data={"key": "val"},
        )
        di.user = admin_user
        session.add(di)
        session.commit()

        client = request.getfixturevalue(client_fixture)
        resp = client.get(f"/import/api/imports/{di.id}", headers=HEADERS)
        assert resp.status_code == expected


# =========================================================================
# POST /import/media/path/ and POST /import/media/process
# =========================================================================


class TestMediaPath:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_post_media_path(self, request, session, client_fixture, expected):
        client = request.getfixturevalue(client_fixture)
        with patch.dict(current_app.config, {"ETL_ALLOWED_PATH": ""}):
            resp = client.post(
                "/import/media/path/",
                json={"recursive": False, "path": ""},
                headers=HEADERS,
            )
            assert resp.status_code == expected


class TestMediaProcess:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_post_media_process(self, request, session, client_fixture, expected):
        filenames = ["file1.txt", "file2.pdf", "file3.jpg"]
        files = [{"filename": fn} for fn in filenames]
        client = request.getfixturevalue(client_fixture)
        resp = client.post(
            "/import/media/process",
            json={"files": files},
            headers=HEADERS,
        )
        assert resp.status_code == expected


# =========================================================================
# CSV UPLOAD + ANALYZE
# =========================================================================


class TestCsvUpload:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_csv_upload(self, request, session, client_fixture, expected):
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as tmp:
            writer = csv.writer(tmp)
            writer.writerow(["file", "file_format"])
            writer.writerow(["test.csv", "csv"])
            writer.writerow(["test2.csv", "csv"])
            tmp.flush()
            csv_path = tmp.name

        try:
            with open(csv_path, "rb") as f:
                client = request.getfixturevalue(client_fixture)
                resp = client.post(
                    "/import/api/csv/upload",
                    content_type="multipart/form-data",
                    data={"file": (f, "test.csv")},
                    follow_redirects=True,
                    headers={"Accept": "application/json"},
                )
                assert resp.status_code == expected
        finally:
            os.unlink(csv_path)


class TestCsvAnalyze:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_csv_analyze(self, request, session, client_fixture, expected):
        from enferno.settings import TestConfig as cfg

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as tmp:
            writer = csv.writer(tmp)
            writer.writerow(["file", "file_format"])
            writer.writerow(["test.csv", "csv"])
            tmp.flush()
            csv_path = tmp.name

        try:
            if not os.path.exists(cfg.IMPORT_DIR):
                os.makedirs(cfg.IMPORT_DIR)
            dest = os.path.join(cfg.IMPORT_DIR, os.path.basename(csv_path))
            shutil.copy(csv_path, dest)

            client = request.getfixturevalue(client_fixture)
            resp = client.post(
                "/import/api/csv/analyze",
                json={"file": {"filename": os.path.basename(dest)}},
            )
            assert resp.status_code == expected
        finally:
            os.unlink(csv_path)
            if os.path.exists(dest):
                os.unlink(dest)


# =========================================================================
# XLS UPLOAD + ANALYZE + PROCESS-SHEET
# =========================================================================


class TestXlsSheets:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_xls_sheets(self, request, session, client_fixture, expected):
        import pandas as pd
        from enferno.settings import TestConfig as cfg

        df = pd.DataFrame({"Name": ["Alice", "Bob"], "Age": [25, 30], "City": ["NY", "LA"]})
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".xlsx") as tmp:
            df.to_excel(tmp.name, index=False)
            xls_path = tmp.name

        try:
            if not os.path.exists(cfg.IMPORT_DIR):
                os.makedirs(cfg.IMPORT_DIR)
            dest = os.path.join(cfg.IMPORT_DIR, os.path.basename(xls_path))
            shutil.copy(xls_path, dest)

            client = request.getfixturevalue(client_fixture)
            resp = client.post(
                "/import/api/xls/sheets",
                json={"file": {"filename": os.path.basename(dest)}},
                headers=HEADERS,
                follow_redirects=True,
            )
            assert resp.status_code == expected
        finally:
            os.unlink(xls_path)
            if os.path.exists(dest):
                os.unlink(dest)


class TestXlsAnalyze:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_xls_analyze(self, request, session, client_fixture, expected):
        import pandas as pd
        from enferno.settings import TestConfig as cfg

        df = pd.DataFrame({"Name": ["Alice", "Bob"], "Age": [25, 30], "City": ["NY", "LA"]})
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".xlsx") as tmp:
            df.to_excel(tmp.name, index=False)
            xls_path = tmp.name

        try:
            if not os.path.exists(cfg.IMPORT_DIR):
                os.makedirs(cfg.IMPORT_DIR)
            dest = os.path.join(cfg.IMPORT_DIR, os.path.basename(xls_path))
            shutil.copy(xls_path, dest)

            client = request.getfixturevalue(client_fixture)
            resp = client.post(
                "/import/api/xls/analyze",
                json={
                    "file": {"filename": os.path.basename(dest)},
                    "sheet": "Sheet1",
                },
                headers=HEADERS,
                follow_redirects=True,
            )
            assert resp.status_code == expected
        finally:
            os.unlink(xls_path)
            if os.path.exists(dest):
                os.unlink(dest)


class TestProcessSheet:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_process_sheet(self, request, session, client_fixture, expected):
        import pandas as pd
        from enferno.settings import TestConfig as cfg

        df = pd.DataFrame({"Name": ["Alice", "Bob"], "Age": [25, 30], "City": ["NY", "LA"]})
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".xlsx") as tmp:
            df.to_excel(tmp.name, index=False)
            xls_path = tmp.name

        try:
            if not os.path.exists(cfg.IMPORT_DIR):
                os.makedirs(cfg.IMPORT_DIR)
            dest = os.path.join(cfg.IMPORT_DIR, os.path.basename(xls_path))
            shutil.copy(xls_path, dest)

            client = request.getfixturevalue(client_fixture)
            resp = client.post(
                "/import/api/process-sheet",
                json={
                    "files": [os.path.basename(dest)],
                    "map": {"name": "test_map", "data": {"test_key": "test_val"}},
                    "vmap": {},
                    "sheet": "Sheet1",
                    "actorConfig": {},
                    "roles": [],
                },
                headers=HEADERS,
                follow_redirects=True,
            )
            assert resp.status_code == expected
        finally:
            os.unlink(xls_path)
            if os.path.exists(dest):
                os.unlink(dest)


# =========================================================================
# MAPPING CRUD
# =========================================================================


class TestMappingCreate:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_create_mapping(self, request, session, client_fixture, expected):
        client = request.getfixturevalue(client_fixture)
        resp = client.post(
            "/import/api/mapping",
            json={"name": "test", "data": {"test_key": "test_val"}},
            headers=HEADERS,
            follow_redirects=True,
        )
        assert resp.status_code == expected


class TestMappingUpdate:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_update_mapping(self, request, session, users, client_fixture, expected):
        from enferno.data_import.models import Mapping

        admin_user, _, _, _ = users
        mapping = MappingFactory()
        mapping.user_id = admin_user.id
        session.add(mapping)
        session.commit()

        client = request.getfixturevalue(client_fixture)
        resp = client.put(
            f"/import/api/mapping/{mapping.id}",
            json={"name": "new_name", "data": {"map": mapping.to_dict()["data"]}},
            headers=HEADERS,
            follow_redirects=True,
        )
        assert resp.status_code == expected
        found = Mapping.query.get(mapping.id)
        if expected == 200:
            assert found.name == "new_name"
        else:
            assert found.name != "new_name"


class TestMappingDelete:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_delete_mapping(self, request, session, users, client_fixture, expected):
        from enferno.data_import.models import Mapping

        admin_user, _, _, _ = users
        mapping = MappingFactory()
        mapping.user_id = admin_user.id
        session.add(mapping)
        session.commit()

        client = request.getfixturevalue(client_fixture)
        resp = client.delete(f"/import/api/mapping/{mapping.id}", headers=HEADERS)
        assert resp.status_code == expected
        if expected == 200:
            assert session.get(Mapping, mapping.id) is None
        else:
            assert session.get(Mapping, mapping.id) is not None


class TestMappingDeleteOtherUser:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 403),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_delete_other_user_mapping(self, request, session, client_fixture, expected):
        from uuid import uuid4

        from enferno.data_import.models import Mapping
        from enferno.user.models import Role

        from sqlalchemy import select

        uid = uuid4().hex[:8]
        new_admin = User(username=f"OtherAdmin{uid}", password="password", active=1)
        new_admin.fs_uniquifier = uuid4().hex
        new_admin.roles.append(session.scalar(select(Role).where(Role.name == "Admin")))
        session.add(new_admin)
        session.commit()

        mapping = MappingFactory()
        mapping.user_id = new_admin.id
        session.add(mapping)
        session.commit()

        client = request.getfixturevalue(client_fixture)
        resp = client.delete(f"/import/api/mapping/{mapping.id}", headers=HEADERS)
        assert resp.status_code == expected


# =========================================================================
# LOOKUP CSV IMPORTS
# =========================================================================

_LOOKUP_CSV_CONFIGS = [
    (
        "label",
        "/admin/api/label/import/",
        LabelFactory,
        Label,
        [
            "title",
            "for_actor",
            "for_bulletin",
            "for_incident",
            "for_offline",
            "verified",
            "order",
            "parent_label_id",
        ],
    ),
    (
        "source",
        "/admin/api/source/import/",
        SourceFactory,
        Source,
        ["title", "title_ar", "comments"],
    ),
    (
        "eventtype",
        "/admin/api/eventtype/import/",
        EventtypeFactory,
        Eventtype,
        ["title", "title_ar", "comments", "for_actor", "for_bulletin"],
    ),
    (
        "claimedviolation",
        "/admin/api/claimedviolation/import/",
        ClaimedViolationFactory,
        ClaimedViolation,
        ["title", "title_ar"],
    ),
    (
        "potentialviolation",
        "/admin/api/potentialviolation/import/",
        PotentialViolationFactory,
        PotentialViolation,
        ["title", "title_ar"],
    ),
]


def _lookup_csv_import_params():
    roles = [
        ("admin_client", 200),
        ("da_client", 403),
        ("mod_client", 403),
        ("anonymous_client", 401),
    ]
    for name, url, factory, model, headers in _LOOKUP_CSV_CONFIGS:
        for client_fixture, status in roles:
            yield pytest.param(
                name,
                url,
                factory,
                model,
                headers,
                client_fixture,
                status,
                id=f"csv-import-{name}-{client_fixture}",
            )


class TestLookupCsvImport:
    @pytest.mark.parametrize(
        "name,url,factory_cls,model_cls,csv_headers,client_fixture,expected",
        list(_lookup_csv_import_params()),
    )
    def test_import(
        self,
        request,
        session,
        name,
        url,
        factory_cls,
        model_cls,
        csv_headers,
        client_fixture,
        expected,
    ):
        # Clear existing data for this model
        session.query(model_cls).delete(synchronize_session=False)
        session.commit()

        e1 = factory_cls()
        e2 = factory_cls()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".csv") as tmp:
            writer = csv.writer(tmp)
            writer.writerow(csv_headers)
            for entity in [e1, e2]:
                row = [
                    str(
                        getattr(entity, field, None)
                        if getattr(entity, field, None) is not None
                        else ""
                    )
                    for field in csv_headers
                ]
                writer.writerow(row)
            tmp.flush()
            csv_path = tmp.name

        try:
            with open(csv_path, "rb") as f:
                client = request.getfixturevalue(client_fixture)
                resp = client.post(
                    url,
                    content_type="multipart/form-data",
                    data={"csv": (f, "test.csv")},
                    follow_redirects=True,
                    headers={"Accept": "application/json"},
                )
                assert resp.status_code == expected
        finally:
            os.unlink(csv_path)


# =========================================================================
# LOCATION ADMIN LEVEL REORDER
# =========================================================================


class TestLocationAdminLevelReorder:
    @pytest.mark.parametrize(
        "client_fixture, expected",
        [
            ("admin_client", 200),
            ("da_client", 403),
            ("mod_client", 403),
            ("anonymous_client", 401),
        ],
    )
    def test_reorder(self, request, session, client_fixture, expected):
        # Clear existing admin levels to avoid count mismatch
        session.query(LocationAdminLevel).delete(synchronize_session=False)
        session.commit()

        lal1 = LocationAdminLevelFactory()
        lal2 = LocationAdminLevelFactory()
        lal3 = LocationAdminLevelFactory()
        lal1.code = 9001
        lal2.code = 9002
        lal3.code = 9003
        lal1.display_order = 1
        lal2.display_order = 2
        lal3.display_order = 3
        session.add_all([lal1, lal2, lal3])
        session.commit()

        client = request.getfixturevalue(client_fixture)
        resp = client.post(
            "/admin/api/location-admin-levels/reorder",
            json={"order": [lal3.id, lal2.id, lal1.id]},
            headers=HEADERS,
        )
        assert resp.status_code == expected
        f1 = LocationAdminLevel.query.filter(LocationAdminLevel.id == lal1.id).first()
        f2 = LocationAdminLevel.query.filter(LocationAdminLevel.id == lal2.id).first()
        f3 = LocationAdminLevel.query.filter(LocationAdminLevel.id == lal3.id).first()
        if expected == 200:
            assert f1.display_order == 3
            assert f2.display_order == 2
            assert f3.display_order == 1
        else:
            assert f1.display_order == 1
            assert f2.display_order == 2
            assert f3.display_order == 3
