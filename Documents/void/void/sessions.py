"""Void session store — SQLite-based session persistence.

Mirrors Hermes sessions: list, browse, rename, delete, export, prune, stats.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from void.config import ensure_home

DB_PATH = ensure_home() / "sessions.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _ensure_schema() -> None:
    conn = _conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT 'untitled',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                message_count INTEGER NOT NULL DEFAULT 0,
                duration_seconds INTEGER NOT NULL DEFAULT 0,
                tags TEXT NOT NULL DEFAULT '[]',
                metadata TEXT NOT NULL DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tool_call_id TEXT,
                created_at TEXT NOT NULL,
                order_index INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at DESC)
        """)
        conn.commit()
    finally:
        conn.close()


# Initialize on import
_ensure_schema()


def create_session(title: str = "untitled", tags: list[str] | None = None) -> dict:
    """Create a new session and return its record."""
    sid = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO sessions (id, title, created_at, updated_at, tags) VALUES (?, ?, ?, ?, ?)",
            (sid, title, now, now, json.dumps(tags or [])),
        )
        conn.commit()
        return get_session(sid)
    finally:
        conn.close()


def get_session(sid: str) -> dict | None:
    """Get a session by ID."""
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (sid,)).fetchone()
        if not row:
            return None
        msgs = list_messages(sid)
        return {
            "id": row["id"],
            "title": row["title"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "message_count": row["message_count"],
            "duration_seconds": row["duration_seconds"],
            "tags": json.loads(row["tags"]),
            "metadata": json.loads(row["metadata"]),
            "messages": msgs,
        }
    finally:
        conn.close()


def list_sessions(limit: int = 50, offset: int = 0) -> list[dict]:
    """List sessions, newest first."""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT * FROM sessions ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        result = []
        for row in rows:
            result.append({
                "id": row["id"],
                "title": row["title"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "message_count": row["message_count"],
                "duration_seconds": row["duration_seconds"],
                "tags": json.loads(row["tags"]),
                "metadata": json.loads(row["metadata"]),
            })
        return result
    finally:
        conn.close()


def rename_session(sid: str, title: str) -> dict | None:
    """Rename a session."""
    conn = _conn()
    try:
        now = datetime.now(timezone.utc).isoformat()
        cur = conn.execute(
            "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
            (title, now, sid),
        )
        conn.commit()
        if cur.rowcount == 0:
            return None
        return get_session(sid)
    finally:
        conn.close()


def delete_session(sid: str) -> bool:
    """Delete a session and all its messages."""
    conn = _conn()
    try:
        cur = conn.execute("DELETE FROM sessions WHERE id = ?", (sid,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def add_message(session_id: str, role: str, content: str, tool_call_id: str | None = None) -> int:
    """Add a message to a session. Returns the message ID."""
    conn = _conn()
    try:
        # Get current max order_index
        row = conn.execute(
            "SELECT COALESCE(MAX(order_index), 0) as mx FROM messages WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        order_index = row["mx"] + 1

        now = datetime.now(timezone.utc).isoformat()
        cur = conn.execute(
            """INSERT INTO messages (session_id, role, content, tool_call_id, created_at, order_index)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (session_id, role, content, tool_call_id, now, order_index),
        )
        conn.commit()

        # Update session message count and updated_at
        conn.execute(
            "UPDATE sessions SET message_count = message_count + 1, updated_at = ? WHERE id = ?",
            (now, session_id),
        )
        conn.commit()

        return cur.lastrowid
    finally:
        conn.close()


def list_messages(session_id: str) -> list[dict]:
    """List all messages in a session, in order."""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT * FROM messages WHERE session_id = ? ORDER BY order_index ASC",
            (session_id,),
        ).fetchall()
        return [
            {
                "id": r["id"],
                "session_id": r["session_id"],
                "role": r["role"],
                "content": r["content"],
                "tool_call_id": r["tool_call_id"],
                "created_at": r["created_at"],
                "order_index": r["order_index"],
            }
            for r in rows
        ]
    finally:
        conn.close()


def update_session_duration(sid: str, seconds: int) -> None:
    """Update the total duration of a session."""
    conn = _conn()
    try:
        cur = conn.execute(
            "SELECT duration_seconds FROM sessions WHERE id = ?",
            (sid,),
        ).fetchone()
        if cur:
            new_duration = (cur["duration_seconds"] or 0) + seconds
            conn.execute(
                "UPDATE sessions SET duration_seconds = ? WHERE id = ?",
                (new_duration, sid),
            )
            conn.commit()
    finally:
        conn.close()


def export_session(sid: str, output_path: str | None = None) -> str:
    """Export a session to a JSON file. Returns the path."""
    session = get_session(sid)
    if not session:
        raise ValueError(f"Session not found: {sid}")

    if output_path is None:
        safe_title = "".join(c for c in session["title"] if c.isalnum() or c in "-_ ")[:40]
        output_path = ensure_home() / "exports" / f"{safe_title}_{sid[:8]}.json"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(session, indent=2, default=str), encoding="utf-8")
    return str(output_path)


def prune_sessions(age_days: int = 30) -> int:
    """Delete sessions older than age_days. Returns count deleted."""
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=age_days)).isoformat()
    conn = _conn()
    try:
        cur = conn.execute(
            "DELETE FROM sessions WHERE created_at < ?",
            (cutoff,),
        )
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def session_stats() -> dict:
    """Return aggregate stats about all sessions."""
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*) as cnt, SUM(message_count) as msgs, SUM(duration_seconds) as secs "
            "FROM sessions",
        ).fetchone()
        return {
            "session_count": row["cnt"] or 0,
            "total_messages": row["msgs"] or 0,
            "total_duration_seconds": row["secs"] or 0,
        }
    finally:
        conn.close()
