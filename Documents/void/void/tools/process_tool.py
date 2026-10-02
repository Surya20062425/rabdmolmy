"""Process tools — manage background processes (Hermes-equivalent)."""

import json
import subprocess
from pathlib import Path

from void.tools.registry import register

PROC_FILE = Path("/tmp/void_processes.json") if Path("/tmp").exists() else Path.home() / ".void" / "processes.json"


def _load():
    if PROC_FILE.exists():
        return json.loads(PROC_FILE.read_text(encoding="utf-8"))
    return {"processes": {}}


def _save(data):
    PROC_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROC_FILE.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def process_list() -> dict:
    """List tracked background processes."""
    data = _load()
    out = {}
    for sid, info in data["processes"].items():
        try:
            p = subprocess.Popen([], shell=False)  # no-op to check subprocess works
            import os
            os.kill(info["pid"], 0)  # check if alive
            alive = True
        except (ProcessLookupError, OSError, TypeError):
            alive = False
        info["alive"] = alive
        out[sid] = info
    return {"count": len(out), "processes": out}


def process_start(command: str, background: bool = True) -> dict:
    """Start a background process. Returns session id."""
    import uuid
    sid = str(uuid.uuid4())[:8]
    proc = subprocess.Popen(
        command, shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True,
    )
    data = _load()
    data["processes"][sid] = {"pid": proc.pid, "command": command, "background": background}
    _save(data)
    return {"session_id": sid, "pid": proc.pid, "command": command, "status": "running"}


def process_stop(session_id: str) -> dict:
    """Stop a background process by session id."""
    import os, signal
    data = _load()
    if session_id not in data["processes"]:
        return {"error": f"process not found: {session_id}"}
    proc_info = data["processes"].pop(session_id)
    try:
        os.kill(proc_info["pid"], signal.SIGTERM)
        return {"stopped": session_id, "pid": proc_info["pid"]}
    except ProcessLookupError:
        return {"stopped": session_id, "pid": proc_info["pid"], "note": "already dead"}


register(
    "process_list",
    {
        "name": "process_list",
        "description": "List background processes",
        "parameters": {"type": "object", "properties": {}},
    },
    process_list,
)
register(
    "process_start",
    {
        "name": "process_start",
        "description": "Start a background process",
        "parameters": {
            "type": "object",
            "properties": {"command": {"type": "string"}, "background": {"type": "boolean", "default": True}},
            "required": ["command"],
        },
    },
    process_start,
)
register(
    "process_stop",
    {
        "name": "process_stop",
        "description": "Stop a background process by session id",
        "parameters": {"type": "object", "properties": {"session_id": {"type": "string"}}, "required": ["session_id"]},
    },
    process_stop,
)