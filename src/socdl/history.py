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
        c.commit()


def record(*, platform: str, kind: str, url: str, engine: str,
           status: str, output_dir: str, message: str = "") -> None:
    init()
    with _conn() as c:
        c.execute(
            """INSERT INTO downloads
               (timestamp, platform, kind, url, engine, status, output_dir, message)
               VALUES (?,?,?,?,?,?,?,?)""",
            (datetime.now().isoformat(timespec="seconds"),
             platform, kind, url, engine, status, output_dir, message),
        )
        c.commit()


def recent(limit: int = 20, platform: Optional[str] = None) -> list[HistoryEntry]:
    init()
    with _conn() as c:
        if platform:
            rows = c.execute(
                """SELECT id, timestamp, platform, kind, url, engine, status, output_dir, message
                   FROM downloads WHERE platform=? ORDER BY id DESC LIMIT ?""",
                (platform, limit),
            ).fetchall()
        else:
            rows = c.execute(
                """SELECT id, timestamp, platform, kind, url, engine, status, output_dir, message
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


__all__ = ["HistoryEntry", "record", "recent", "clear", "db_path"]
