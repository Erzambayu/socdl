"""Clipboard watcher: auto-download when a supported URL is copied."""
from __future__ import annotations

import re
import time
from typing import Callable, Optional

import pyperclip

from .platforms import detect_platform

URL_RE = re.compile(r"https?://\S+")


def _extract_url(text: str) -> Optional[str]:
    if not text:
        return None
    m = URL_RE.search(text.strip())
    return m.group(0).rstrip(",;)]}") if m else None


def watch(
    on_link: Callable[[str], None],
    interval: float = 0.7,
    supported_only: bool = True,
    stop_check: Optional[Callable[[], bool]] = None,
) -> None:
    """Poll clipboard forever, dispatch new URLs to `on_link`."""
    last_seen = ""
    try:
        last_seen = pyperclip.paste() or ""
    except pyperclip.PyperclipException:
        pass

    while True:
        if stop_check and stop_check():
            return
        try:
            current = pyperclip.paste() or ""
        except pyperclip.PyperclipException:
            time.sleep(interval * 2)
            continue

        if current and current != last_seen:
            last_seen = current
            url = _extract_url(current)
            if url:
                if supported_only:
                    det = detect_platform(url)
                    if det.platform != "unknown":
                        on_link(url)
                else:
                    on_link(url)
        time.sleep(interval)


__all__ = ["watch"]
