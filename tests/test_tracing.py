"""Unit tests for agent/tracing.py.

Uses a temporary database per test (pytest's `tmp_path` fixture) so test
runs never touch the real `traces.db` and never leak state between tests.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from agent.tracing import Trace, fetch_all, init_db, record_trace


def test_init_db_creates_file_and_table(tmp_path: Path) -> None:
    db = tmp_path / "traces.db"
    init_db(db)
    assert db.exists()
    # Inspect via raw sqlite to confirm the table exists with the right cols.
    with sqlite3.connect(db) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(traces)")}
    assert {"id", "ts", "profile_label", "kind", "raw_reply", "extra"} <= cols


def test_init_db_is_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "traces.db"
    init_db(db)
    # Calling twice must not error and must not wipe data.
    record_trace(_sample_trace(), db)
    init_db(db)
    rows = fetch_all(db)
    assert len(rows) == 1


def test_record_trace_round_trip(tmp_path: Path) -> None:
    db = tmp_path / "traces.db"
    init_db(db)
    new_id = record_trace(_sample_trace(), db)
    assert new_id >= 1

    rows = fetch_all(db)
    assert len(rows) == 1
    row = rows[0]
    assert row["profile_label"] == "veg-celiac"
    assert row["kind"] == "plan"
    assert row["raw_reply"].startswith("{")
    assert row["latency_ms"] == 123
    assert row["error"] is None
    # JSON columns are decoded back to Python on the way out.
    assert row["user_messages"] == [{"role": "user", "content": "hello"}]
    assert row["extra"] == {"note": "first try"}


def test_record_trace_persists_error(tmp_path: Path) -> None:
    db = tmp_path / "traces.db"
    init_db(db)
    bad = Trace(
        profile_label="bad",
        kind="plan",
        system_prompt="sys",
        user_messages=[{"role": "user", "content": "x"}],
        raw_reply="",
        latency_ms=42,
        error="LLM returned 500",
    )
    record_trace(bad, db)
    rows = fetch_all(db)
    assert rows[0]["error"] == "LLM returned 500"


def test_fetch_all_orders_by_id(tmp_path: Path) -> None:
    db = tmp_path / "traces.db"
    init_db(db)
    for i in range(3):
        record_trace(_sample_trace(label=f"profile-{i}"), db)
    rows = fetch_all(db)
    assert [r["profile_label"] for r in rows] == ["profile-0", "profile-1", "profile-2"]


def _sample_trace(label: str = "veg-celiac") -> Trace:
    return Trace(
        profile_label=label,
        kind="plan",
        system_prompt="You are a nutritionist.",
        user_messages=[{"role": "user", "content": "hello"}],
        raw_reply='{"meals": []}',
        latency_ms=123,
        extra={"note": "first try"},
    )
