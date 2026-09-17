"""Shared engine helpers."""
from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class EngineResult:
    ok: bool
    exit_code: int
    engine: str
    output_dir: Path
    message: str = ""


def find_command(name: str) -> Optional[list[str]]:
    """Return runnable command list, preferring PATH exe, else python -m module."""
    exe = shutil.which(name)
    if exe:
        return [exe]
    module_alias = {
        "yt-dlp": "yt_dlp",
        "gallery-dl": "gallery_dl",
        "instaloader": "instaloader",
    }
    mod = module_alias.get(name)
    if mod:
        try:
            __import__(mod)
            return [sys.executable, "-m", mod]
        except ImportError:
            return None
    return None


def run_subprocess(cmd: Sequence[str], *, quiet: bool = False) -> int:
    """Run subprocess, streaming stdout/stderr to terminal. Returns exit code."""
    try:
        proc = subprocess.run(
            list(cmd),
            check=False,
            stdout=None if not quiet else subprocess.DEVNULL,
            stderr=None if not quiet else subprocess.DEVNULL,
        )
        return proc.returncode
    except FileNotFoundError:
        return 127
    except KeyboardInterrupt:
        return 130


class BaseEngine:
    name: str = "base"

    def is_available(self) -> bool:
        return find_command(self.name) is not None

    def base_cmd(self) -> Optional[list[str]]:
        return find_command(self.name)
