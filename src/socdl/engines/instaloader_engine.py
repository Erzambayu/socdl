"""instaloader engine wrapper (Instagram specialist)."""
from __future__ import annotations

from pathlib import Path

from ..config import Config
from ..platforms import Detected
from .base import BaseEngine, EngineResult, run_subprocess


class InstaloaderEngine(BaseEngine):
    name = "instaloader"
    module = "instaloader"

    def download(self, url: str, out_dir: Path, det: Detected, cfg: Config) -> EngineResult:
        if self.should_run_in_process():
            return self._download_in_process(url, out_dir, det, cfg)
        return self._download_subprocess(url, out_dir, det, cfg)

    # -- CLI args shared by both modes --------------------------------------
    @staticmethod
    def _template_patterns(out_dir: Path, cfg: Config) -> tuple[str, str]:
        dirname = str(out_dir / "{profile}") if cfg.subfolder_per_uploader else str(out_dir)
        filename = "{date_utc:%Y-%m-%d}_{shortcode}"
        return dirname, filename

    def _target_arg(self, det: Detected):
        if det.kind in ("post", "reel"):
            return ("post", det.target) if det.target else None
        if det.kind == "profile":
            return ("profile", det.target) if det.target else None
        if det.kind == "story":
            return ("stories", det.target) if det.target else None
        return ("post", det.target) if det.target else None

    # -- subprocess ---------------------------------------------------------
    def _download_subprocess(self, url, out_dir, det, cfg) -> EngineResult:
        cmd = self.find_command()
        if cmd is None:
            return EngineResult(False, 127, self.name, out_dir, "instaloader not found")

        target = self._target_arg(det)
        if target is None:
            return EngineResult(False, 2, self.name, out_dir, "cannot parse IG url")

        dirname, filename = self._template_patterns(out_dir, cfg)
        args = [
            *cmd,
            "--dirname-pattern", dirname,
            "--filename-pattern", filename,
            "--no-metadata-json",
            "--no-captions",
            "--quiet",
        ]
        if cfg.instagram_login:
            args += ["--login", cfg.instagram_login]

        kind, value = target
        if kind == "post":
            args += ["--", f"-{value}"]
        elif kind == "profile":
            args += [value]
        elif kind == "stories":
            args += ["--stories", ":stories", value]

        code = run_subprocess(args)
        return EngineResult(code == 0, code, self.name, out_dir)

    # -- in-process ---------------------------------------------------------
    def _download_in_process(self, url, out_dir, det, cfg) -> EngineResult:
        try:
            import instaloader  # type: ignore
        except ImportError:
            return EngineResult(False, 127, self.name, out_dir, "instaloader module not bundled")

        target = self._target_arg(det)
        if target is None:
            return EngineResult(False, 2, self.name, out_dir, "cannot parse IG url")

        dirname, filename = self._template_patterns(out_dir, cfg)
        L = instaloader.Instaloader(
            dirname_pattern=dirname,
            filename_pattern=filename,
            save_metadata=False,
            post_metadata_txt_pattern="",
            download_pictures=True,
            download_videos=True,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            quiet=True,
        )

        if cfg.instagram_login:
            try:
                L.load_session_from_file(cfg.instagram_login)
            except Exception:  # noqa: BLE001
                # no saved session; continue anonymously
                pass

        kind, value = target
        try:
            if kind == "post":
                post = instaloader.Post.from_shortcode(L.context, value)
                L.download_post(post, target=post.owner_username)
            elif kind == "profile":
                profile = instaloader.Profile.from_username(L.context, value)
                for post in profile.get_posts():
                    L.download_post(post, target=profile.username)
            elif kind == "stories":
                profile = instaloader.Profile.from_username(L.context, value)
                L.download_stories(userids=[profile.userid])
            return EngineResult(True, 0, self.name, out_dir)
        except Exception as exc:  # noqa: BLE001
            return EngineResult(False, 1, self.name, out_dir, str(exc))
