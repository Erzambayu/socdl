"""Shared engine helpers.

Engines can run in two modes:

  * **subprocess** — when an external `yt-dlp` / `gallery-dl` / `instaloader`
    executable is on PATH (or importable as a module via a real Python
    interpreter). This gives users the exact upstream behavior and easy
    upgrades.

  * **in-process** — when socdl is frozen with PyInstaller (`sys.frozen`),
    or when no external executable is available but the library is
    importable. We call the library API directly instead of re-spawning
    `sys.executable` (which would point at socdl itself in a frozen build).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


def is_frozen() -> bool:
    """True when running from a PyInstaller / py2exe style bundle."""
    return getattr(sys, "frozen", False)


@dataclass
class EngineResult:
    ok: bool
    exit_code: int
    engine: str
    output_dir: Path
    message: str = ""


@dataclass
class ProgressInfo:
    """Normalized progress snapshot reported by an engine.

    ``total`` may be None when the size is unknown (indeterminate). ``status``
    mirrors yt-dlp's hook status: 'downloading' | 'finished' | 'error'.
    """

    status: str = "downloading"
    downloaded: float = 0.0
    total: Optional[float] = None
    speed: Optional[float] = None    # bytes/sec
    eta: Optional[float] = None      # seconds
    filename: str = ""

    @property
    def percent(self) -> Optional[float]:
        if not self.total:
            return None
        try:
            return max(0.0, min(100.0, self.downloaded / self.total * 100.0))
        except ZeroDivisionError:
            return None


MODULE_ALIAS = {
    "yt-dlp": "yt_dlp",
    "gallery-dl": "gallery_dl",
    "instaloader": "instaloader",
}


@dataclass
class MediaInfo:
    """Best-effort metadata about a link, gathered before downloading.

    All counters are optional because no single engine/site exposes every
    field — ``None`` means "not available", which the UI simply hides.
    """

    engine: str = ""
    title: str = ""
    uploader: str = ""
    duration: Optional[float] = None       # seconds
    upload_date: str = ""                  # YYYYMMDD or ISO
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    share_count: Optional[int] = None
    repost_count: Optional[int] = None
    extra: dict = field(default_factory=dict)

    @property
    def has_counts(self) -> bool:
        return any(v is not None for v in (
            self.view_count, self.like_count, self.comment_count,
            self.share_count, self.repost_count,
        ))

    def is_empty(self) -> bool:
        return not any((
            self.title, self.uploader, self.has_counts,
            self.duration, self.upload_date,
        ))


# Alias some sites use for shares/reposts; map them onto one field.
_SHARE_KEYS = ("share_count", "repost_count", "retweet_count", "repost")


def media_info_from_ytdlp(info: dict, engine: str = "yt-dlp") -> MediaInfo:
    """Build a MediaInfo from a yt-dlp info dict (best-effort)."""
    def _int(*keys) -> Optional[int]:
        for k in keys:
            v = info.get(k)
            if v is None:
                continue
            try:
                return int(v)
            except (TypeError, ValueError):
                continue
        return None

    share = _int(*_SHARE_KEYS)
    repost = _int("repost_count", "retweet_count")
    duration = info.get("duration")
    try:
        duration = float(duration) if duration is not None else None
    except (TypeError, ValueError):
        duration = None

    return MediaInfo(
        engine=engine,
        title=str(info.get("title") or "").strip(),
        uploader=str(info.get("uploader") or info.get("channel")
                     or info.get("uploader_id") or "").strip(),
        duration=duration,
        upload_date=str(info.get("upload_date") or "").strip(),
        view_count=_int("view_count", "play_count"),
        like_count=_int("like_count"),
        comment_count=_int("comment_count"),
        share_count=share,
        repost_count=repost,
    )


def find_executable(name: str) -> Optional[list[str]]:
    """Return `[exe]` if a standalone executable is on PATH, else None."""
    exe = shutil.which(name)
    if exe:
        return [exe]
    return None


def module_available(module: str) -> bool:
    try:
        __import__(module)
        return True
    except ImportError:
        return False


def find_command(name: str) -> Optional[list[str]]:
    """Return a runnable command list, or None if not available.

    Never falls back to `[sys.executable, "-m", ...]` when frozen, because
    `sys.executable` would be the socdl binary itself (infinite recursion).
    """
    exe = find_executable(name)
    if exe:
        return exe
    if is_frozen():
        return None
    mod = MODULE_ALIAS.get(name)
    if mod and module_available(mod):
        return [sys.executable, "-m", mod]
    return None


def run_subprocess(cmd: Sequence[str], *, quiet: bool = False,
                   on_line=None) -> int:
    """Run subprocess, streaming stdout/stderr to terminal. Returns exit code.

    When ``on_line`` is given, stdout is captured and each line is passed to
    the callback (used to parse download progress) instead of inheriting the
    terminal; stderr is still inherited so warnings stay visible.
    """
    try:
        if on_line is None:
            proc = subprocess.run(
                list(cmd),
                check=False,
                stdout=None if not quiet else subprocess.DEVNULL,
                stderr=None if not quiet else subprocess.DEVNULL,
            )
            return proc.returncode

        proc = subprocess.Popen(
            list(cmd),
            stdout=subprocess.PIPE,
            stderr=None,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            try:
                on_line(line.rstrip("\r\n"))
            except Exception:  # noqa: BLE001 - never let a callback kill the download
                pass
        proc.stdout.close()
        proc.wait()
        return proc.returncode
    except FileNotFoundError:
        return 127
    except KeyboardInterrupt:
        return 130


class BaseEngine:
    name: str = "base"
    module: str = ""

    # -- availability -------------------------------------------------------
    def is_available(self) -> bool:
        return self.find_command() is not None or self.module_available()

    def find_command(self) -> Optional[list[str]]:
        return find_command(self.name)

    def module_available(self) -> bool:
        return bool(self.module) and module_available(self.module)

    def should_run_in_process(self) -> bool:
        """Prefer the in-process API when we can't spawn a real subprocess."""
        if self.find_command() is not None:
            return False
        return self.module_available()

    def base_cmd(self) -> Optional[list[str]]:
        return self.find_command()

    # -- metadata -----------------------------------------------------------
    def probe(self, url: str, cfg) -> Optional[MediaInfo]:
        """Fetch metadata for `url` without downloading.

        Best-effort: return None when unsupported or the fetch fails. Engines
        that can't provide metadata inherit this no-op.
        """
        return None
