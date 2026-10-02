"""Task list tools — Hermes-equivalent todo tracking."""

import json
from datetime import datetime, timezone
from pathlib import Path

from void.config import ensure_home
from void.tools.registry import register

DB = ensure_home() / "tasks.json"


def _load():
    if DB.exists():
        return json.loads(DB.read_text(encoding="utf-8"))
    return {"tasks": []}


def _save(data):
    DB.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def task_list(limit: int = 50) -> dict:
    data = _load()
    tasks = data["tasks"]
    open_t = [t for t in tasks if t.get("status") != "done"]
    return {
        "total": len(tasks),
        "open": len(open_t),
        "done": len(tasks) - len(open_t),
        "tasks": open_t[-limit:],
    }


def task_add(description: str) -> dict:
    data = _load()
    t = {
        "id": str(len(data["tasks"]) + 1),
        "description": description,
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    data["tasks"].append(t)
    _save(data)
    return t


def task_done(task_id: str) -> dict:
    data = _load()
    for t in data["tasks"]:
        if t["id"] == task_id:
            t["status"] = "done"
            t["done_at"] = datetime.now(timezone.utc).isoformat()
            _save(data)
            return t
    return {"error": f"task not found: {task_id}"}


def task_delete(task_id: str) -> dict:
    data = _load()
    orig = len(data["tasks"])
    data["tasks"] = [t for t in data["tasks"] if t["id"] != task_id]
    if len(data["tasks"]) == orig:
        return {"error": f"task not found: {task_id}"}
    _save(data)
    return {"deleted": task_id}


register("task_list", {"name": "task_list", "description": "List open tasks", "parameters": {"type": "object", "properties": {"limit": {"type": "integer", "default": 50}}}}, task_list)
register("task_add", {"name": "task_add", "description": "Add a task", "parameters": {"type": "object", "properties": {"description": {"type": "string"}}, "required": ["description"]}}, task_add)
register("task_done", {"name": "task_done", "description": "Mark task done", "parameters": {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]}}, task_done)
register("task_delete", {"name": "task_delete", "description": "Delete a task", "parameters": {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]}}, task_delete)