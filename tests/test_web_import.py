import io

import pytest
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
    assert media_download._get_ytdl_options()["external_downloader"] == {"m3u8": "native"}


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
