"""Route a URL to the best-fit engine, with fallback chain."""
from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from .config import Config
from .engines import EngineResult, GalleryDLEngine, InstaloaderEngine, YtDlpEngine
from .platforms import Detected


def _resolve_out_dir(det: Detected, cfg: Config) -> Path:
    base = cfg.resolved_output_dir()
    if cfg.subfolder_per_platform:
        base = base / det.folder_name
    base.mkdir(parents=True, exist_ok=True)
    return base


def engine_chain(det: Detected) -> list[str]:
    if det.platform == "instagram":
        # instaloader = best for posts/carousels (photo+video).
        # yt-dlp only handles the *video* items in a carousel, so we prefer
        # gallery-dl as second, and yt-dlp only for reels (video-only content).
        if det.kind == "reel":
            return ["yt-dlp", "instaloader", "gallery-dl"]
        return ["instaloader", "gallery-dl"]
    if det.platform == "tiktok":
        if det.kind == "photo":
            return ["gallery-dl", "yt-dlp"]
        return ["yt-dlp", "gallery-dl"]
    if det.platform == "facebook":
        # yt-dlp is the only engine with real Facebook support; gallery-dl has
        # no Facebook extractor, so don't waste an attempt (and a misleading
        # final error) on it.
        return ["yt-dlp"]
    if det.platform == "twitter":
        return ["gallery-dl", "yt-dlp"]
    if det.platform == "reddit":
        return ["gallery-dl", "yt-dlp"]
    return ["yt-dlp", "gallery-dl"]


ENGINE_MAP = {
    "yt-dlp":      YtDlpEngine,
    "instaloader": InstaloaderEngine,
    "gallery-dl":  GalleryDLEngine,
}


def download(url: str, det: Detected, cfg: Config, progress_cb=None,
             on_engine=None) -> EngineResult:
    """Try engines in order until one succeeds or all fail.

    ``on_engine(name)`` is called when an engine attempt begins (engine
    switch). ``progress_cb(ProgressInfo)`` receives byte-level progress from
    engines that support it (currently yt-dlp).
    """
    out_dir = _resolve_out_dir(det, cfg)
    chain: Iterable[str] = engine_chain(det)

    last: EngineResult = EngineResult(False, 1, "-", out_dir, "no engine ran")
    for name in chain:
        engine = ENGINE_MAP[name]()
        if not engine.is_available():
            continue
        if on_engine:
            on_engine(name)
        res = engine.download(url, out_dir, det, cfg, progress=progress_cb)
        if res.ok:
            return res
        last = res
    return last


__all__ = ["download", "engine_chain"]
