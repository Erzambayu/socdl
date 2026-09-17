"""socdl command-line entry point."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

import click
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from . import __version__, history, updater
from . import config as cfgmod
from .i18n import set_lang, t
from .platforms import detect_platform
from .router import download as route_download
from .ui import (
    console,
    err,
    hr,
    kv,
    muted,
    notice,
    ok,
    print_banner,
    print_help_table,
    print_history,
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
def _handle_url(url: str, cfg: cfgmod.Config) -> bool:
    url = url.strip().rstrip(",;")
    det = detect_platform(url)

    hr()
    kv(t("platform"), det.label)
    kv(t("kind"),     det.kind)
    kv(t("url"),      url)

    if det.platform == "unknown":
        warn(t("unknown_platform"))

    engine_used = ["-"]
    with Progress(
        SpinnerColumn(style="brand"),
        TextColumn("[accent]{task.description}"),
        BarColumn(bar_width=None),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task(f"{t('downloading')}...", start=True, total=None)

        def on_engine(name: str) -> None:
            engine_used[0] = name
            progress.update(task, description=f"{t('downloading')} · [muted]{name}[/muted]")

        result = route_download(url, det, cfg, progress_cb=on_engine)

    if result.ok:
        ok(t("success", path=str(result.output_dir)))
    else:
        err(t("fail_generic", code=result.exit_code) +
            (f"  {result.message}" if result.message else ""))
        if det.platform == "instagram" and not cfg.instagram_login:
            muted(t("ig_login_needed"))

    if cfg.log_history:
        history.record(
            platform=det.platform,
            kind=det.kind,
            url=url,
            engine=result.engine,
            status="success" if result.ok else "failed",
            output_dir=str(result.output_dir),
            message=result.message,
        )
    return result.ok


# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------
def _interactive(cfg: cfgmod.Config) -> None:
    print_banner()
    kv(t("folder"), str(cfg.resolved_output_dir()))
    muted(t("prompt_hint"))
    console.print()

    while True:
        try:
            raw = prompt_url()
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        if not raw:
            continue

        if raw.startswith("/"):
            parts = raw[1:].split(maxsplit=1)
            cmd = parts[0].lower() if parts else ""
            arg = parts[1] if len(parts) > 1 else ""
            if not _handle_command(cmd, arg, cfg):
                break
            continue

        if raw.lower() in ("q", "quit", "exit", ":q"):
            break

        urls = _extract_urls(raw)
        if not urls:
            warn(t("no_url"))
            continue
        for u in urls:
            _handle_url(u, cfg)

    ok(t("goodbye"))


def _handle_command(cmd: str, arg: str, cfg: cfgmod.Config) -> bool:
    if cmd in ("quit", "exit", "q"):
        return False
    if cmd == "help":
        print_help_table()
        return True
    if cmd == "config":
        _open_path(cfgmod.config_path())
        notice(str(cfgmod.config_path()))
        return True
    if cmd == "history":
        print_history(history.recent(limit=20))
        return True
    if cmd == "open":
        _open_path(cfg.resolved_output_dir())
        return True
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
                _handle_url(u, cfg)
        return True
    if cmd == "watch":
        _run_watcher(cfg)
        return True
    if cmd == "lang":
        lang = (arg or "").strip().lower()
        if lang in ("en", "id"):
            set_lang(lang)
            cfg.language = lang
            cfgmod.save(cfg)
            ok(t("cfg_saved"))
        else:
            warn("Usage: /lang en | /lang id")
        return True
    warn(f"Unknown command: /{cmd}")
    return True


def _open_path(path: Path) -> None:
    if path.suffix:
        path.parent.mkdir(parents=True, exist_ok=True)
    else:
        path.mkdir(parents=True, exist_ok=True)
    try:
        if sys.platform == "win32":
            os.startfile(str(path))  # noqa
        elif sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except Exception:
        pass


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
