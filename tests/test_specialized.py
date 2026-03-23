"""
RBAC tests for specialized endpoints: relation infos, history, locations,
queries, activity, bulk status, whisper, media upload, data imports,
and the combined relation info endpoint.
"""

import os
import random
import tempfile
from io import BytesIO
from unittest.mock import patch

import pytest
from flask import current_app

from enferno.admin.models import (
    Activity,
    Actor,
    ActorHistory,
    AtoaInfo,
    AtobInfo,
    BtobInfo,
    Bulletin,
    BulletinHistory,
    Incident,
    IncidentHistory,
    ItoaInfo,
    ItobInfo,
    ItoiInfo,
    Location,
    LocationHistory,
    Query,
)
from enferno.user.models import User
from tests.factories import (
    ActorFactory,
    ActorHistoryFactory,
    ActivityFactory,
    AtoaInfoFactory,
    AtobInfoFactory,
    BtobInfoFactory,
    BulletinFactory,
    BulletinHistoryFactory,
    IncidentFactory,
    IncidentHistoryFactory,
    ItoaInfoFactory,
    ItobInfoFactory,
    ItoiInfoFactory,
    LocationFactory,
    LocationHistoryFactory,
    QueryFactory,
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
