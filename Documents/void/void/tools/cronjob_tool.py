"""Cronjob tools — manage scheduled jobs from the agent."""

import json
from pathlib import Path

from void.config import ensure_home
from void.tools.registry import register

DB = ensure_home() / "cron.db"


def _conn():
    import sqlite3
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def cronjob_list(limit: int = 20) -> dict:
    conn = _conn()
    try:
        rows = conn.execute("SELECT * FROM cron_jobs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return {"count": len(rows), "jobs": [dict(r) for r in rows]}
    finally:
        conn.close()


def cronjob_create(schedule: str, prompt: str) -> dict:
    """Create a scheduled job. schedule like '30m', 'every 2h', '0 9 * * *'.

    Returns {"error": ...} on an unparseable schedule instead of raising —
    tool handlers must return, not throw, so the agent loop keeps its turn.
    """
    from void.commands.cron_cmd import create_job
    try:
        return create_job(schedule, prompt)
    except ValueError as e:
        return {"error": str(e)}


def cronjob_delete(job_id: str) -> dict:
    conn = _conn()
    try:
        cur = conn.execute("DELETE FROM cron_jobs WHERE id = ?", (job_id,))
        conn.commit()
        return {"deleted": job_id, "ok": cur.rowcount > 0}
    finally:
        conn.close()


register(
    "cronjob_list",
    {
        "name": "cronjob_list",
        "description": "List scheduled cron jobs",
        "parameters": {"type": "object", "properties": {"limit": {"type": "integer", "default": 20}}},
    },
    cronjob_list,
)
register(
    "cronjob_create",
    {
        "name": "cronjob_create",
        "description": "Create a scheduled job (schedule: '30m', 'every 2h', '0 9 * * *')",
        "parameters": {
            "type": "object",
            "properties": {"schedule": {"type": "string"}, "prompt": {"type": "string"}},
            "required": ["schedule", "prompt"],
        },
    },
    cronjob_create,
)
register(
    "cronjob_delete",
    {
        "name": "cronjob_delete",
        "description": "Delete a cron job by ID",
        "parameters": {"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"]},
    },
    cronjob_delete,
)