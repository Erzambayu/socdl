"""Download videos from supported DoodStream mirror pages."""
from __future__ import annotations

import re
import secrets
import string
import time
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests

from ..config import Config
from ..platforms import Detected
from .base import EngineResult, MediaInfo, ProgressInfo

_PASS_MD5 = re.compile(r"\$\.get\(['\"](/pass_md5/[^'\"]+)['\"]")
_TOKEN = re.compile(r"function makePlay\(\).*?\?token=([a-zA-Z0-9]+)&expiry=", re.S)
_VIDEO_ID = re.compile(r"^/(?:d|e)/([a-zA-Z0-9]+)/*$")
_ALPHABET = string.ascii_letters + string.digits


def _player_url(url: str) -> tuple[str, str]:
    parsed = urlsplit(url)
    if parsed.scheme != "https" or (parsed.hostname or "").lower() not in {
        "playmogo.com", "www.playmogo.com",
    }:
        raise ValueError("unsupported DoodStream mirror")
    match = _VIDEO_ID.fullmatch(parsed.path)
    if not match:
        raise ValueError("invalid DoodStream video link")
    video_id = match.group(1)
    return f"{parsed.scheme}://{parsed.netloc}/e/{video_id}", video_id


class DoodStreamEngine:
    name = "doodstream"

    def is_available(self) -> bool:
        return True

    def probe(self, url: str, cfg: Config) -> MediaInfo | None:
        return None

    def download(self, url: str, out_dir: Path, det: Detected, cfg: Config,
                 progress=None) -> EngineResult:
        try:
            player_url, video_id = _player_url(url)
            with requests.Session() as session:
                page = session.get(player_url, timeout=20)
                page.raise_for_status()
                endpoint = _PASS_MD5.search(page.text)
                token = _TOKEN.search(page.text)
                if not endpoint or not token:
                    raise ValueError("DoodStream player did not expose a download URL")

                # The player requests a short-lived base URL and appends a random
                # suffix and timestamp. Never reuse a URL from a previous run.
                base = session.get(
                    urljoin(player_url, endpoint.group(1)),
                    headers={"Referer": player_url}, timeout=20,
                )
                base.raise_for_status()
                media_base = base.text.strip()
                media_host = urlsplit(media_base).hostname
                if not media_base.startswith("https://") or not media_host:
                    raise ValueError("DoodStream returned an invalid media URL")
                suffix = "".join(secrets.choice(_ALPHABET) for _ in range(10))
                media_url = (
                    f"{media_base}{suffix}?token={token.group(1)}"
                    f"&expiry={int(time.time() * 1000)}"
                )
                dest = out_dir / f"{video_id}.mp4"
                part = dest.with_suffix(".mp4.part")
                try:
                    with session.get(media_url, headers={"Referer": player_url},
                                     stream=True, timeout=30) as response:
                        response.raise_for_status()
                        if "video/" not in response.headers.get("Content-Type", "").lower():
                            raise ValueError("DoodStream did not return a video")
                        total = int(response.headers.get("Content-Length") or 0) or None
                        downloaded = 0
                        with part.open("wb") as output:
                            for chunk in response.iter_content(chunk_size=1024 * 256):
                                if chunk:
                                    output.write(chunk)
                                    downloaded += len(chunk)
                                    if progress:
                                        progress(ProgressInfo(downloaded=downloaded,
                                                              total=total, filename=str(dest)))
                    if downloaded == 0 or (total is not None and downloaded != total):
                        raise ValueError("DoodStream download was incomplete")
                    part.replace(dest)
                    if progress:
                        progress(ProgressInfo(status="finished", downloaded=downloaded,
                                              total=total, filename=str(dest)))
                except Exception:
                    part.unlink(missing_ok=True)
                    raise
            return EngineResult(True, 0, self.name, out_dir)
        except (requests.RequestException, OSError, ValueError) as exc:
            return EngineResult(False, 1, self.name, out_dir, str(exc))
