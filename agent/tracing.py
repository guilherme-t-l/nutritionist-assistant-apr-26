"""SQLite-backed trace recorder for LLM calls.

Phase 3's job is to *measure* the agent. To measure it we need a record of
what was sent and what came back, per call. SQLite is overkill for one user
on one laptop, but it's:

  - Stdlib (no new dependency).
  - A single file on disk that other tools (DB Browser, the `sqlite3` CLI,
    pandas) can open. No server to run.
  - Future-proof: Phase 3.5 wants to add `iterations` / `converged` columns
    and Phase 4 wants tool-call rows. SQL handles both with `ALTER TABLE` /
    extra columns; a JSON file would not.

Teaching note (Chapter ~12 — file/IO and stdlib): `sqlite3` is built into
Python. `with sqlite3.connect(...) as conn` opens the file, runs your code,
commits on clean exit and rolls back on exception — same context-manager
pattern as `with open(...)` for files.

This module is intentionally *passive*: nothing here calls `record_trace`
on its own. The eval runner does it explicitly. Production routes are not
wired in this phase (see Phase 3.5).
"""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# Project root / traces.db. Resolves relative to THIS file so the eval
# runner finds the same db whether invoked from the project root or not.
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "traces.db"


# `kind` lets us distinguish trace types without making a new table per
# phase. Phase 3 only writes "plan" rows. Phase 3.5 will add "refine".
# Phase 4 will add "tool_call". Same table, new `kind` values.
@dataclass
class Trace:
    """One row in the traces table, before insertion."""

    profile_label: str
    kind: str  # "plan" | "refine" | "tool_call" (Phase 4)
    system_prompt: str
    user_messages: list[dict[str, str]]  # [{"role": ..., "content": ...}, ...]
    raw_reply: str
    latency_ms: int
    error: str | None = None
    # Free-form bag for phase-specific extras (e.g. iteration index).
    # Stored as a JSON blob so the schema doesn't need to change every phase.
    extra: dict[str, Any] = field(default_factory=dict)


# `CREATE TABLE IF NOT EXISTS` makes init_db safe to call repeatedly —
# no error on the second run, no destructive recreate.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS traces (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ts              TEXT NOT NULL,           -- ISO-8601, UTC
    profile_label   TEXT NOT NULL,
    kind            TEXT NOT NULL,
    system_prompt   TEXT NOT NULL,
    user_messages   TEXT NOT NULL,           -- JSON-encoded list
    raw_reply       TEXT NOT NULL,
    latency_ms      INTEGER NOT NULL,
    error           TEXT,                    -- NULL when call succeeded
    extra           TEXT NOT NULL DEFAULT '{}'  -- JSON-encoded dict
);
"""


def init_db(db_path: Path | str = DEFAULT_DB_PATH) -> Path:
    """Create traces.db (and the table) if they don't exist. Returns the path.

    Idempotent: safe to call on every runner invocation.
    """
    # `Path(...)` handles both str and Path inputs uniformly.
    path = Path(db_path)
    # `parent.mkdir(parents=True, exist_ok=True)` ensures the directory
    # exists. No-op if it already does. Belt and suspenders.
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.executescript(_SCHEMA)
    return path


def record_trace(trace: Trace, db_path: Path | str = DEFAULT_DB_PATH) -> int:
    """Insert one trace row. Returns the new row id.

    Caller is responsible for measuring `latency_ms` and constructing the
    `Trace`. Keeping this dumb means tests can build a Trace by hand without
    any timing tricks.
    """
    path = Path(db_path)
    # ISO-8601 with 'Z' suffix = unambiguously UTC. `time.gmtime()` is the
    # UTC version of `time.localtime()`. Chosen over `datetime.utcnow()`
    # because the latter returns a naive datetime that's easy to misuse.
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    with sqlite3.connect(path) as conn:
        # `?` placeholders + tuple of values = the only safe way to pass
        # data to SQL. Never use f-strings or `%` to build SQL — that's
        # how SQL injection happens. Even on a local-only DB, the habit matters.
        cursor = conn.execute(
            """
            INSERT INTO traces (
                ts, profile_label, kind, system_prompt,
                user_messages, raw_reply, latency_ms, error, extra
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ts,
                trace.profile_label,
                trace.kind,
                trace.system_prompt,
                json.dumps(trace.user_messages),
                trace.raw_reply,
                trace.latency_ms,
                trace.error,
                json.dumps(trace.extra),
            ),
        )
        # `cursor.lastrowid` returns the id assigned by AUTOINCREMENT.
        # Useful so the caller can reference the row in follow-up writes.
        new_id = cursor.lastrowid
    # `lastrowid` is `int | None` on the type stubs; in practice the INSERT
    # above guarantees an int. The `or 0` keeps mypy happy without lying.
    return new_id or 0


def fetch_all(db_path: Path | str = DEFAULT_DB_PATH) -> list[dict[str, Any]]:
    """Read every trace row back as a list of plain dicts.

    Mostly for tests and the runner's debug output. Production will not call
    this — querying happens in `sqlite3` CLI or a notebook.
    """
    path = Path(db_path)
    with sqlite3.connect(path) as conn:
        # `row_factory = sqlite3.Row` gives back row objects you can index by
        # column name (`row["ts"]`) instead of by integer position. Cleaner.
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM traces ORDER BY id").fetchall()
    # Decode the JSON blob columns back into Python objects on the way out,
    # so callers don't need to remember which fields were stringified.
    return [_row_to_dict(row) for row in rows]


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a sqlite3.Row into a plain dict and decode JSON columns."""
    data = dict(row)
    data["user_messages"] = json.loads(data["user_messages"])
    data["extra"] = json.loads(data["extra"])
    return data


# Convenience: build a Trace from a dataclass-like dict.
# Mainly here so callers in the runner don't write `Trace(**{...})` by hand.
def trace_from_dict(payload: dict[str, Any]) -> Trace:
    """Build a Trace from the kind of dict the runner accumulates."""
    # `**asdict(Trace(...))` round-trips fine because every field has a
    # default or a value here.
    return Trace(**payload)


__all__ = [
    "DEFAULT_DB_PATH",
    "Trace",
    "init_db",
    "record_trace",
    "fetch_all",
    "trace_from_dict",
    "asdict",  # re-exported so callers don't need a separate dataclasses import
]
