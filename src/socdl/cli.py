"""socdl command-line entry point."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import click

from . import __version__, history, updater
from . import config as cfgmod
from .i18n import set_lang, t
from .platforms import detect_platform
from .router import download as route_download
from .router import probe as route_probe
from .ui import blank as ui_blank
from .ui import (
    console,
    err,
    fmt_bytes,
    fmt_eta,
    fmt_speed,
    hr,
    kv,
    make_progress,
    muted,
    notice,
    ok,
    print_banner,
    print_help_table,
    print_history,
    print_media_info,
    print_queue,
    print_stats,
    prompt_url,
    warn,
)

URL_RE = re.compile(r"https?://\S+")

SUBCOMMANDS = {"watch", "history", "config", "update", "detect"}


# ---------------------------------------------------------------------------
# Windows UTF-8 sanity
# ---------------------------------------------------------------------------
def _fix_windows_encoding() -> None:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
        os.system("")


# ---------------------------------------------------------------------------
def _load_cfg_and_lang(lang_override: Optional[str] = None) -> cfgmod.Config:
    cfg = cfgmod.load()
    set_lang(lang_override or cfg.language or "en")
    return cfg


def _extract_urls(text: str) -> list[str]:
    return [m.group(0).rstrip(",;)]}") for m in URL_RE.finditer(text or "")]


def _read_batch_file(path: str) -> list[str]:
    urls: list[str] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            urls.extend(_extract_urls(line) or ([line] if line.startswith("http") else []))
    return urls


def _maybe_notify_update() -> None:
    info = updater.is_outdated()
    if info:
        current, latest = info
        muted(t("update_available", current=current, latest=latest))


# ---------------------------------------------------------------------------
def _fetch_and_show_info(url: str, det, cfg: cfgmod.Config):
    """Probe link metadata and render the info panel. Returns MediaInfo|None."""
    muted(t("info_fetching"))
    info = route_probe(url, det, cfg)
    if info is not None:
        print_media_info(info)
    return info


def _handle_url(url: str, cfg: cfgmod.Config) -> bool:
    url = url.strip().rstrip(",;")
    det = detect_platform(url)

    hr()
    kv(t("platform"), det.label)
    kv(t("kind"),     det.kind)
    kv(t("url"),      url)

    if det.platform == "unknown":
        warn(t("unknown_platform"))

    info = _fetch_and_show_info(url, det, cfg)

    with make_progress() as progress:
        task = progress.add_task(f"{t('downloading')}...", start=True,
                                 total=None, detail=t("prog_unknown"))

        def on_engine(name: str) -> None:
            progress.update(task, description=f"{t('downloading')} · [muted]{name}[/muted]",
                            detail=t("prog_unknown"))

        def on_progress(info) -> None:
            if info.status == "finished":
                progress.update(task, completed=100, total=100,
                                detail=t("prog_processing"))
                return

            size = t("prog_size",
                     downloaded=fmt_bytes(info.downloaded),
                     total=fmt_bytes(info.total) if info.total else "?")
            bits = [size]
            if info.speed:
                bits.append(fmt_speed(info.speed))
            if info.eta is not None:
                bits.append(t("prog_eta", eta=fmt_eta(info.eta)))
            detail = "  ".join(bits)

            if info.total:
                progress.update(task, total=info.total, completed=info.downloaded,
                                detail=detail)
            else:
                progress.update(task, total=None, detail=detail)

        result = route_download(url, det, cfg,
                                progress_cb=on_progress, on_engine=on_engine)

    if result.ok:
        ok(t("success", path=str(result.output_dir)))
    else:
        err(t("fail_generic", code=result.exit_code) +
            (f"  {result.message}" if result.message else ""))
        if det.platform == "instagram" and not cfg.instagram_login:
            muted(t("ig_login_needed"))
        elif det.platform == "facebook" and not cfg.cookies_from_browser:
            muted(t("fb_login_needed"))

    if cfg.log_history:
        history.record(
            platform=det.platform,
            kind=det.kind,
            url=url,
            engine=result.engine,
            status="success" if result.ok else "failed",
            output_dir=str(result.output_dir),
            message=result.message,
            title=(info.title if info else ""),
            uploader=(info.uploader if info else ""),
            view_count=(info.view_count if info else None),
            like_count=(info.like_count if info else None),
            comment_count=(info.comment_count if info else None),
            share_count=(info.share_count if info else None),
        )
    return result.ok


# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------
QUIT_WORDS = {"quit", "exit", "q", "bye", ":q", ":quit"}
PATH_COMMANDS = {"open", "config"}


@dataclass
class QueueItem:
    """A URL waiting to be downloaded."""

    url: str
    platform: str = "?"


def _drain_queue(items: list["QueueItem"], cfg: cfgmod.Config,
                 state: "_InteractionState") -> None:
    """Download every queued item, reporting a final summary."""
    total = len(items)
    if not total:
        warn(t("queue_empty"))
        return

    notice(t("queue_start", n=total), "accent")
    ok_count = 0
    fail_count = 0
    for i, item in enumerate(items, start=1):
        muted(t("queue_item", i=i, n=total, url=item.url))
        ok_dl = _handle_url(item.url, cfg)
        state.remember(item.url, ok_dl)
        if ok_dl:
            ok_count += 1
        else:
            fail_count += 1
        console.print()

    style = "ok" if fail_count == 0 else "warn"
    notice(t("queue_done", ok=ok_count, fail=fail_count), style)
    items.clear()


def _interactive(cfg: cfgmod.Config) -> None:
    _print_intro(cfg)
    state = _InteractionState()

    while True:
        try:
            raw = prompt_url()
        except KeyboardInterrupt:
            console.print()
            warn(t("goodbye"))
            break

        if not raw:
            continue

        if raw.startswith("/"):
            parts = raw[1:].split(maxsplit=1)
            cmd = parts[0].lower() if parts else ""
            arg = parts[1] if len(parts) > 1 else ""
            keep_going = _handle_command(cmd, arg, cfg, state)
            if not keep_going:
                break
            # Commands that trigger OS side-effects (open/config) can leave the
            # terminal cursor in a weird place; reset cleanly.
            if cmd in PATH_COMMANDS:
                ui_blank()
            continue

        if raw.lower() in QUIT_WORDS:
            break

        urls = _extract_urls(raw)
        if not urls:
            warn(t("no_url"))
            continue

        # A single link downloads right away. Multiple links are queued so
        # each one gets its own progress bar and the user can review/run the
        # batch with /queue run.
        if len(urls) == 1:
            ok_dl = _handle_url(urls[0], cfg)
            state.remember(urls[0], ok_dl)
            console.print()
            continue

        for u in urls:
            state.queue.append(QueueItem(url=u, platform=detect_platform(u).platform))
        ok(t("queue_added_many", n=len(urls)))
        muted(t("queue_queued_n", n=len(state.queue)))
        muted(t("queue_hint_auto"))
        console.print()

    ok(t("goodbye"))


class _InteractionState:
    """Tiny bit of session memory for interactive niceties (e.g. /clip)."""

    def __init__(self) -> None:
        self.last_url: Optional[str] = None
        self.last_ok: Optional[bool] = None
        self.queue: list[QueueItem] = []

    def remember(self, url: str, ok: bool) -> None:
        self.last_url = url
        self.last_ok = ok


def _print_intro(cfg: cfgmod.Config) -> None:
    print_banner()
    kv(t("folder"), str(cfg.resolved_output_dir()))
    notice(t("prompt_hint"), "muted")
    console.print()


def _handle_command(cmd: str, arg: str, cfg: cfgmod.Config, state: "_InteractionState") -> bool:
    """Return False to exit the interactive loop."""
    # --- exit ---
    if cmd in QUIT_WORDS:
        return False

    # --- help ---
    if cmd in ("help", "h", "?"):
        print_help_table()
        return True

    # --- config ---
    if cmd == "config":
        path = cfgmod.config_path()
        if _open_path(path):
            ok(t("cmd_opened", path=str(path)))
        else:
            warn(t("cmd_open_fail", path=str(path)))
        return True

    # --- history ---
    if cmd == "history":
        print_history(history.recent(limit=20))
        return True

    # --- stats ---
    if cmd == "stats":
        print_stats(history.stats())
        return True

    # --- info [url] ---
    if cmd in ("info", "meta"):
        value = arg.strip() or state.last_url or ""
        if not value:
            warn(t("cmd_info_empty"))
            return True
        urls = _extract_urls(value)
        if not urls:
            warn(t("cmd_info_usage"))
            return True
        for u in urls:
            det = detect_platform(u)
            hr()
            kv(t("platform"), det.label)
            kv(t("kind"),     det.kind)
            kv(t("url"),      u)
            info = _fetch_and_show_info(u, det, cfg)
            if info is None:
                muted(t("info_unavailable"))
        return True

    # --- open [path] ---
    if cmd == "open":
        target = Path(arg).expanduser() if arg else cfg.resolved_output_dir()
        if not target.exists():
            warn(t("cmd_path_not_found", path=str(target)))
            return True
        if _open_path(target):
            ok(t("cmd_opened", path=str(target)))
        else:
            warn(t("cmd_open_fail", path=str(target)))
        return True

    # --- paste ---
    if cmd == "paste":
        try:
            import pyperclip
            text = pyperclip.paste()
        except Exception:
            text = ""
        urls = _extract_urls(text)
        if not urls:
            warn(t("watch_no_clip"))
        else:
            for u in urls:
                ok_dl = _handle_url(u, cfg)
                state.remember(u, ok_dl)
            console.print()
        return True

    # --- clip [value] ---
    if cmd == "clip":
        value = arg.strip() or state.last_url or ""
        if not value:
            warn(t("cmd_clip_empty"))
            return True
        try:
            import pyperclip
            pyperclip.copy(value)
            ok(t("cmd_clip_copied", value=value))
        except Exception:
            warn(t("cmd_clip_usage"))
        return True

    # --- watch ---
    if cmd == "watch":
        _run_watcher(cfg)
        return True

    # --- clear ---
    if cmd == "clear":
        console.clear()
        _print_intro(cfg)
        return True

    # --- queue ---
    if cmd == "queue":
        _handle_queue(arg, cfg, state)
        return True

    # --- lang ---
    if cmd == "lang":
        lang = (arg or "").strip().lower()
        if lang in ("en", "id"):
            set_lang(lang)
            cfg.language = lang
            cfgmod.save(cfg)
            ok(t("cfg_saved"))
        else:
            warn(t("cmd_lang_invalid"))
        return True

    warn(t("cmd_unknown", cmd=cmd))
    return True


def _handle_queue(arg: str, cfg: cfgmod.Config, state: "_InteractionState") -> None:
    """Handle `/queue ...` subcommands: add | run | list | clear."""
    parts = arg.split(maxsplit=1)
    sub = parts[0].lower() if parts else ""
    rest = parts[1] if len(parts) > 1 else ""

    # /queue (no sub) or /queue list -> show queue
    if sub in ("", "list", "ls", "show"):
        print_queue(state.queue)
        if state.queue:
            muted(t("queue_queued_n", n=len(state.queue)))
        return

    # /queue add <url...>  (also accepts bare URLs: /queue <url>)
    if sub in ("add", "a", "push", "+") or _looks_like_url(sub) or _extract_urls(sub):
        text = f"{sub} {rest}" if sub not in ("add", "a", "push", "+") else rest
        urls = _extract_urls(text)
        if not urls:
            warn(t("queue_no_url"))
            return
        for u in urls:
            state.queue.append(QueueItem(url=u, platform=detect_platform(u).platform))
        if len(urls) == 1:
            ok(t("queue_added", url=urls[0]))
        else:
            ok(t("queue_added_many", n=len(urls)))
        muted(t("queue_queued_n", n=len(state.queue)))
        return

    # /queue run -> download everything now
    if sub in ("run", "start", "go", "download"):
        _drain_queue(state.queue, cfg, state)
        return

    # /queue clear -> empty the queue
    if sub in ("clear", "reset", "flush"):
        n = len(state.queue)
        state.queue.clear()
        ok(t("queue_cleared", n=n))
        return

    warn(t("queue_usage"))


def _open_path(path: Path) -> bool:
    """Open a file/folder with the OS default handler. Returns True on success."""
    try:
        if path.suffix:
            path.parent.mkdir(parents=True, exist_ok=True)
        else:
            path.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False

    try:
        if sys.platform == "win32":
            os.startfile(str(path))  # noqa: S606
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
        return True
    except Exception:
        return False


def _run_watcher(cfg: cfgmod.Config) -> None:
    from .watcher import watch
    ok(t("watch_started"))
    muted(t("watch_hint"))
    try:
        watch(on_link=lambda u: (notice(t("watch_detected"), "accent"), _handle_url(u, cfg)))
    except KeyboardInterrupt:
        console.print()
        warn(t("watch_stopped"))


# ---------------------------------------------------------------------------
# Click CLI
# ---------------------------------------------------------------------------
@click.group(
    invoke_without_command=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
@click.version_option(__version__, "-V", "--version", prog_name="socdl")
@click.option("--lang", type=click.Choice(["en", "id"]), default=None, help="Force UI language.")
@click.option("-o", "--output", type=click.Path(file_okay=False), default=None,
              help="Override output directory.")
@click.option("-q", "--quality",
              type=click.Choice(["best", "1080p", "720p", "480p", "360p", "audio"]),
              default=None, help="Override quality.")
@click.option("-f", "--file", "batch_file", type=click.Path(exists=True, dir_okay=False),
              default=None, help="Download URLs listed in a text file (one per line).")
@click.pass_context
def cli(ctx: click.Context, lang: Optional[str], output: Optional[str],
        quality: Optional[str], batch_file: Optional[str]) -> None:
    """socdl - download photos & videos from social media, fast."""
    _fix_windows_encoding()
    cfg = _load_cfg_and_lang(lang)
    if output:
        cfg.output_dir = output
    if quality:
        cfg.quality = quality

    ctx.obj = cfg

    if ctx.invoked_subcommand is None and batch_file:
        print_banner()
        for u in _read_batch_file(batch_file):
            _handle_url(u, cfg)
        if cfg.check_updates:
            _maybe_notify_update()
    elif ctx.invoked_subcommand is None:
        _interactive(cfg)
        if cfg.check_updates:
            _maybe_notify_update()


# ---- subcommands ----

@cli.command("watch")
@click.pass_obj
def cmd_watch(cfg: cfgmod.Config) -> None:
    """Start clipboard watcher - auto-download any supported link you copy."""
    print_banner()
    _run_watcher(cfg)


@cli.command("history")
@click.option("-n", "--limit", default=20, show_default=True, help="How many entries to show.")
@click.option("-p", "--platform", default=None, help="Filter by platform.")
@click.option("--clear", "do_clear", is_flag=True, help="Delete all history.")
@click.pass_obj
def cmd_history(cfg: cfgmod.Config, limit: int, platform: Optional[str], do_clear: bool) -> None:
    """Show or clear download history."""
    if do_clear:
        n = history.clear()
        ok(f"Deleted {n} entries.")
        return
    print_history(history.recent(limit=limit, platform=platform))


@cli.command("config")
@click.option("--show", is_flag=True, help="Print current config to stdout.")
@click.option("--reset", is_flag=True, help="Overwrite with defaults.")
@click.option("--set", "kv_pairs", multiple=True, metavar="KEY=VALUE",
              help="Set a config value, e.g. --set quality=1080p")
@click.pass_obj
def cmd_config(cfg: cfgmod.Config, show: bool, reset: bool, kv_pairs: tuple[str, ...]) -> None:
    """Show or edit the config file."""
    if reset:
        cfg = cfgmod.Config()
        cfgmod.save(cfg)
        ok(t("cfg_saved"))

    if kv_pairs:
        for pair in kv_pairs:
            if "=" not in pair:
                warn(f"Ignored: {pair}")
                continue
            k, v = pair.split("=", 1)
            k = k.strip()
            v = v.strip()
            if not hasattr(cfg, k):
                warn(f"Unknown key: {k}")
                continue
            current = getattr(cfg, k)
            if isinstance(current, bool):
                setattr(cfg, k, v.lower() in ("1", "true", "yes", "on"))
            elif isinstance(current, int):
                try:
                    setattr(cfg, k, int(v))
                except ValueError:
                    warn(f"Not an int: {v}")
            else:
                setattr(cfg, k, v)
        cfgmod.save(cfg)
        ok(t("cfg_saved"))

    if show or (not reset and not kv_pairs):
        console.print(f"[muted]{cfgmod.config_path()}[/muted]")
        for k, v in cfg.to_dict().items():
            kv(k, str(v))


@cli.command("update")
def cmd_update() -> None:
    """Upgrade underlying downloaders (yt-dlp, instaloader, gallery-dl)."""
    pkgs = ["yt-dlp", "instaloader", "gallery-dl"]
    notice(f"Upgrading: {', '.join(pkgs)}", "accent")
    code = subprocess.call([sys.executable, "-m", "pip", "install", "--upgrade", *pkgs])
    if code == 0:
        ok("Downloaders upgraded.")
    else:
        err("Upgrade failed.")

    info = updater.is_outdated()
    if info:
        current, latest = info
        notice(t("update_available", current=current, latest=latest), "warn")
    else:
        ok(t("update_uptodate", current=__version__))


@cli.command("detect")
@click.argument("url")
def cmd_detect(url: str) -> None:
    """Print detected platform/kind for a URL (debug helper)."""
    det = detect_platform(url)
    kv("platform", det.platform)
    kv("kind", det.kind)
    kv("target", str(det.target))
    kv("label", det.label)
    kv("folder", det.folder_name)


# ---------------------------------------------------------------------------
def _looks_like_url(s: str) -> bool:
    return s.startswith(("http://", "https://"))


def _grab_flag_value(argv: list[str], flags: tuple[str, ...]) -> Optional[str]:
    for i, tok in enumerate(argv):
        if tok in flags and i + 1 < len(argv):
            return argv[i + 1]
        for f in flags:
            if tok.startswith(f + "="):
                return tok.split("=", 1)[1]
    return None


def _quick_download_mode(argv: list[str]) -> bool:
    """Handle bare `socdl <url>...` before Click sees the URL as a subcommand."""
    for tok in argv:
        if tok in SUBCOMMANDS or tok in ("-h", "--help", "-V", "--version"):
            return False
    urls = [a for a in argv if _looks_like_url(a)]
    if not urls:
        return False

    lang = _grab_flag_value(argv, ("--lang",))
    output = _grab_flag_value(argv, ("-o", "--output"))
    quality = _grab_flag_value(argv, ("-q", "--quality"))
    batch_file = _grab_flag_value(argv, ("-f", "--file"))

    cfg = _load_cfg_and_lang(lang)
    if output:
        cfg.output_dir = output
    if quality:
        cfg.quality = quality

    print_banner()
    all_urls = list(urls)
    if batch_file:
        all_urls += _read_batch_file(batch_file)
    for u in all_urls:
        _handle_url(u, cfg)
    if cfg.check_updates:
        _maybe_notify_update()
    return True


def main() -> None:
    _fix_windows_encoding()
    argv = sys.argv[1:]
    try:
        if argv and _quick_download_mode(argv):
            return
        cli(standalone_mode=True)
    except KeyboardInterrupt:
        console.print()
        sys.exit(130)


if __name__ == "__main__":
    main()
