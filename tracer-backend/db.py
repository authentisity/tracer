import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).parent / 'tracer.db'

_SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    intent      TEXT    NOT NULL,
    created_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS stages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id),
    stage_type  TEXT    NOT NULL,
    status      TEXT    NOT NULL,
    input_json  TEXT,
    output_json TEXT,
    error       TEXT,
    created_at  TEXT    NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(_SCHEMA)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Projects ──────────────────────────────────────────────────────────────────

def create_project(name: str, intent: str) -> int:
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO projects (name, intent, created_at) VALUES (?, ?, ?)",
            (name, intent, _now()),
        )
        return cur.lastrowid


def get_project(project_id: int) -> Optional[dict]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        return dict(row) if row else None


# ── Stages ────────────────────────────────────────────────────────────────────

def _decode_stage(row: sqlite3.Row) -> dict:
    d = dict(row)
    d['input_json'] = json.loads(d['input_json']) if d['input_json'] else None
    d['output_json'] = json.loads(d['output_json']) if d['output_json'] else None
    return d


def get_stages_for_project(project_id: int) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM stages WHERE project_id = ? ORDER BY created_at",
            (project_id,),
        ).fetchall()
        return [_decode_stage(r) for r in rows]


def get_stage(stage_id: int) -> Optional[dict]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM stages WHERE id = ?", (stage_id,)
        ).fetchone()
        return _decode_stage(row) if row else None


def upsert_stage(
    project_id: int,
    stage_type: str,
    status: str,
    *,
    input_data: Optional[dict] = None,
    output_data: Optional[dict] = None,
    error: Optional[str] = None,
) -> int:
    """Insert or update the single stage row for (project_id, stage_type). Returns the row id."""
    input_json = json.dumps(input_data) if input_data is not None else None
    output_json = json.dumps(output_data) if output_data is not None else None

    with _connect() as conn:
        existing = conn.execute(
            "SELECT id FROM stages WHERE project_id = ? AND stage_type = ?",
            (project_id, stage_type),
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE stages
                   SET status = ?, input_json = ?, output_json = ?, error = ?
                   WHERE id = ?""",
                (status, input_json, output_json, error, existing['id']),
            )
            return existing['id']

        cur = conn.execute(
            """INSERT INTO stages
               (project_id, stage_type, status, input_json, output_json, error, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (project_id, stage_type, status, input_json, output_json, error, _now()),
        )
        return cur.lastrowid


def update_stage_output(stage_id: int, output_data: dict) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE stages SET output_json = ?, status = 'complete', error = NULL WHERE id = ?",
            (json.dumps(output_data), stage_id),
        )
