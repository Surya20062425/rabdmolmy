"""System control tools — file ops, shell, directory navigation.

Ponytail: direct OS access via stdlib. No sandbox. User is responsible.
"""

import json
import os
import subprocess
from pathlib import Path

from void.tools.registry import register


def system_read_file(path: str, offset: int = 0, limit: int = 2000) -> dict:
    """Read a local file and return content + line count."""
    p = Path(path)
    if not p.exists():
        return {"error": f"file not found: {path}"}
    if not p.is_file():
        return {"error": f"not a file: {path}"}
    try:
        content = p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return {"error": str(e)}
    lines = content.splitlines()
    total = len(lines)
    chunk = lines[offset: offset + limit]
    return {
        "path": str(p),
        "total_lines": total,
        "offset": offset,
        "limit": limit,
        "truncated": offset + limit < total,
        "content": "\n".join(chunk),
    }


def system_write_file(path: str, content: str, append: bool = False) -> dict:
    """Write content to a local file."""
    p = Path(path)
    try:
        if append and p.exists():
            p.write_text(p.read_text(encoding="utf-8") + content, encoding="utf-8")
        else:
            p.write_text(content, encoding="utf-8")
        return {"success": True, "path": str(p), "bytes": len(content.encode("utf-8"))}
    except Exception as e:
        return {"error": str(e)}


def system_shell(command: str, timeout: int = 30) -> dict:
    """Run a shell command and return stdout + stderr + exit code."""
    # ponytail: no sandbox — user is responsible for what runs
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True,
            text=True, timeout=timeout, cwd=os.getcwd(),
        )
        return {
            "command": command,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"timeout after {timeout}s: {command}"}
    except Exception as e:
        return {"error": str(e)}


def system_ls(path: str = ".") -> dict:
    """List directory contents."""
    p = Path(path)
    if not p.exists():
        return {"error": f"path not found: {path}"}
    if not p.is_dir():
        return {"error": f"not a directory: {path}"}
    entries = []
    for e in sorted(p.iterdir()):
        st = e.stat()
        entries.append({
            "name": e.name,
            "type": "dir" if e.is_dir() else ("file" if e.is_file() else "other"),
            "size": st.st_size if e.is_file() else 0,
        })
    return {"path": str(p.resolve()), "entries": entries, "count": len(entries)}


def system_pwd() -> dict:
    return {"cwd": os.getcwd()}


def system_env_var(name: str) -> dict:
    val = os.environ.get(name)
    return {"name": name, "value": val, "exists": val is not None}


register(
    name="system_read_file",
    schema={
        "name": "system_read_file",
        "description": "Read a local file and return content",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or relative file path"},
                "offset": {"type": "integer", "description": "Line offset to start reading from", "default": 0},
                "limit": {"type": "integer", "description": "Max lines to read", "default": 2000},
            },
            "required": ["path"],
        },
    },
    handler=system_read_file,
)

register(
    name="system_write_file",
    schema={
        "name": "system_write_file",
        "description": "Write content to a local file",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "File path"},
                "content": {"type": "string", "description": "Content to write"},
                "append": {"type": "boolean", "description": "Append to existing file", "default": False},
            },
            "required": ["path", "content"],
        },
    },
    handler=system_write_file,
)

register(
    name="system_shell",
    schema={
        "name": "system_shell",
        "description": "Run a shell command and return output",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 30},
            },
            "required": ["command"],
        },
        "dangerous": True,
    },
    handler=system_shell,
)

register(
    name="system_ls",
    schema={
        "name": "system_ls",
        "description": "List directory contents",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Directory path", "default": "."},
            },
            "required": [],
        },
    },
    handler=system_ls,
)

register(
    name="system_pwd",
    schema={
        "name": "system_pwd",
        "description": "Get current working directory",
        "parameters": {"type": "object", "properties": {}},
    },
    handler=system_pwd,
)

register(
    name="system_env_var",
    schema={
        "name": "system_env_var",
        "description": "Get an environment variable value",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Environment variable name"},
            },
            "required": ["name"],
        },
    },
    handler=system_env_var,
)
