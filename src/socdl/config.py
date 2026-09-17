"""Config loader/writer for socdl."""
from __future__ import annotations

import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import tomli_w
from platformdirs import user_config_dir, user_downloads_dir

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


APP_NAME = "socdl"


def config_dir() -> Path:
    return Path(user_config_dir(APP_NAME, appauthor=False))


def config_path() -> Path:
    return config_dir() / "config.toml"


def data_dir() -> Path:
    """Where history.db, sessions, etc. live."""
    d = config_dir() / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def default_output_dir() -> Path:
    """Default: ~/Downloads/socdl-downloads (avoid clashing with a repo folder named 'socdl')."""
    return Path(user_downloads_dir()) / "socdl-downloads"


@dataclass
class Config:
    # I/O
    output_dir: str = ""                   # empty -> default_output_dir()
    subfolder_per_platform: bool = True
    subfolder_per_uploader: bool = True

    # Behavior
    language: str = "en"                   # "en" | "id"
    quality: str = "best"                  # best|1080p|720p|480p|360p|audio
    embed_metadata: bool = True
    embed_thumbnail: bool = True
    concurrent_fragments: int = 4
    restrict_filenames: bool = True

    # Features
    check_updates: bool = True
    log_history: bool = True

    # Instagram
    instagram_login: str = ""

    # Cookies (for private / age-restricted content)
    cookies_from_browser: str = ""         # chrome|firefox|edge|brave|opera|vivaldi

    def resolved_output_dir(self) -> Path:
        return Path(self.output_dir).expanduser() if self.output_dir else default_output_dir()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load() -> Config:
    path = config_path()
    if not path.exists():
        cfg = Config()
        save(cfg)
        return cfg
    try:
        with path.open("rb") as f:
            data = tomllib.load(f)
        return _from_dict(data)
    except Exception:
        return Config()


def save(cfg: Config) -> Path:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        tomli_w.dump(_to_serializable(cfg.to_dict()), f)
    return path


def _from_dict(data: dict[str, Any]) -> Config:
    known = set(Config.__dataclass_fields__)
    filtered = {k: v for k, v in data.items() if k in known}
    try:
        return Config(**filtered)
    except TypeError:
        return Config()


def _to_serializable(d: dict[str, Any]) -> dict[str, Any]:
    out = {}
    for k, v in d.items():
        out[k] = "" if v is None else v
    return out


__all__ = ["Config", "load", "save", "config_path", "config_dir", "data_dir", "default_output_dir"]
