"""yt-dlp engine wrapper (subprocess or in-process)."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from ..config import Config
from ..platforms import Detected
from .base import BaseEngine, EngineResult, ProgressInfo, run_subprocess
from .ffmpeg import ffmpeg_dir


def _quality_format(quality: str) -> str:
    """Build a yt-dlp format selector for a quality preset.

    The selector always ends in an unrestricted fallback (``/b``) so it never
    hard-fails when a site does not expose formats matching the cap. Height
    caps also consider ``width`` so portrait videos (reels, shorts, vertical
    TikTok/FB clips) are matched correctly — for those, the *height* is the
    long side and a plain ``height<=720`` filter would exclude everything.
    """
    if quality == "audio":
        return "ba/b"

    cap = {
        "best":  None,
        "1080p": 1080,
        "720p":  720,
        "480p":  480,
        "360p":  360,
    }.get(quality)
    if cap is None:
        return "bv*+ba/b"

    # Filter on the *shorter* side so portrait and landscape both work: for a
    # landscape video height is the short side; for portrait it is width.
    within = f"[height<={cap}][width<={cap}]"
    # 1) best video+audio within the cap   2) any combined within the cap
    # 3) best video+audio uncapped         4) any single best (last resort)
    return f"bv*{within}+ba/bv*{within}/b{within}/bv*+ba/b"


QUALITY_MAP = {
    "best":  "bv*+ba/b",
    "1080p": _quality_format("1080p"),
    "720p":  _quality_format("720p"),
    "480p":  _quality_format("480p"),
    "360p":  _quality_format("360p"),
    "audio": "ba/b",
}


def _download_opts(out_dir: Path, det: Detected, cfg: Config,
                   progress_hook=None) -> dict:
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

    if progress_hook is not None:
        # We render our own Rich progress bar, so silence yt-dlp's own
        # console progress lines to avoid interleaved output.
        opts["quiet"] = True
        opts["noprogress"] = True
        opts["progress_hooks"] = [progress_hook]

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

    def download(self, url: str, out_dir: Path, det: Detected, cfg: Config,
                 progress=None) -> EngineResult:
        if self.should_run_in_process():
            return self._download_in_process(url, out_dir, det, cfg, progress)
        return self._download_subprocess(url, out_dir, det, cfg, progress)

    # -- progress helpers ---------------------------------------------------
    @staticmethod
    def _progress_from_hook(d: dict) -> ProgressInfo:
        """Map a yt-dlp progress_hook dict to a ProgressInfo."""
        status = d.get("status", "downloading")
        downloaded = float(d.get("downloaded_bytes") or 0)
        total = d.get("total_bytes") or d.get("total_bytes_estimate")
        total = float(total) if total else None
        speed = d.get("speed")
        eta = d.get("eta")
        return ProgressInfo(
            status="finished" if status == "finished" else ("error" if status == "error" else "downloading"),
            downloaded=downloaded,
            total=total,
            speed=float(speed) if speed else None,
            eta=float(eta) if eta else None,
            filename=str(d.get("filename") or d.get("info_dict", {}).get("title") or ""),
        )

    @staticmethod
    def _progress_from_template(line: str) -> Optional[ProgressInfo]:
        """Parse a `--progress-template` line emitted by the subprocess mode."""
        marker = "SOCDL_PROGRESS"
        if marker not in line:
            return None
        payload = line.split(marker, 1)[1].lstrip("|:").strip()
        parts = payload.split("|")
        if len(parts) < 5:
            return None

        def _num(value: str) -> Optional[float]:
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        downloaded = _num(parts[1]) or 0.0
        total = _num(parts[2])
        return ProgressInfo(
            status=parts[0] or "downloading",
            downloaded=downloaded,
            total=total,
            speed=_num(parts[3]),
            eta=_num(parts[4]),
        )

    # -- subprocess ---------------------------------------------------------
    def _download_subprocess(self, url, out_dir, det, cfg, progress=None) -> EngineResult:
        cmd = self.find_command()
        if cmd is None:
            return EngineResult(False, 127, self.name, out_dir, "yt-dlp not found")

        args = [*cmd, "-o", _output_template(out_dir, det, cfg)]
        args += ["--no-mtime", "--no-warnings", "--ignore-errors",
                 "--retries", "5", "--fragment-retries", "5",
                 "--concurrent-fragments", str(cfg.concurrent_fragments),
                 "--newline", "--no-colors", "--progress"]

        on_line = None
        if progress is not None:
            # status|downloaded|total|speed|eta
            args += ["--progress-template",
                     "download:SOCDL_PROGRESS|%(progress.status)s|%(progress.downloaded_bytes)s"
                     "|%(progress.total_bytes,progress.total_bytes_estimate)s"
                     "|%(progress.speed)s|%(progress.eta)s"]

            def on_line(line: str) -> None:
                info = self._progress_from_template(line)
                if info is not None:
                    progress(info)
                elif line.strip():
                    # Non-progress output (e.g. post-processing) -> keep visible.
                    pass

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
        code = run_subprocess(args, on_line=on_line)
        return EngineResult(code == 0, code, self.name, out_dir)

    # -- in-process ---------------------------------------------------------
    def _download_in_process(self, url, out_dir, det, cfg, progress=None) -> EngineResult:
        try:
            import yt_dlp  # type: ignore
        except ImportError:
            return EngineResult(False, 127, self.name, out_dir, "yt_dlp module not bundled")

        hook = None
        if progress is not None:
            def hook(d: dict) -> None:
                progress(self._progress_from_hook(d))

        opts = _download_opts(out_dir, det, cfg, progress_hook=hook)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                code = ydl.download([url])
            # yt-dlp returns None/0 on success
            ok = code in (0, None)
            return EngineResult(ok, code or 0, self.name, out_dir)
        except Exception as exc:  # noqa: BLE001
            return EngineResult(False, 1, self.name, out_dir, str(exc))
