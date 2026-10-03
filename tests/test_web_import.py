import io

import pytest
import yt_dlp
from yt_dlp.utils import DownloadError

from enferno.admin.validation.models import FullConfigValidationModel
from enferno.tasks import media_download
from enferno.utils.config_utils import ConfigManager


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
    with pytest.raises(ValueError, match="Download failed"):
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
