"""yt-dlp engine wrapper (subprocess or in-process)."""
from __future__ import annotations

from pathlib import Path

from ..config import Config
from ..platforms import Detected
from .base import BaseEngine, EngineResult, run_subprocess
from .ffmpeg import ffmpeg_dir

QUALITY_MAP = {
    "best":  "bv*+ba/b",
    "1080p": "bv*[height<=1080]+ba/b[height<=1080]",
    "720p":  "bv*[height<=720]+ba/b[height<=720]",
    "480p":  "bv*[height<=480]+ba/b[height<=480]",
    "360p":  "bv*[height<=360]+ba/b[height<=360]",
    "audio": "ba/b",
}


def _download_opts(out_dir: Path, det: Detected, cfg: Config) -> dict:
    """Build a yt-dlp options dict (shared by subprocess args and in-process API)."""
    out_tpl = _output_template(out_dir, det, cfg)

    opts: dict = {
        "outtmpl": out_tpl,
        "nopart": False,
        "retries": 5,
        "fragment_retries": 5,
        "concurrent_fragment_downloads": cfg.concurrent_fragments,
        "ignoreerrors": True,
        "no_warnings": True,
        "quiet": False,
    }
    if cfg.restrict_filenames:
        opts["restrictfilenames"] = True

    if cfg.quality == "audio":
        opts.update({
            "format": QUALITY_MAP["audio"],
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "0"}
            ],
        })
    else:
        opts["format"] = QUALITY_MAP.get(cfg.quality, QUALITY_MAP["best"])
        opts["merge_output_format"] = "mp4"

    if cfg.embed_metadata:
        opts["postprocessors"] = opts.get("postprocessors", []) + [{"key": "FFmpegMetadata"}]
    if cfg.embed_thumbnail and cfg.quality != "audio":
        opts["writethumbnail"] = True
        opts["postprocessors"] = opts.get("postprocessors", []) + [
            {"key": "EmbedThumbnail", "already_have_thumbnail": False}
        ]
    if cfg.cookies_from_browser:
        opts["cookiesfrombrowser"] = (cfg.cookies_from_browser,)

    # Frozen builds inherit a trimmed PATH; help yt-dlp find ffmpeg.
    loc = ffmpeg_dir()
    if loc:
        opts["ffmpeg_location"] = loc

    return opts


def _output_template(out_dir: Path, det: Detected, cfg: Config) -> str:
    uploader_part = "%(uploader,uploader_id,channel)s/" if cfg.subfolder_per_uploader else ""
    if det.platform == "youtube":
        fname = "%(title).150B [%(id)s].%(ext)s"
    else:
        fname = "%(upload_date>%Y-%m-%d,epoch>%Y-%m-%d)s_%(title).100B [%(id)s].%(ext)s"
    return str(out_dir / (uploader_part + fname))


class YtDlpEngine(BaseEngine):
    name = "yt-dlp"
    module = "yt_dlp"

    def download(self, url: str, out_dir: Path, det: Detected, cfg: Config) -> EngineResult:
        if self.should_run_in_process():
            return self._download_in_process(url, out_dir, det, cfg)
        return self._download_subprocess(url, out_dir, det, cfg)

    # -- subprocess ---------------------------------------------------------
    def _download_subprocess(self, url, out_dir, det, cfg) -> EngineResult:
        cmd = self.find_command()
        if cmd is None:
            return EngineResult(False, 127, self.name, out_dir, "yt-dlp not found")

        args = [*cmd, "-o", _output_template(out_dir, det, cfg)]
        args += ["--no-mtime", "--no-warnings", "--ignore-errors",
                 "--retries", "5", "--fragment-retries", "5",
                 "--concurrent-fragments", str(cfg.concurrent_fragments)]
        if cfg.restrict_filenames:
            args.append("--restrict-filenames")

        if cfg.quality == "audio":
            args += ["-f", QUALITY_MAP["audio"], "--extract-audio",
                     "--audio-format", "mp3", "--audio-quality", "0"]
        else:
            args += ["-f", QUALITY_MAP.get(cfg.quality, QUALITY_MAP["best"]),
                     "--merge-output-format", "mp4"]

        if cfg.embed_metadata:
            args.append("--embed-metadata")
        if cfg.embed_thumbnail and cfg.quality != "audio":
            args.append("--embed-thumbnail")
        if cfg.cookies_from_browser:
            args += ["--cookies-from-browser", cfg.cookies_from_browser]

        loc = ffmpeg_dir()
        if loc:
            args += ["--ffmpeg-location", loc]

        args.append(url)
        code = run_subprocess(args)
        return EngineResult(code == 0, code, self.name, out_dir)

    # -- in-process ---------------------------------------------------------
    def _download_in_process(self, url, out_dir, det, cfg) -> EngineResult:
        try:
            import yt_dlp  # type: ignore
        except ImportError:
            return EngineResult(False, 127, self.name, out_dir, "yt_dlp module not bundled")

        opts = _download_opts(out_dir, det, cfg)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                code = ydl.download([url])
            # yt-dlp returns None/0 on success
            ok = code in (0, None)
            return EngineResult(ok, code or 0, self.name, out_dir)
        except Exception as exc:  # noqa: BLE001
            return EngineResult(False, 1, self.name, out_dir, str(exc))
