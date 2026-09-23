"""Tests for media-info probing, formatting, and history persistence."""
from socdl.engines.base import MediaInfo, media_info_from_ytdlp
from socdl.ui import fmt_count, fmt_date, fmt_duration


# -- formatting ------------------------------------------------------------
def test_fmt_count_compact():
    assert fmt_count(None) == "?"
    assert fmt_count(0) == "0"
    assert fmt_count(999) == "999"
    assert fmt_count(1000) == "1.0K"
    assert fmt_count(1266) == "1.3K"
    assert fmt_count(23_386_341) == "23.4M"
    assert fmt_count(3_400_000_000) == "3.4B"


def test_fmt_duration():
    assert fmt_duration(None) == "?"
    assert fmt_duration(0) == "0:00"
    assert fmt_duration(45) == "0:45"
    assert fmt_duration(635) == "10:35"
    assert fmt_duration(3661) == "1:01:01"


def test_fmt_date():
    assert fmt_date("") == ""
    assert fmt_date("20141110") == "2014-11-10"
    assert fmt_date("2024-01-02") == "2024-01-02"


# -- media_info_from_ytdlp -------------------------------------------------
def test_media_info_maps_youtube_fields():
    info = media_info_from_ytdlp({
        "title": "Big Buck Bunny",
        "uploader": "Blender",
        "duration": 635,
        "upload_date": "20141110",
        "view_count": 23_386_341,
        "like_count": 109_971,
        "comment_count": 5100,
    })
    assert info.engine == "yt-dlp"
    assert info.title == "Big Buck Bunny"
    assert info.uploader == "Blender"
    assert info.duration == 635.0
    assert info.upload_date == "20141110"
    assert info.view_count == 23_386_341
    assert info.like_count == 109_971
    assert info.comment_count == 5100
    assert info.has_counts


def test_media_info_handles_missing_and_aliases():
    info = media_info_from_ytdlp({"channel": "SomeChannel", "repost_count": 12})
    assert info.uploader == "SomeChannel"
    assert info.repost_count == 12
    assert info.share_count == 12
    assert info.view_count is None
    assert not info.is_empty()

    empty = media_info_from_ytdlp({})
    assert empty.is_empty()
    assert not empty.has_counts


def test_media_info_coerces_string_counts():
    info = media_info_from_ytdlp({"view_count": "42", "like_count": "abc"})
    assert info.view_count == 42
    assert info.like_count is None


# -- router.probe (best-effort) --------------------------------------------
def test_router_probe_returns_none_when_engines_fail(monkeypatch):
    from socdl import router
    from socdl.platforms import detect_platform

    class _Boom:
        def is_available(self):
            return True

        def probe(self, url, cfg):
            raise RuntimeError("network down")

    # Facebook's chain is ["yt-dlp"] only, so one monkeypatched engine suffices.
    monkeypatch.setattr(router, "ENGINE_MAP", {"yt-dlp": _Boom})
    det = detect_platform("https://www.facebook.com/reel/123")
    assert router.probe("https://www.facebook.com/reel/123", det, cfg=None) is None


def test_router_probe_returns_first_non_empty(monkeypatch):
    from socdl import router
    from socdl.platforms import detect_platform

    class _Probe:
        def is_available(self):
            return True

        def probe(self, url, cfg):
            return MediaInfo(engine="yt-dlp", title="hello", like_count=5)

    monkeypatch.setattr(router, "ENGINE_MAP", {"yt-dlp": _Probe})
    det = detect_platform("https://www.facebook.com/reel/123")
    info = router.probe("https://www.facebook.com/reel/123", det, cfg=None)
    assert info is not None and info.title == "hello" and info.like_count == 5


# -- history persistence ---------------------------------------------------
def test_history_record_and_recent_roundtrip(tmp_path, monkeypatch):
    from socdl import history

    monkeypatch.setattr(history.cfgmod, "data_dir", lambda: tmp_path)
    history.record(
        platform="youtube", kind="video", url="https://youtu.be/x",
        engine="yt-dlp", status="success", output_dir=str(tmp_path),
        title="My Video", uploader="Someone",
        view_count=1000, like_count=50, comment_count=5, share_count=2,
    )
    rows = history.recent(limit=1)
    assert len(rows) == 1
    r = rows[0]
    assert r.title == "My Video"
    assert r.uploader == "Someone"
    assert r.view_count == 1000
    assert r.like_count == 50
    assert r.comment_count == 5
    assert r.share_count == 2
