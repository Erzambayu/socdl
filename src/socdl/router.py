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


def download(url: str, det: Detected, cfg: Config, progress_cb=None) -> EngineResult:
    """Try engines in order until one succeeds or all fail."""
    out_dir = _resolve_out_dir(det, cfg)
    chain: Iterable[str] = engine_chain(det)

    last: EngineResult = EngineResult(False, 1, "-", out_dir, "no engine ran")
    for name in chain:
        engine = ENGINE_MAP[name]()
        if not engine.is_available():
            continue
        if progress_cb:
            progress_cb(name)
        res = engine.download(url, out_dir, det, cfg)
        if res.ok:
            return res
        last = res
    return last


__all__ = ["download", "engine_chain"]
