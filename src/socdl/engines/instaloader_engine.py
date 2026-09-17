"""instaloader engine wrapper (Instagram specialist)."""
from __future__ import annotations

from pathlib import Path

from ..config import Config
from ..platforms import Detected
from .base import BaseEngine, EngineResult, run_subprocess


class InstaloaderEngine(BaseEngine):
    name = "instaloader"

    def download(self, url: str, out_dir: Path, det: Detected, cfg: Config) -> EngineResult:
        cmd = self.base_cmd()
        if cmd is None:
            return EngineResult(False, 127, self.name, out_dir, "instaloader not found")

        dirname = str(out_dir / "{profile}") if cfg.subfolder_per_uploader else str(out_dir)
        filename = "{date_utc:%Y-%m-%d}_{shortcode}"

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

        if det.kind in ("post", "reel"):
            if not det.target:
                return EngineResult(False, 2, self.name, out_dir, "cannot parse shortcode")
            args += ["--", f"-{det.target}"]
        elif det.kind == "profile":
            if not det.target:
                return EngineResult(False, 2, self.name, out_dir, "cannot parse username")
            args += [det.target]
        elif det.kind == "story":
            username = det.target if isinstance(det.target, str) else ""
            if not username:
                return EngineResult(False, 2, self.name, out_dir, "cannot parse username")
            args += ["--stories", ":stories", username]
        else:
            if det.target:
                args += ["--", f"-{det.target}"]
            else:
                return EngineResult(False, 2, self.name, out_dir, "unsupported IG url")

        code = run_subprocess(args)
        return EngineResult(code == 0, code, self.name, out_dir)
