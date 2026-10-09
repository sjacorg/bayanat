import io

import pytest
import requests
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


def _response(content_type, body=b"img"):
    response = requests.Response()
    response.status_code = 200
    response.headers["Content-Type"] = content_type
    response.raw = io.BytesIO(body)
    return response


@pytest.fixture
def fake_get(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(media_download.Media, "media_dir", tmp_path)
    monkeypatch.setattr(media_download.cfg, "MEDIA_UPLOAD_MAX_FILE_SIZE", 1, raising=False)
    monkeypatch.setattr(media_download.cfg, "YTDLP_PROXY", "http://127.0.0.1:8118", raising=False)
    monkeypatch.setattr(
        media_download.cfg, "MEDIA_ALLOWED_EXTENSIONS", ["png", "jpg"], raising=False
    )

    def install(response):
        def get(session, url, **kwargs):
            calls.append((session, kwargs))
            return response

        monkeypatch.setattr(media_download.requests.Session, "get", get)
        return calls

    return install


def test_direct_image_downloads_through_proxy_without_redirects(fake_get, tmp_path):
    calls = fake_get(_response("image/png; charset=binary"))
    info, path = media_download._download_image("https://example.com/a.png")
    session, kwargs = calls[0]
    assert session.proxies == {"http": "http://127.0.0.1:8118", "https": "http://127.0.0.1:8118"}
    assert session.trust_env is False and kwargs["allow_redirects"] is False
    assert path.parent == tmp_path and path.suffix == ".png" and path.read_bytes() == b"img"
    assert info == {
        "title": "https://example.com/a.png",
        "webpage_url": "https://example.com/a.png",
    }


@pytest.mark.parametrize("content_type", ["text/html", "image/svg+xml"])
def test_non_image_or_disallowed_type_is_unsupported(fake_get, tmp_path, content_type):
    fake_get(_response(content_type))
    with pytest.raises(ValueError, match="not supported"):
        media_download._download_image("https://example.com/page")
    assert not list(tmp_path.iterdir())


def test_oversized_image_is_rejected_and_removed(fake_get, tmp_path):
    fake_get(_response("image/jpeg", body=b"x" * (1024 * 1024 + 1)))
    with pytest.raises(ValueError, match="maximum allowed size"):
        media_download._download_image("https://example.com/big.jpg")
    assert not list(tmp_path.iterdir())


def test_unsupported_url_falls_back_to_image(monkeypatch):
    def fail(*args, **kwargs):
        raise DownloadError("ERROR: Unsupported URL: https://example.com/a.png")

    monkeypatch.setattr(media_download.yt_dlp.YoutubeDL, "extract_info", fail)
    monkeypatch.setattr(media_download, "_download_image", lambda url: ("info", url))
    assert media_download._download_media("https://example.com/a.png") == (
        "info",
        "https://example.com/a.png",
    )
