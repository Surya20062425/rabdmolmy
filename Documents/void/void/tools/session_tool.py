"""Session tools — search/read past sessions."""

import json
from pathlib import Path

from void.config import ensure_home
from void.tools.registry import register

DB = ensure_home() / "sessions.db"


def _conn():
    import sqlite3
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    return conn


def session_search(query: str, limit: int = 10) -> dict:
    """Search session content for a query."""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT DISTINCT s.id, s.title, s.updated_at, m.content "
            "FROM sessions s JOIN messages m ON s.id = m.session_id "
            "WHERE m.content LIKE ? ORDER BY s.updated_at DESC LIMIT ?",
            (f"%{query}%", limit),
        ).fetchall()
        return {
            "query": query,
            "count": len(rows),
            "sessions": [
                {"id": r["id"], "title": r["title"], "updated_at": r["updated_at"], "snippet": r["content"][:300]}
                for r in rows
            ],
        }
    finally:
        conn.close()


def session_read(session_id: str) -> dict:
    """Read a session's messages."""
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not row:
            return {"error": f"session not found: {session_id}"}
        msgs = conn.execute(
            "SELECT role, content, created_at FROM messages WHERE session_id = ? ORDER BY order_index",
            (session_id,),
        ).fetchall()
        return {
            "id": row["id"],
            "title": row["title"],
            "messages": [{"role": m["role"], "content": m["content"], "created_at": m["created_at"]} for m in msgs],
        }
    finally:
        conn.close()


register("session_search", {"name": "session_search", "description": "Search past sessions by keyword", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "default": 10}}, "required": ["query"]}}, session_search)
register("session_read", {"name": "session_read", "description": "Read a session's messages", "parameters": {"type": "object", "properties": {"session_id": {"type": "string"}}, "required": ["session_id"]}}, session_read)