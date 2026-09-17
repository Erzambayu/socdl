"""Locate ffmpeg/ffprobe on the host system.

Frozen binaries (PyInstaller) often inherit a trimmed PATH, so a plain
`shutil.which("ffmpeg")` can miss installs that the user's shell finds.
We probe PATH first, then a handful of well-known install locations.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Optional

_WINDOWS_GLOBS = [
    # winget (Gyan.FFmpeg)
    r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\*\bin\ffmpeg.exe",
    r"%LOCALAPPDATA%\Microsoft\WinGet\Packages\Gyan.FFmpeg*\**\bin\ffmpeg.exe",
    # scoop
    r"%USERPROFILE%\scoop\shims\ffmpeg.exe",
    r"%USERPROFILE%\scoop\apps\ffmpeg\current\bin\ffmpeg.exe",
    # chocolatey
    r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
    # common manual installs
    r"C:\ffmpeg\bin\ffmpeg.exe",
    r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
]

_POSIX_PATHS = [
    "/usr/bin/ffmpeg",
    "/usr/local/bin/ffmpeg",
    "/opt/homebrew/bin/ffmpeg",
    "/snap/bin/ffmpeg",
]


def find_ffmpeg() -> Optional[str]:
    """Return the path to an ffmpeg executable, or None."""
    found = shutil.which("ffmpeg")
    if found:
        return found

    if sys.platform == "win32":
        for pattern in _WINDOWS_GLOBS:
            expanded = os.path.expandvars(pattern)
            try:
                # Path.glob needs an anchored pattern split into anchor + relative.
                anchor = Path(expanded.split("*", 1)[0]).anchor or str(Path.cwd().anchor)
                rel = expanded[len(anchor):]
                for p in Path(anchor).glob(rel):
                    if p.is_file():
                        return str(p)
            except (OSError, ValueError):
                continue
    else:
        for p in _POSIX_PATHS:
            if Path(p).is_file():
                return p

    return None


def ffmpeg_dir() -> Optional[str]:
    """Return the *directory* containing ffmpeg, suitable for yt-dlp's
    `ffmpeg_location` option (which accepts either a dir or a file path).
    """
    exe = find_ffmpeg()
    return str(Path(exe).parent) if exe else None


__all__ = ["find_ffmpeg", "ffmpeg_dir"]
