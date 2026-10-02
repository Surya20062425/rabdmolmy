"""Task inbox -- queue new tasks into a running agent.

A task typed while the agent is working lands here (a JSONL file, so any
process can append). The agent loop drains it between turns and folds the new
task into the live conversation instead of losing it.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

from void.config import ensure_home

_LOCK = threading.Lock()


def _path() -> Path:
    return ensure_home() / "inbox.jsonl"


def submit(task: str, source: str = "user") -> None:
    """Queue a task for the running agent. Safe to call from any process/thread."""
    task = (task or "").strip()
    if not task:
        return
    line = json.dumps({"task": task, "source": source,
                       "at": datetime.now(timezone.utc).isoformat()})
    with _LOCK:
        with _path().open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def pending() -> list[dict]:
    """Return queued tasks and clear the queue. Empty list if none."""
    p = _path()
    if not p.exists():
        return []
    with _LOCK:
        try:
            raw = p.read_text(encoding="utf-8")
        except OSError:
            return []
        if not raw.strip():
            return []
        # Truncate via atomic replace so a concurrent submit isn't lost.
        tmp = p.with_suffix(".tmp")
        try:
            os.replace(p, tmp)
        except OSError:
            return []
        try:
            raw = tmp.read_text(encoding="utf-8")
        finally:
            tmp.unlink(missing_ok=True)

    out = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def count() -> int:
    """How many tasks are queued (non-destructive)."""
    p = _path()
    if not p.exists():
        return 0
    try:
        return sum(1 for l in p.read_text(encoding="utf-8").splitlines() if l.strip())
    except OSError:
        return 0


def demo() -> None:
    """Self-check: submit, count, drain, verify empty."""
    p = _path()
    backup = p.read_text(encoding="utf-8") if p.exists() else None
    try:
        p.unlink(missing_ok=True)
        assert count() == 0 and pending() == []
        submit("task one")
        submit("task two")
        submit("")  # ignored
        assert count() == 2, count()
        got = pending()
        assert [t["task"] for t in got] == ["task one", "task two"], got
        assert pending() == [], "queue not cleared"
        print("inbox OK")
    finally:
        p.unlink(missing_ok=True)
        if backup is not None:
            p.write_text(backup, encoding="utf-8")


if __name__ == "__main__":
    demo()
