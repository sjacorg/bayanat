"""Tests for import failure handling in MediaImport.

A failed media upload must terminate the import. Otherwise the import continues
and can create a Media row whose file was never stored, which is unservable in
production because media URLs are generated from S3 with no local fallback.

process() must also tolerate the None a terminated import returns, rather than
dereferencing it and masking the real cause behind an AttributeError.
"""

import pytest

from enferno.data_import.utils.media_import import MediaImport
from enferno.settings import Config

TERMINATION_LOG = "Unable to proceed without media file. Terminating."

WEB_FILE = {"filename": "video.mp4", "name": "video.mp4"}
UPLOAD_FILE = {"filename": "video.mp4", "original_filename": "video.mp4"}


class _StubDataImport:
    """Records log lines and failure state instead of touching the database."""

    id = 1

    def __init__(self):
        self.log = []
        self.data = {}
        self.failed = False

    def add_to_log(self, message):
        self.log.append(message)

    def add_format(self, file_ext):
        pass

    def processing(self):
        pass

    def fail(self):
        self.failed = True


class _StubImporter(MediaImport):
    """A MediaImport that skips the DB session its __init__ would open.

    Subclassed rather than duck-typed so the MODE_* constants process() reads
    off self are inherited.
    """

    def __init__(self, upload_result=False):
        self.data_import = _StubDataImport()
        self.meta = {}
        self._upload_result = upload_result

    def upload(self, filepath, target):
        return self._upload_result


@pytest.fixture(autouse=True)
def s3_mode(monkeypatch):
    """Select the S3 branch and stub exif extraction, which shells out."""
    monkeypatch.setattr(
        Config, "get", lambda key, default=None: False if key == "FILESYSTEM_LOCAL" else default
    )
    monkeypatch.setattr(
        "enferno.data_import.utils.media_import.exiflib.get_json", lambda path: [{}]
    )


@pytest.mark.parametrize(
    "import_method, file_arg",
    [
        (MediaImport.web_import, WEB_FILE),
        (MediaImport.upload_import, UPLOAD_FILE),
    ],
    ids=["web_import", "upload_import"],
)
def test_failed_upload_terminates_the_import(import_method, file_arg):
    """A rejected upload must fail the import, not fall through to bulletin creation."""
    importer = _StubImporter(upload_result=False)

    assert import_method(importer, file_arg) is None
    assert importer.data_import.failed is True
    assert TERMINATION_LOG in importer.data_import.log


@pytest.mark.parametrize(
    "import_method, file_arg",
    [
        (MediaImport.web_import, WEB_FILE),
        (MediaImport.upload_import, UPLOAD_FILE),
    ],
    ids=["web_import", "upload_import"],
)
def test_successful_upload_continues(import_method, file_arg):
    """The happy path must be untouched by the failure handling."""
    importer = _StubImporter(upload_result=True)

    info = import_method(importer, file_arg)

    assert info is not None
    assert info["filename"] == "video.mp4"
    assert importer.data_import.failed is False
    assert TERMINATION_LOG not in importer.data_import.log


def test_process_tolerates_a_terminated_import():
    """Regression: process() raised AttributeError on the None from a failed import.

    server_import has always returned None on upload failure, so this crash
    predates the two call sites fixed alongside it.
    """
    importer = _StubImporter()
    importer.meta = {"mode": MediaImport.MODE_WEB}
    importer.web_import = lambda file: None

    assert MediaImport.process(importer, {"filename": "video.mp4"}) is None
