"""Memory tools — read/write persistent memory (Hermes-equivalent)."""

import json
from pathlib import Path

from void.config import ensure_home
from void.tools.registry import register

MEM = ensure_home() / "memory.json"


def _load():
    if MEM.exists():
        return json.loads(MEM.read_text(encoding="utf-8"))
    return {"entries": []}


def _save(data):
    MEM.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def memory_list() -> dict:
    data = _load()
    return {"count": len(data["entries"]), "entries": data["entries"]}


def memory_add(content: str) -> dict:
    data = _load()
    entry = {"content": content, "added_at": Path(MEM).stat().st_mtime if MEM.exists() else 0}
    data["entries"].append(entry)
    _save(data)
    return entry


def memory_remove(index: int) -> dict:
    data = _load()
    if 0 <= index < len(data["entries"]):
        removed = data["entries"].pop(index)
        _save(data)
        return {"removed": removed}
    return {"error": f"index out of range: {index}"}


register("memory_list", {"name": "memory_list", "description": "List persistent memory entries", "parameters": {"type": "object", "properties": {}}}, memory_list)
register("memory_add", {"name": "memory_add", "description": "Add a memory entry", "parameters": {"type": "object", "properties": {"content": {"type": "string"}}, "required": ["content"]}}, memory_add)
register("memory_remove", {"name": "memory_remove", "description": "Remove a memory entry by index", "parameters": {"type": "object", "properties": {"index": {"type": "integer"}}, "required": ["index"]}}, memory_remove)