"""gallery-dl engine wrapper."""
from __future__ import annotations

from pathlib import Path

from ..config import Config
from ..platforms import Detected
from .base import BaseEngine, EngineResult, run_subprocess


class GalleryDLEngine(BaseEngine):
    name = "gallery-dl"

    def download(self, url: str, out_dir: Path, det: Detected, cfg: Config) -> EngineResult:
        cmd = self.base_cmd()
        if cmd is None:
            return EngineResult(False, 127, self.name, out_dir, "gallery-dl not found")

        if det.platform == "instagram":
            subdir = "{username}" if cfg.subfolder_per_uploader else ""
            fname = "{date:%Y-%m-%d}_{shortcode}_{num}.{extension}"
        elif det.platform == "tiktok":
            subdir = "{user[unique_id]|user[nickname]|author}" if cfg.subfolder_per_uploader else ""
            fname = "{date:%Y-%m-%d}_{id}_{num:>02}.{extension}"
        elif det.platform == "twitter":
            subdir = "{user[name]}" if cfg.subfolder_per_uploader else ""
            fname = "{date:%Y-%m-%d}_{tweet_id}_{num}.{extension}"
        elif det.platform == "reddit":
            subdir = "{subreddit}" if cfg.subfolder_per_uploader else ""
            fname = "{id}_{num:>02}.{extension}"
        else:
            subdir = ""
            fname = "{filename}.{extension}"

        args = [
            *cmd,
            "-D", str(out_dir),
            "--directory", subdir,
            "-f", fname,
            "--retries", "5",
            "--no-mtime",
        ]
        if cfg.cookies_from_browser:
            args += ["--cookies-from-browser", cfg.cookies_from_browser]

        args.append(url)
        code = run_subprocess(args)
        return EngineResult(code == 0, code, self.name, out_dir)
