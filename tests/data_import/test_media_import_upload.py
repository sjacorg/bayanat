"""Tests for MediaImport.upload S3 behaviour.

Regression cover for uploads above S3's 5 GiB single-PUT limit. put_object caps
there and returned EntityTooLarge in production, losing two YouTube imports
(data_import 318146 and 265556, 2025-03-28) whose muxed video exceeded 5 GiB.
"""

from unittest.mock import MagicMock

import pytest

from enferno.data_import.utils.media_import import MediaImport
from enferno.settings import Config

S3_CONFIG = {
    "FILESYSTEM_LOCAL": False,
    "S3_BUCKET": "test-bucket",
    "AWS_ACCESS_KEY_ID": "key",
    "AWS_SECRET_ACCESS_KEY": "secret",
    "AWS_REGION": "us-east-1",
}


class _StubDataImport:
    """Collects log lines instead of writing to the database."""

    def __init__(self):
        self.log = []

    def add_to_log(self, message):
        self.log.append(message)


class _StubImporter:
    """Stands in for MediaImport, whose __init__ requires a DB session."""

    def __init__(self):
        self.data_import = _StubDataImport()


@pytest.fixture
def s3_bucket(monkeypatch):
    """Route upload() down the S3 branch against a mock bucket."""
    monkeypatch.setattr(Config, "get", lambda key, default=None: S3_CONFIG.get(key, default))
    bucket = MagicMock()
    resource = MagicMock()
    resource.Bucket.return_value = bucket
    monkeypatch.setattr(
        "enferno.data_import.utils.media_import.boto3.resource",
        lambda *args, **kwargs: resource,
    )
    return bucket


@pytest.fixture
def media_file(tmp_path):
    path = tmp_path / "video.mp4"
    path.write_bytes(b"stand-in for a multi-gigabyte video")
    return path


def test_upload_uses_managed_transfer(s3_bucket, media_file):
    """Must use upload_file, which splits into a multipart transfer automatically.

    put_object is a single PUT and cannot exceed 5 GiB, so its presence here is
    the bug this test guards against.
    """
    assert MediaImport.upload(_StubImporter(), str(media_file), "video.mp4") is True

    s3_bucket.upload_file.assert_called_once_with(str(media_file), "video.mp4")
    s3_bucket.put_object.assert_not_called()


def test_upload_strips_directories_from_the_key(s3_bucket, media_file):
    """Keys are flat in the bucket; a nested source path must not create prefixes."""
    MediaImport.upload(_StubImporter(), str(media_file), "yt-2024-hi/abc123/video.mp4")

    s3_bucket.upload_file.assert_called_once_with(str(media_file), "video.mp4")


def test_upload_reports_failure(s3_bucket, media_file):
    """A rejected upload must return False so callers can fail the import."""
    s3_bucket.upload_file.side_effect = Exception(
        "An error occurred (EntityTooLarge) when calling the PutObject operation"
    )
    importer = _StubImporter()

    assert MediaImport.upload(importer, str(media_file), "video.mp4") is False
    assert "Failed to upload to S3 bucket." in importer.data_import.log


def test_upload_reports_failure_when_filesystem_unconfigured(monkeypatch, media_file):
    """Neither local nor S3 configured is a failure, not a silent success."""
    monkeypatch.setattr(Config, "get", lambda key, default=None: None)
    importer = _StubImporter()

    assert MediaImport.upload(importer, str(media_file), "video.mp4") is False
    assert "Filesystem is not configured properly" in importer.data_import.log
