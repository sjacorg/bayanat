import io
import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import yt_dlp
from yt_dlp.utils import DownloadError

from enferno.admin.validation.models import FullConfigValidationModel
from enferno.tasks import media_download
from enferno.utils.config_utils import ConfigManager


@pytest.fixture(autouse=True)
def _ffmpeg_tools_present(monkeypatch):
    # Keep these tests independent of whether the host has ffmpeg installed
    monkeypatch.setattr("enferno.utils.dep_utils.shutil.which", lambda name: f"/usr/bin/{name}")


def test_cookies_stay_in_memory(monkeypatch):
    monkeypatch.setattr(media_download.cfg, "YTDLP_COOKIES", "cookie-data", raising=False)
    options = media_download._get_ytdl_options(with_cookies=True)
    assert isinstance(options["cookiefile"], io.StringIO)
    assert options["cookiefile"].read() == "cookie-data"


def test_no_cookies_configured_means_no_cookiefile(monkeypatch):
    monkeypatch.setattr(media_download.cfg, "YTDLP_COOKIES", "", raising=False)
    assert "cookiefile" not in media_download._get_ytdl_options(with_cookies=True)


def test_hls_downloads_bypass_ffmpeg():
    from yt_dlp.downloader import get_suitable_downloader

    params = yt_dlp.YoutubeDL(media_download._get_ytdl_options()).params
    for protocol in ("m3u8", "m3u8_native"):
        info = {"protocol": protocol, "url": "https://x/y.m3u8", "ext": "mp4"}
        assert get_suitable_downloader(info, params).__name__ == "HlsFD"


def test_masked_cookies_pass_validation():
    assert (
        FullConfigValidationModel.validate_cookies(ConfigManager.MASK_STRING)
        == ConfigManager.MASK_STRING
    )


@pytest.mark.parametrize(
    "stored, submitted, previous_timestamp, expected",
    [
        ("", "new-cookies", None, "2026-10-10T12:30"),
        ("old-cookies", "new-cookies", "2026-09-01T09:00", "2026-10-10T12:30"),
        ("old-cookies", ConfigManager.MASK_STRING, "2026-09-01T09:00", "2026-09-01T09:00"),
        ("old-cookies", "old-cookies", "2026-09-01T09:00", "2026-09-01T09:00"),
        ("old-cookies", "", "2026-09-01T09:00", None),
    ],
)
def test_cookie_timestamp_tracks_actual_changes(
    monkeypatch, tmp_path, stored, submitted, previous_timestamp, expected
):
    from enferno.admin.models import Activity, AppConfig
    from enferno.settings import Config
    from enferno.utils.date_helper import DateHelper

    config_path = tmp_path / "config.json"
    monkeypatch.setattr(ConfigManager, "CONFIG_FILE_PATH", str(config_path))
    monkeypatch.setattr(Config, "YTDLP_COOKIES", stored)
    monkeypatch.setattr(Config, "YTDLP_COOKIES_UPDATED_AT", previous_timestamp)
    monkeypatch.setattr(DateHelper, "utcnow", lambda: datetime(2026, 10, 10, 12, 30))
    monkeypatch.setattr("enferno.utils.config_utils.current_user", SimpleNamespace(id=1))
    revisions = []
    monkeypatch.setattr(AppConfig, "save", lambda self: revisions.append(self.config))
    monkeypatch.setattr(Activity, "create", Mock())
    conf = {"YTDLP_COOKIES": submitted, "YTDLP_COOKIES_UPDATED_AT": "2000-01-01T00:00"}

    assert ConfigManager.write_config(conf)

    saved = json.loads(config_path.read_text())
    assert saved["YTDLP_COOKIES"] == (
        stored if submitted == ConfigManager.MASK_STRING else submitted
    )
    assert saved["YTDLP_COOKIES_UPDATED_AT"] == expected
    assert revisions == [{"YTDLP_COOKIES_UPDATED_AT": saved["YTDLP_COOKIES_UPDATED_AT"]}]


def test_generic_errors_mentioning_age_do_not_retry_with_cookies(monkeypatch):
    attempts = []

    class FakeYDL:
        def __init__(self, options):
            attempts.append("cookiefile" in options)

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def extract_info(self, url, download):
            raise DownloadError("ERROR: unable to download webpage: HTTP Error 404")

    monkeypatch.setattr(media_download.yt_dlp, "YoutubeDL", FakeYDL)
    monkeypatch.setattr(media_download.cfg, "YTDLP_COOKIES", "cookie-data", raising=False)
    with pytest.raises(ValueError, match="HTTP Error 404"):
        media_download._download_media("https://example.com/video")
    assert attempts == [False]


@pytest.mark.parametrize("error", [ValueError("cookies may be expired"), RuntimeError("disk full")])
def test_failure_notification_includes_reason(monkeypatch, error):
    sent = []

    class FakeImport:
        def add_to_log(self, msg):
            pass

        def fail(self):
            pass

    def boom(url):
        raise error

    monkeypatch.setattr(media_download.db.session, "get", lambda model, ident: FakeImport())
    monkeypatch.setattr(media_download, "_download_media", boom)
    monkeypatch.setattr(
        media_download.Notification,
        "send_notification_for_event",
        lambda *args: sent.append(args[-1]),
    )
    media_download.download_media_from_web.run("https://example.com/v", 1, "batch", 1)
    assert sent == [f"Web import of https://example.com/v has failed: {error}"]


def test_auth_error_without_cookies_reports_the_real_error(monkeypatch):
    class BotCheckYDL:
        def __init__(self, options):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def extract_info(self, url, download):
            raise DownloadError("ERROR: Sign in to confirm you're not a bot. Use --cookies")

    monkeypatch.setattr(media_download.yt_dlp, "YoutubeDL", BotCheckYDL)
    monkeypatch.setattr(media_download.cfg, "YTDLP_COOKIES", "", raising=False)
    with pytest.raises(ValueError, match="not a bot"):
        media_download._download_media("https://www.youtube.com/watch?v=x")


def test_web_import_requires_ffmpeg(monkeypatch):
    monkeypatch.setattr("enferno.utils.dep_utils.shutil.which", lambda name: None)
    with pytest.raises(ValueError, match="ffmpeg, ffprobe not installed"):
        media_download._download_media("https://example.com/video")


@pytest.mark.parametrize("name", ["abc.unknown_video", "abc.mp4"])
def test_downloaded_file_is_named_by_content(monkeypatch, tmp_path, name):
    monkeypatch.setattr(media_download.Media, "media_dir", tmp_path)
    temp_file = tmp_path / name
    temp_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)
    final = media_download._process_downloaded_file(temp_file, {"id": "abc"})
    assert final.startswith("abc-") and final.endswith(".png")
    assert (tmp_path / final).exists()
