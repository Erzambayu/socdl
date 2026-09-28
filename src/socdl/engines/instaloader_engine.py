"""instaloader engine wrapper (Instagram specialist)."""
from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import Optional

from ..config import Config
from ..platforms import Detected, detect_platform
from .base import BaseEngine, EngineResult, MediaInfo, run_subprocess

# Cookies that carry the login. They are read from a file the user supplies and
# written to the local session file; none of their values are ever logged or
# included in any message.
REQUIRED_COOKIES = ("sessionid", "csrftoken")


def _parse_cookie_export(raw: str) -> list[tuple[str, str]]:
    """Read cookies from a browser-extension export.

    Supports the JSON array shape (EditThisCookie, Get cookies.txt, etc.) and
    Netscape ``cookies.txt``. Returns ``[(name, value), ...]`` for Instagram only.
    """
    text = raw.strip()
    if not text:
        return []

    if text[0] in "[{":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return []
        if isinstance(data, dict):
            data = data.get("cookies", [])
        if not isinstance(data, list):
            return []
        out: list[tuple[str, str]] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            value = item.get("value")
            domain = item.get("domain", "")
            if not name or value is None:
                continue
            if domain and "instagram.com" not in str(domain):
                continue
            out.append((str(name), str(value)))
        return out

    # Netscape format: domain \t flag \t path \t secure \t expiry \t name \t value
    out = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 7:
            continue
        domain, _flag, _path, _secure, _expiry, name, value = parts[:7]
        if "instagram.com" in domain:
            out.append((name, value))
    return out


def _username_from_cookies(pairs) -> str:
    """Best-effort username from a session (falls back to a placeholder)."""
    get = dict(pairs).get
    return get("ds_user_id") or get("ds_user") or "socdl"


