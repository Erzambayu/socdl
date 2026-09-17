"""Check PyPI for socdl updates (silent, best-effort)."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Optional

from . import __version__

PYPI_URL = "https://pypi.org/pypi/socdl/json"


def latest_version(timeout: float = 3.0) -> Optional[str]:
    try:
        req = urllib.request.Request(PYPI_URL, headers={"User-Agent": f"socdl/{__version__}"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            data = json.load(resp)
        return data.get("info", {}).get("version")
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None


def is_outdated() -> Optional[tuple[str, str]]:
    latest = latest_version()
    if not latest:
        return None
    if _parse(latest) > _parse(__version__):
        return (__version__, latest)
    return None


def _parse(v: str) -> tuple[int, ...]:
    parts = []
    for p in v.split("."):
        num = ""
        for ch in p:
            if ch.isdigit():
                num += ch
            else:
                break
        parts.append(int(num) if num else 0)
    return tuple(parts)


__all__ = ["latest_version", "is_outdated"]
