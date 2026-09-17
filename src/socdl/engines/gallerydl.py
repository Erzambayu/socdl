"""gallery-dl engine wrapper (subprocess or in-process)."""
from __future__ import annotations

from pathlib import Path

from ..config import Config
from ..platforms import Detected
from .base import BaseEngine, EngineResult, run_subprocess


class GalleryDLEngine(BaseEngine):
    name = "gallery-dl"
    module = "gallery_dl"

    def download(self, url: str, out_dir: Path, det: Detected, cfg: Config) -> EngineResult:
        if self.should_run_in_process():
            return self._download_in_process(url, out_dir, det, cfg)
        return self._download_subprocess(url, out_dir, det, cfg)

    # -- config shared by both modes ----------------------------------------
    @staticmethod
    def _dir_and_filename(det: Detected, cfg: Config) -> tuple[str, str]:
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
        return subdir, fname

    # -- subprocess ---------------------------------------------------------
    def _download_subprocess(self, url, out_dir, det, cfg) -> EngineResult:
        cmd = self.find_command()
        if cmd is None:
            return EngineResult(False, 127, self.name, out_dir, "gallery-dl not found")

        subdir, fname = self._dir_and_filename(det, cfg)
        args = [*cmd, "-D", str(out_dir), "--directory", subdir, "-f", fname,
                "--retries", "5", "--no-mtime"]
        if cfg.cookies_from_browser:
            args += ["--cookies-from-browser", cfg.cookies_from_browser]
        args.append(url)

        code = run_subprocess(args)
        return EngineResult(code == 0, code, self.name, out_dir)

    # -- in-process ---------------------------------------------------------
    def _download_in_process(self, url, out_dir, det, cfg) -> EngineResult:
        try:
            from gallery_dl import config as gdl_config
            from gallery_dl import exception as gdl_exc
            from gallery_dl import job as gdl_job
        except ImportError:
            return EngineResult(False, 127, self.name, out_dir, "gallery_dl module not bundled")

        subdir, fname = self._dir_and_filename(det, cfg)

        # Mirror the CLI's -D / --directory / -f options.
        gdl_config.set(("extractor",), "base-directory", str(out_dir))
        gdl_config.set(("extractor", "base"), "filename", fname)
        if subdir:
            gdl_config.set(("extractor", "base"), "directory", [subdir])
        if cfg.cookies_from_browser:
            gdl_config.set(("extractor", "base"), "cookies", cfg.cookies_from_browser)

        try:
            gdl_job.DownloadJob(url).run()
            return EngineResult(True, 0, self.name, out_dir)
        except gdl_exc.GalleryDLException as exc:
            return EngineResult(False, 1, self.name, out_dir, str(exc))
        except Exception as exc:  # noqa: BLE001
            return EngineResult(False, 1, self.name, out_dir, str(exc))
