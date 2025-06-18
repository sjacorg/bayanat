from io import BytesIO
import os
import pytest
import random
from werkzeug.datastructures import FileStorage
from unittest.mock import patch
from flask import current_app

from enferno.utils.config_utils import ConfigManager
from tests.test_utils import (
    create_binary_file,
)

ALLOWED_EXTS = ["jpg", "mp4", "doc"]


##### FIXTURES #####


@pytest.fixture(scope="function")
def create_media_file(request, app):
    app = request.getfixturevalue("app")
    ext = random.choice(ALLOWED_EXTS)
    yield from create_binary_file(ext)


##### POST /admin/api/media/chunk #####

post_media_chunk_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_media_chunk_endpoint_roles)
def test_post_media_chunk_endpoint(create_media_file, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    _, ext = os.path.splitext(create_media_file)
    with open(create_media_file, "rb") as f:
        file_size = os.path.getsize(create_media_file)
        chunk_size = file_size
        dzuuid = "test-uuid"
        data = {
            "file": (f, f"test{ext}"),
            "dzuuid": dzuuid,
            "dzchunkindex": str(0),
            "dztotalchunkcount": str(1),
            "dztotalfilesize": str(file_size),
        }
        with patch.dict(current_app.config, {"MEDIA_ALLOWED_EXTENSIONS": ALLOWED_EXTS}):
            response = client_.post(
                "/admin/api/media/chunk",
                content_type="multipart/form-data",
                data=data,
                headers={"Referer": "", "Accept": "application/json"},
            )
            assert response.status_code == expected_status
            if expected_status == 200:
                # Check if the file was created
                media_directory = "enferno/media"
                file_exists = any(f.endswith(f"test{ext}") for f in os.listdir(media_directory))
                assert file_exists, "File not found in the media directory"

                # Delete the file after the assertion
                for filename in os.listdir(media_directory):
                    if filename.endswith(f"test{ext}"):
                        os.remove(os.path.join(media_directory, filename))
                        break


##### POST /admin/api/media/chunk FOR CHUNKED UPLOAD #####


@pytest.mark.parametrize("client_fixture, expected_status", post_media_chunk_endpoint_roles)
def test_post_media_chunk_endpoint_chunked_upload(
    create_media_file, request, client_fixture, expected_status
):
    client_ = request.getfixturevalue(client_fixture)
    _, ext = os.path.splitext(create_media_file)
    total_chunks = 5  # Define the total number of chunks for the test

    # Generate chunked file data
    file_size = os.path.getsize(create_media_file)
    chunk_size = file_size // total_chunks
    dzuuid = "test-uuid"  # A unique identifier for the chunked upload

    for chunk_index in range(total_chunks):
        with open(create_media_file, "rb") as f:
            f.seek(chunk_index * chunk_size)
            chunk_data = f.read(chunk_size)

        # Last chunk adjustment
        if chunk_index == total_chunks - 1:
            remaining_size = file_size - chunk_size * total_chunks
            if remaining_size > 0:
                with open(create_media_file, "rb") as f:
                    f.seek(chunk_index * chunk_size + chunk_size)
                    chunk_data += f.read(remaining_size)

        data = {
            "file": (FileStorage(stream=BytesIO(chunk_data), filename=f"test-chunk{ext}")),
            "dzuuid": dzuuid,
            "dzchunkindex": str(chunk_index),
            "dztotalchunkcount": str(total_chunks),
            "dztotalfilesize": str(file_size),
        }
        with patch.dict(current_app.config, {"MEDIA_ALLOWED_EXTENSIONS": ALLOWED_EXTS}):
            response = client_.post(
                "/admin/api/media/chunk",
                content_type="multipart/form-data",
                data=data,
                headers={"Referer": "", "Accept": "application/json"},
            )
            assert response.status_code == expected_status

            # Only perform the following checks after the last chunk
            if chunk_index == total_chunks - 1 and expected_status == 200:
                # Check if the final file was created and its size matches the original file
                media_directory = "enferno/media"
                file_exists = any(
                    f.endswith(f"test-chunk{ext}") for f in os.listdir(media_directory)
                )
                assert file_exists, "Final file not found in the media directory"

                # Check the size of the uploaded file
                for filename in os.listdir(media_directory):
                    if filename.endswith(f"test-chunk{ext}"):
                        final_path = os.path.join(media_directory, filename)
                        assert (
                            os.path.getsize(final_path) == file_size
                        ), "Final file size does not match the original file size"
                        # Cleanup: Delete the file after the assertion
                        os.remove(final_path)
                        break


##### POST /admin/api/media/upload #####

post_media_upload_endpoint_roles = [
    ("admin_client", 200),
    ("da_client", 200),
    ("mod_client", 403),
    ("anonymous_client", 401),
]


@pytest.mark.parametrize("client_fixture, expected_status", post_media_upload_endpoint_roles)
def test_post_media_upload_endpoint(create_media_file, request, client_fixture, expected_status):
    client_ = request.getfixturevalue(client_fixture)
    _, ext = os.path.splitext(create_media_file)
    with open(create_media_file, "rb") as f:
        with patch.dict(current_app.config, {"MEDIA_ALLOWED_EXTENSIONS": ALLOWED_EXTS}):
            data = {"file": (f, f"test{ext}")}
            response = client_.post(
                "/admin/api/media/upload/",
                content_type="multipart/form-data",
                data=data,
                headers={"Accept": "application/json"},
            )
            assert response.status_code == expected_status
            if expected_status == 200:
                # Check if the file was created
                media_directory = "enferno/media"
                file_exists = any(f.endswith(f"test{ext}") for f in os.listdir(media_directory))
                assert file_exists, "File not found in the media directory"

                # Delete the file after the assertion
                for filename in os.listdir(media_directory):
                    if filename.endswith(f"test{ext}"):
                        os.remove(os.path.join(media_directory, filename))
                        break
