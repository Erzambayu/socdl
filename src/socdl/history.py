"""SQLite-backed download history."""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import NamedTuple, Optional

from . import config as cfgmod


class HistoryEntry(NamedTuple):
    id: int
    timestamp: str
    platform: str
    kind: str
    url: str
    engine: str
    status: str
    output_dir: str
    message: str
    title: str = ""
    uploader: str = ""
    view_count: Optional[int] = None
    like_count: Optional[int] = None
    comment_count: Optional[int] = None
    share_count: Optional[int] = None


def db_path() -> Path:
    return cfgmod.data_dir() / "history.db"


@contextmanager
def _conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(str(db_path()))
    try:
        yield conn
    finally:
        conn.close()


def init() -> None:
    with _conn() as c:
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS downloads (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp  TEXT NOT NULL,
                platform   TEXT NOT NULL,
                kind       TEXT NOT NULL,
                url        TEXT NOT NULL,
                engine     TEXT NOT NULL,
                status     TEXT NOT NULL,
                output_dir TEXT NOT NULL,
                message    TEXT DEFAULT ''
            )
            """
        )
        _migrate(c)
        c.commit()


_MEDIA_COLUMNS = {
    "title": "TEXT DEFAULT ''",
    "uploader": "TEXT DEFAULT ''",
    "view_count": "INTEGER",
    "like_count": "INTEGER",
    "comment_count": "INTEGER",
    "share_count": "INTEGER",
}


def _migrate(c: sqlite3.Connection) -> None:
    """Add media-info columns to pre-existing databases (idempotent)."""
    existing = {row[1] for row in c.execute("PRAGMA table_info(downloads)")}
    for name, decl in _MEDIA_COLUMNS.items():
        if name not in existing:
            c.execute(f"ALTER TABLE downloads ADD COLUMN {name} {decl}")


_SELECT_COLUMNS = (
    "id, timestamp, platform, kind, url, engine, status, output_dir, message, "
    "title, uploader, view_count, like_count, comment_count, share_count"
)


def record(*, platform: str, kind: str, url: str, engine: str,
           status: str, output_dir: str, message: str = "",
           title: str = "", uploader: str = "",
           view_count: Optional[int] = None, like_count: Optional[int] = None,
           comment_count: Optional[int] = None,
           share_count: Optional[int] = None) -> None:
    init()
    with _conn() as c:
        c.execute(
            """INSERT INTO downloads
               (timestamp, platform, kind, url, engine, status, output_dir,
                message, title, uploader, view_count, like_count,
                comment_count, share_count)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (datetime.now().isoformat(timespec="seconds"),
             platform, kind, url, engine, status, output_dir, message,
             title, uploader, view_count, like_count, comment_count, share_count),
        )
        c.commit()


def recent(limit: int = 20, platform: Optional[str] = None) -> list[HistoryEntry]:
    init()
    with _conn() as c:
        if platform:
            rows = c.execute(
                f"""SELECT {_SELECT_COLUMNS}
                    FROM downloads WHERE platform=? ORDER BY id DESC LIMIT ?""",
                (platform, limit),
            ).fetchall()
        else:
            rows = c.execute(
                f"""SELECT {_SELECT_COLUMNS}
                    FROM downloads ORDER BY id DESC LIMIT ?""",
                (limit,),
            ).fetchall()
    return [HistoryEntry(*r) for r in rows]


def clear() -> int:
    init()
    with _conn() as c:
        cur = c.execute("DELETE FROM downloads")
        c.commit()
        return cur.rowcount


class Stats(NamedTuple):
    total: int
    success: int
    failed: int
    by_platform: list[tuple[str, int]]


def stats() -> Stats:
    """Aggregate download counts overall and per platform."""
    init()
    with _conn() as c:
        total = c.execute("SELECT COUNT(*) FROM downloads").fetchone()[0]
        success = c.execute(
            "SELECT COUNT(*) FROM downloads WHERE status='success'"
        ).fetchone()[0]
        failed = total - success
        rows = c.execute(
            """SELECT platform, COUNT(*) AS n FROM downloads
               GROUP BY platform ORDER BY n DESC"""
        ).fetchall()
    return Stats(total=total, success=success, failed=failed,
                 by_platform=[(r[0], r[1]) for r in rows])


__all__ = ["HistoryEntry", "Stats", "record", "recent", "clear", "stats", "db_path"]
