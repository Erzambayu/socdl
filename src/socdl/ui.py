"""Rich TUI helpers: banner, tables, prompts."""
from __future__ import annotations

from collections.abc import Iterable

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from . import __version__
from .i18n import t

THEME = Theme({
    "brand":   "bold magenta",
    "accent":  "cyan",
    "ok":      "bold green",
    "warn":    "yellow",
    "err":     "bold red",
    "muted":   "grey62",
    "label":   "bold cyan",
    "value":   "white",
    "prompt":  "bold magenta",
})

console = Console(theme=THEME, highlight=False)


def print_banner() -> None:
    title = Text()
    title.append("  socdl ", style="brand")
    title.append(f"v{__version__}", style="muted")
    subtitle = Text(t("banner_subtitle"), style="accent")
    tagline = Text(t("app_tagline"), style="muted")

    body = Align.center(
        Text.assemble(title, "\n", subtitle, "\n", tagline),
        vertical="middle",
    )
    console.print(Panel(body, border_style="brand", padding=(1, 4)))


def kv(label: str, value: str) -> None:
    console.print(f"  [label]{label:<10}[/label] [value]{value}[/value]")


def hr() -> None:
    console.rule(style="muted")


def print_help_table() -> None:
    tbl = Table(title=t("cmd_help_title"), title_style="brand", border_style="muted")
    tbl.add_column("Command", style="accent", no_wrap=True)
    tbl.add_column("Description", style="value")
    tbl.add_row("/help",    t("cmd_help_help"))
    tbl.add_row("/quit",    t("cmd_help_quit"))
    tbl.add_row("/config",  t("cmd_help_config"))
    tbl.add_row("/history", t("cmd_help_history"))
    tbl.add_row("/stats",   t("cmd_help_stats"))
    tbl.add_row("/queue",   t("cmd_help_queue"))
    tbl.add_row("/watch",   t("cmd_help_watch"))
    tbl.add_row("/paste",   t("cmd_help_paste"))
    tbl.add_row("/clip",    t("cmd_help_clip"))
    tbl.add_row("/open",    t("cmd_help_open"))
    tbl.add_row("/clear",   t("cmd_help_clear"))
    tbl.add_row("/lang",    t("cmd_help_lang"))
    console.print(tbl)
    console.print(f"[muted]{t('cmd_help_urls')}[/muted]")


def print_stats(st: "object") -> None:
    """Render a history.Stats object as a colored summary."""
    from rich.columns import Columns
    from rich.panel import Panel

    def box(label: str, value: int, style: str) -> Panel:
        body = Text.assemble(
            (f"{value}\n", f"bold {style}"),
            (label, "muted"),
        )
        return Panel(Align.center(body), border_style=style, padding=(0, 2))

    grid = Columns(
        [
            box(t("stats_total"), st.total, "brand"),
            box(t("stats_success"), st.success, "ok"),
            box(t("stats_failed"), st.failed, "err"),
        ],
        equal=True,
        expand=True,
    )
    console.print(
        Panel(grid, title=f"[brand]{t('stats_title')}[/brand]", border_style="muted")
    )

    if st.by_platform:
        tbl = Table(title=t("stats_by_platform"), title_style="accent", border_style="muted")
        tbl.add_column(t("hist_col_platform"), style="accent")
        tbl.add_column("Count", style="value", justify="right")
        for plat, n in st.by_platform:
            tbl.add_row(plat or "unknown", str(n))
        console.print(tbl)


def print_history(rows: Iterable) -> None:
    rows = list(rows)
    if not rows:
        console.print(f"[muted]{t('hist_empty')}[/muted]")
        return
    tbl = Table(title=t("hist_title"), title_style="brand", border_style="muted")
    tbl.add_column(t("hist_col_when"),     style="muted", no_wrap=True)
    tbl.add_column(t("hist_col_platform"), style="accent")
    tbl.add_column(t("hist_col_url"),      style="value", overflow="fold", max_width=60)
    tbl.add_column(t("hist_col_status"),   style="ok")
    for r in rows:
        status_style = "ok" if r.status == "success" else "err"
        tbl.add_row(
            r.timestamp.replace("T", " "),
            r.platform,
            r.url,
            f"[{status_style}]{r.status}[/{status_style}]",
        )
    console.print(tbl)


def fmt_bytes(n) -> str:
    """Human-readable byte size, e.g. '12.4 MB'."""
    if not n:
        return "0 B"
    n = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def fmt_speed(bps) -> str:
    """Human-readable transfer speed, e.g. '3.2 MB/s'."""
    if not bps:
        return "?"
    return f"{fmt_bytes(bps)}/s"


def fmt_eta(seconds) -> str:
    """Human-readable ETA, e.g. '1m 05s'."""
    if seconds is None:
        return "?"
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return "?"
    if seconds < 0:
        return "?"
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m}m {s:02d}s"
    h, m = divmod(m, 60)
    return f"{h}h {m:02d}m"


def make_progress() -> "Progress":
    """Build the shared Rich Progress bar used for downloads."""
    return Progress(
        SpinnerColumn(style="brand"),
        TextColumn("[accent]{task.description}"),
        BarColumn(bar_width=None),
        TextColumn("[muted]{task.fields[detail]}"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    )


def print_queue(items: Iterable) -> None:
    """Render the queued URLs as a table."""
    items = list(items)
    if not items:
        console.print(f"[muted]{t('queue_empty')}[/muted]")
        return
    tbl = Table(title=t("queue_title"), title_style="brand", border_style="muted")
    tbl.add_column(t("queue_col_num"), style="muted", justify="right", no_wrap=True)
    tbl.add_column(t("queue_col_platform"), style="accent", no_wrap=True)
    tbl.add_column(t("queue_col_url"), style="value", overflow="fold", max_width=60)
    for i, item in enumerate(items, start=1):
        plat = getattr(item, "platform", "") or "?"
        url = getattr(item, "url", str(item))
        tbl.add_row(str(i), plat, url)
    console.print(tbl)


def prompt_url() -> str:
    """Read a line from the user, styled. Flushes any pending output first."""
    console.file.flush()
    try:
        return console.input("[prompt]socdl >[/prompt] ").strip()
    except EOFError:
        return "/quit"


def blank() -> None:
    """Print a blank line (used after side-effects like opening a folder)."""
    console.print()


def notice(msg: str, style: str = "accent") -> None:
    console.print(f"[{style}]{msg}[/{style}]")


def ok(msg: str) -> None: notice(msg, "ok")
def warn(msg: str) -> None: notice(msg, "warn")
def err(msg: str) -> None: notice(msg, "err")
def muted(msg: str) -> None: notice(msg, "muted")


__all__ = [
    "console", "print_banner", "kv", "hr", "print_help_table",
    "print_history", "print_stats", "print_queue", "prompt_url", "blank",
    "notice", "ok", "warn", "err", "muted",
    "fmt_bytes", "fmt_speed", "fmt_eta", "make_progress",
]
