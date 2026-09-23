"""Tests for download progress plumbing and queue helpers."""
from socdl.cli import QueueItem, _drain_queue, _extract_urls, _InteractionState
from socdl.engines.base import ProgressInfo
from socdl.engines.ytdlp import YtDlpEngine
from socdl.ui import fmt_bytes, fmt_eta, fmt_speed


# -- byte / speed / eta formatting -----------------------------------------
def test_fmt_bytes():
    assert fmt_bytes(0) == "0 B"
    assert fmt_bytes(512) == "512 B"
    assert fmt_bytes(1024) == "1.0 KB"
    assert fmt_bytes(1024 * 1024 * 5) == "5.0 MB"


def test_fmt_speed_and_eta():
    assert fmt_speed(None) == "?"
    assert fmt_speed(1024) == "1.0 KB/s"
    assert fmt_eta(None) == "?"
    assert fmt_eta(45) == "45s"
    assert fmt_eta(65) == "1m 05s"
    assert fmt_eta(3600 + 120) == "1h 02m"


# -- ProgressInfo ----------------------------------------------------------
def test_progress_percent():
    info = ProgressInfo(downloaded=50, total=100)
    assert info.percent == 50.0
    assert ProgressInfo(downloaded=1, total=None).percent is None
    assert ProgressInfo(downloaded=1, total=0).percent is None


def test_progress_percent_clamped():
    assert ProgressInfo(downloaded=200, total=100).percent == 100.0


# -- yt-dlp hook mapping ---------------------------------------------------
def test_progress_from_hook_downloading():
    info = YtDlpEngine._progress_from_hook({
        "status": "downloading",
        "downloaded_bytes": 1024,
        "total_bytes": 4096,
        "speed": 512.0,
        "eta": 6.0,
        "filename": "clip.mp4",
    })
    assert info.status == "downloading"
    assert info.downloaded == 1024
    assert info.total == 4096
    assert info.percent == 25.0
    assert info.speed == 512.0
    assert info.eta == 6.0
    assert info.filename == "clip.mp4"


def test_progress_from_hook_estimate_and_finished():
    info = YtDlpEngine._progress_from_hook({
        "status": "downloading",
        "downloaded_bytes": 10,
        "total_bytes_estimate": 100,
    })
    assert info.total == 100

    done = YtDlpEngine._progress_from_hook({"status": "finished"})
    assert done.status == "finished"


# -- yt-dlp subprocess template parsing ------------------------------------
def test_progress_from_template():
    line = "SOCDL_PROGRESS|downloading|2048|8192|1024.5|6"
    info = YtDlpEngine._progress_from_template(line)
    assert info is not None
    assert info.downloaded == 2048
    assert info.total == 8192
    assert info.speed == 1024.5
    assert info.eta == 6.0


def test_progress_from_template_ignores_noise():
    assert YtDlpEngine._progress_from_template("[download] 50%") is None
    assert YtDlpEngine._progress_from_template("SOCDL_PROGRESS|broken") is None


# -- quality format selectors ---------------------------------------------
def test_quality_format_best_has_no_cap():
    from socdl.engines.ytdlp import QUALITY_MAP, _quality_format

    assert QUALITY_MAP["best"] == "bv*+ba/b"
    assert _quality_format("audio") == "ba/b"


def test_quality_format_always_has_unrestricted_fallback():
    from socdl.engines.ytdlp import QUALITY_MAP

    # Every capped preset must end in a fallback that ignores the cap so the
    # download never hard-fails on sites without a matching format.
    for key in ("1080p", "720p", "480p", "360p"):
        sel = QUALITY_MAP[key]
        assert sel.endswith("/bv*+ba/b"), sel
        assert sel.count("/") >= 3, sel


def test_quality_format_considers_portrait_width():
    from socdl.engines.ytdlp import QUALITY_MAP

    # Portrait/reel filters must cap both dimensions, otherwise vertical
    # videos (where height is the long side) would be excluded.
    for key in ("1080p", "720p", "480p", "360p"):
        sel = QUALITY_MAP[key]
        assert "[height<=" in sel and "[width<=" in sel, sel


# -- queue -----------------------------------------------------------------
def test_extract_urls_strips_trailing_punct():
    urls = _extract_urls("see https://youtu.be/abc, and https://x.com/y)")
    assert urls == ["https://youtu.be/abc", "https://x.com/y"]


def test_drain_queue_empty_is_noop():
    state = _InteractionState()
    _drain_queue(state.queue, cfg=None, state=state)  # type: ignore[arg-type]
    assert state.queue == []


def test_drain_queue_runs_all_and_clears(monkeypatch):
    from socdl import cli as climod

    calls: list[str] = []
    monkeypatch.setattr(climod, "_handle_url", lambda url, cfg: calls.append(url) or True)

    state = _InteractionState()
    state.queue.extend([QueueItem("https://a"), QueueItem("https://b")])
    _drain_queue(state.queue, cfg=None, state=state)  # type: ignore[arg-type]

    assert calls == ["https://a", "https://b"]
    assert state.queue == []
    assert state.last_url == "https://b"