class InstaloaderEngine(BaseEngine):
    name = "instaloader"
    module = "instaloader"

    @staticmethod
    def default_session_path() -> Path:
        """Where the reusable Instagram session cookie file lives."""
        from ..config import data_dir

        return data_dir() / "instagram.session"

    @staticmethod
    def login(session_path: Path, username: str = "") -> tuple[bool, str]:
        """Log into Instagram interactively and persist the session to `session_path`.

        Returns ``(ok, message)``. With an empty `username` instaloader prompts
        for credentials interactively; otherwise it uses the given username.
        """
        try:
            import instaloader  # type: ignore
        except ImportError:
            return False, "instaloader is not installed (pip install instaloader)"

        session_path.parent.mkdir(parents=True, exist_ok=True)
        loader = instaloader.Instaloader(
            quiet=False,
            save_metadata=False,
            download_comments=False,
            download_geotags=False,
            download_videos=False,
            download_pictures=False,
        )
        loader.login(username or None, interactive=True)
        return InstaloaderEngine._persist(loader, session_path)

    @staticmethod
    def import_cookies(cookie_file: Path, session_path: Path) -> tuple[bool, str]:
        """Build a session file from exported Instagram cookies.

        Accepts the two formats browser extensions actually export:
        a JSON array of cookie objects, or Netscape ``cookies.txt``.
        """
        cookie_file = cookie_file.expanduser()
        if not cookie_file.exists():
            return False, f"cookie file not found: {cookie_file}"
        try:
            raw = cookie_file.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            return False, f"cannot read {cookie_file}: {exc}"

        pairs = _parse_cookie_export(raw)
        if not pairs:
            return False, f"no Instagram cookies found in {cookie_file}"

        names = {name for name, _ in pairs}
        missing = [name for name in REQUIRED_COOKIES if name not in names]
        if missing:
            return False, (
                f"missing {', '.join(repr(m) for m in missing)} in the export - "
                "these cookies are not a logged-in Instagram session. Log into "
                "instagram.com in your browser first, then re-export."
            )

        try:
            import instaloader  # type: ignore
        except ImportError:
            return False, "instaloader is not installed (pip install instaloader)"

        loader = instaloader.Instaloader(
            quiet=True,
            save_metadata=False,
            download_comments=False,
            download_geotags=False,
            download_videos=False,
            download_pictures=False,
        )
        username = _username_from_cookies(pairs)
        try:
            for name, value in pairs:
                loader.context._session.cookies.set(
                    name, value, domain=".instagram.com", path="/"
                )
            loader.context.username = username
            loader.context._session.headers.update(
                {"X-CSRFToken": loader.context._session.cookies.get_dict()["csrftoken"]}
            )
        except Exception as exc:  # noqa: BLE001
            return False, f"could not build session: {exc}"

        ok_flag, message = InstaloaderEngine._persist(loader, session_path)
        if ok_flag:
            message += f" ({len(pairs)} cookies imported)"
        return ok_flag, message

    @staticmethod
    def _persist(loader, session_path: Path) -> tuple[bool, str]:
        """Write the loader's current cookies to `session_path` (pickle, instaloader's format)."""
        try:
            session_path.parent.mkdir(parents=True, exist_ok=True)
            with session_path.open("wb") as fh:
                pickle.dump(loader.save_session(), fh)
        except Exception as exc:  # noqa: BLE001
            return False, f"login ok but could not save session: {exc}"
        return True, f"Session saved to {session_path}"

    @staticmethod
    def session_path_for(cfg: Config) -> Optional[Path]:
        """Resolve which session file to use.

        ``cfg.instagram_login`` wins when set. Otherwise fall back to the
        default session file, but only when it actually exists, so an empty
        config still means "anonymous".
        """
        if cfg.instagram_login:
            return Path(cfg.instagram_login).expanduser()
        default = InstaloaderEngine.default_session_path()
        return default if default.exists() else None

    @staticmethod
    def apply_session(loader, cfg: Config) -> bool:
        """Load the saved session into `loader`. Returns True if one was loaded.

        instaloader's ``load_session_from_file`` takes a *username* as its first
        argument (the filename is derived from it), so we pass the session data
        directly instead.
        """
        session_path = InstaloaderEngine.session_path_for(cfg)
        if session_path is None or not session_path.exists():
            return False
        try:
            with session_path.open("rb") as fh:
                data = pickle.load(fh)
            username = _username_from_cookies(data.items()) if data else ""
            loader.load_session(username, data)
            return True
        except Exception:  # noqa: BLE001 - session is an optimisation, never fatal
            return False

    def download(self, url: str, out_dir: Path, det: Detected, cfg: Config,
                 progress=None) -> EngineResult:
        # instaloader exposes no stable byte-level progress hook; ``progress``
        # is accepted for a uniform engine interface and ignored here.
        if self.should_run_in_process():
            return self._download_in_process(url, out_dir, det, cfg)
        return self._download_subprocess(url, out_dir, det, cfg)

    # -- metadata -----------------------------------------------------------
    def probe(self, url: str, cfg: Config) -> Optional[MediaInfo]:
        """Fetch like/comment counts for an Instagram post (best-effort)."""
        try:
            import instaloader  # type: ignore
        except ImportError:
            return None

        target = self._target_arg(detect_platform(url))
        if target is None or target[0] != "post":
            return None

        try:
            loader = instaloader.Instaloader(quiet=True, save_metadata=False)
            self.apply_session(loader, cfg)
            post = instaloader.Post.from_shortcode(loader.context, target[1])
        except Exception:  # noqa: BLE001 - metadata is best-effort
            return None

        return MediaInfo(
            engine=self.name,
            title=(post.caption or "").strip().splitlines()[0] if post.caption else "",
            uploader=post.owner_username,
            duration=float(post.video_duration) if post.is_video and post.video_duration else None,
            upload_date=post.date_utc.strftime("%Y%m%d") if post.date_utc else "",
            like_count=int(post.likes) if post.likes is not None else None,
            comment_count=int(post.comments) if post.comments is not None else None,
            view_count=int(post.video_view_count) if post.is_video and post.video_view_count else None,
        )

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
        if self.session_path_for(cfg) is not None:
            # The session is a pickle only instaloader's API can read, so the
            # CLI has to run through the in-process engine to use it.
            return self._download_in_process(url, out_dir, det, cfg)

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

        self.apply_session(L, cfg)

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
