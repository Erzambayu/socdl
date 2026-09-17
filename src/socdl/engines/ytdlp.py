"""yt-dlp engine wrapper."""
from __future__ import annotations

from pathlib import Path

from ..config import Config
from ..platforms import Detected
from .base import BaseEngine, EngineResult, run_subprocess

QUALITY_MAP = {
    "best":  "bv*+ba/b",
    "1080p": "bv*[height<=1080]+ba/b[height<=1080]",
    "720p":  "bv*[height<=720]+ba/b[height<=720]",
    "480p":  "bv*[height<=480]+ba/b[height<=480]",
    "360p":  "bv*[height<=360]+ba/b[height<=360]",
    "audio": "ba/b",
}


class YtDlpEngine(BaseEngine):
    name = "yt-dlp"

    def download(self, url: str, out_dir: Path, det: Detected, cfg: Config) -> EngineResult:
        cmd = self.base_cmd()
        if cmd is None:
            return EngineResult(False, 127, self.name, out_dir, "yt-dlp not found")

        out_tpl = self._output_template(out_dir, det, cfg)

        args = [
            *cmd,
            "-o", out_tpl,
            "--no-mtime",
            "--no-warnings",
            "--ignore-errors",
            "--retries", "5",
            "--fragment-retries", "5",
            "--concurrent-fragments", str(cfg.concurrent_fragments),
        ]
        if cfg.restrict_filenames:
            args.append("--restrict-filenames")

        if cfg.quality == "audio":
            args += [
                "-f", QUALITY_MAP["audio"],
                "--extract-audio",
                "--audio-format", "mp3",
                "--audio-quality", "0",
            ]
        else:
            args += ["-f", QUALITY_MAP.get(cfg.quality, QUALITY_MAP["best"])]
            args += ["--merge-output-format", "mp4"]

        if cfg.embed_metadata:
            args.append("--embed-metadata")
        if cfg.embed_thumbnail and cfg.quality != "audio":
            args.append("--embed-thumbnail")
        if cfg.cookies_from_browser:
            args += ["--cookies-from-browser", cfg.cookies_from_browser]

        args.append(url)
        code = run_subprocess(args)
        return EngineResult(code == 0, code, self.name, out_dir)

    @staticmethod
    def _output_template(out_dir: Path, det: Detected, cfg: Config) -> str:
        uploader_part = "%(uploader,uploader_id,channel)s/" if cfg.subfolder_per_uploader else ""
        if det.platform == "youtube":
            fname = "%(title).150B [%(id)s].%(ext)s"
        else:
            fname = "%(upload_date>%Y-%m-%d,epoch>%Y-%m-%d)s_%(title).100B [%(id)s].%(ext)s"
        return str(out_dir / (uploader_part + fname))
