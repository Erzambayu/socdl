"""Tests for the DoodStream engine (playmogo.com mirror).

All network access is faked: the flow, the URL shapes and the failure
handling are exercised without touching a real player page.
"""
import pytest
import requests

from socdl.config import Config
from socdl.engines import doodstream
from socdl.engines.doodstream import DoodStreamEngine, _player_url
from socdl.platforms import detect_platform

PLAYER_PAGE = (
    "<script type=\"text/javascript\">\n"
    "  function makePlay() {\n"
    "    $.get('/pass_md5/abc123/xyz789', function(data) {\n"
    "      $('.videoplayer').html(data);\n"
    "    });\n"
    "    return '?token=abc123def456&expiry=' + expiry;\n"
    "  }\n"
    "</script>"
)
MEDIA_BASE = "https://media.example.test/v/abc123/"
VIDEO_BYTES = b"\x00\x00\x00\x20ftypisom" + b"payload" * 64


class FakeResponse:
    def __init__(self, *, text="", headers=None, chunks=None, status=200):
        self.text = text
        self.headers = headers or {}
        self.status_code = status
        self._chunks = chunks or []

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")

    def iter_content(self, chunk_size=1):
        for chunk in self._chunks:
            yield chunk

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeSession:
    def __init__(self, handler):
        self._handler = handler

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url, headers=None, timeout=None, stream=False):
        return self._handler(url, stream)


def _install(monkeypatch, handler):
    monkeypatch.setattr(doodstream.requests, "Session", lambda: FakeSession(handler))


@pytest.mark.parametrize("url, video_id", [
    ("https://playmogo.com/d/yj2iqz70pnsx", "yj2iqz70pnsx"),
    ("https://playmogo.com/e/yj2iqz70pnsx", "yj2iqz70pnsx"),
    ("https://www.playmogo.com/d/yj2iqz70pnsx/", "yj2iqz70pnsx"),
])
def test_player_url_normalizes_share_links(url, video_id):
    player_url, returned_id = _player_url(url)
    assert returned_id == video_id
    assert player_url == f"https://www.playmogo.com/e/{video_id}" or \
        player_url == f"https://playmogo.com/e/{video_id}"


@pytest.mark.parametrize("url", [
    "http://playmogo.com/d/yj2iqz70pnsx",              # not https
    "https://playmogo.com.evil.test/d/yj2iqz70pnsx",   # lookalike host
    "https://playmogo.com/",                           # missing id
    "https://playmogo.com/d/",                         # empty id
    "https://playmogo.com/watch/yj2iqz70pnsx",         # unknown path
])
def test_player_url_rejects_unsupported_links(url):
    with pytest.raises(ValueError):
        _player_url(url)


def test_download_happy_path(monkeypatch, tmp_path):
    def handler(url, stream):
        if url == "https://playmogo.com/e/yj2iqz70pnsx":
            return FakeResponse(text=PLAYER_PAGE)
        if url == "https://playmogo.com/pass_md5/abc123/xyz789":
            return FakeResponse(text=MEDIA_BASE)
        if url.startswith(MEDIA_BASE):
            assert stream, "media must be streamed"
            return FakeResponse(
                headers={"Content-Type": "video/mp4",
                         "Content-Length": str(len(VIDEO_BYTES))},
                chunks=[VIDEO_BYTES],
            )
        raise AssertionError(f"unexpected GET {url}")

    _install(monkeypatch, handler)
    progress = []
    url = "https://playmogo.com/d/yj2iqz70pnsx"
    result = DoodStreamEngine().download(
        url, tmp_path, detect_platform(url), Config(), progress=progress.append,
    )

    assert result.ok, result.message
    out = tmp_path / "yj2iqz70pnsx.mp4"
    assert out.read_bytes() == VIDEO_BYTES
    assert not (tmp_path / "yj2iqz70pnsx.mp4.part").exists()
    assert any(p.status == "finished" for p in progress)


def test_non_video_response_is_rejected(monkeypatch, tmp_path):
    def handler(url, stream):
        if url == "https://playmogo.com/e/yj2iqz70pnsx":
            return FakeResponse(text=PLAYER_PAGE)
        if url == "https://playmogo.com/pass_md5/abc123/xyz789":
            return FakeResponse(text=MEDIA_BASE)
        return FakeResponse(headers={"Content-Type": "text/html"}, chunks=[b"<html>"])

    _install(monkeypatch, handler)
    url = "https://playmogo.com/d/yj2iqz70pnsx"
    result = DoodStreamEngine().download(url, tmp_path, detect_platform(url), Config())

    assert not result.ok
    assert not (tmp_path / "yj2iqz70pnsx.mp4").exists()
    assert not (tmp_path / "yj2iqz70pnsx.mp4.part").exists()


def test_incomplete_download_leaves_no_partial_file(monkeypatch, tmp_path):
    def handler(url, stream):
        if url == "https://playmogo.com/e/yj2iqz70pnsx":
            return FakeResponse(text=PLAYER_PAGE)
        if url == "https://playmogo.com/pass_md5/abc123/xyz789":
            return FakeResponse(text=MEDIA_BASE)
        return FakeResponse(
            headers={"Content-Type": "video/mp4", "Content-Length": "999999"},
            chunks=[VIDEO_BYTES],
        )

    _install(monkeypatch, handler)
    url = "https://playmogo.com/d/yj2iqz70pnsx"
    result = DoodStreamEngine().download(url, tmp_path, detect_platform(url), Config())

    assert not result.ok
    assert not (tmp_path / "yj2iqz70pnsx.mp4").exists()
    assert not (tmp_path / "yj2iqz70pnsx.mp4.part").exists()


def test_missing_player_endpoint_reports_clean_error(monkeypatch, tmp_path):
    _install(monkeypatch, lambda url, stream: FakeResponse(text="<html>no player</html>"))
    url = "https://playmogo.com/d/yj2iqz70pnsx"
    result = DoodStreamEngine().download(url, tmp_path, detect_platform(url), Config())

    assert not result.ok
    assert result.exit_code == 1
    assert not list(tmp_path.iterdir())
