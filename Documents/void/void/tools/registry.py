"""Tool registry — register tools, dispatch calls. Auto-discovers tools/*.py."""

import importlib
import json
import pkgutil
from pathlib import Path
from typing import Any

_REGISTRY: dict[str, dict[str, Any]] = {}


def _discover_tools() -> None:
    """Import every module under the tools package so its top-level register() runs."""
    if _discovered():
        return
    # registry.py lives in void/tools/ — parent is the tools dir
    here = Path(__file__).resolve().parent
    for mod in pkgutil.iter_modules([str(here)]):
        try:
            importlib.import_module(f"void.tools.{mod.name}")
        except Exception:
            pass  # bad tool module — skip, don't break startup


def _discovered() -> bool:
    return bool(_REGISTRY)


def register(name: str, schema: dict, handler) -> None:
    """Register a tool. Schema is an OpenAI-format function tool def."""
    _REGISTRY[name] = {"schema": schema, "handler": handler}


def dispatch(name: str, args: dict) -> str:
    """Call a registered tool's handler with args. Returns a JSON string."""
    if name not in _REGISTRY:
        return json.dumps({"error": f"unknown tool: {name}"})
    try:
        result = _REGISTRY[name]["handler"](**args)
    except TypeError as e:
        return json.dumps({"error": f"handler args mismatch: {e}"})
    except Exception as e:
        return json.dumps({"error": str(e)})
    # Normalise return to a JSON string
    if isinstance(result, str):
        return result
    return json.dumps(result)


def list_tools() -> list[str]:
    _discover_tools()
    return list(_REGISTRY.keys())


def get_schemas() -> list[dict]:
    """Return OpenAI-format function tool defs, ready to pass to the model.

    Each entry is wrapped as `{"type": "function", "function": ...}` —
    the shape OpenAI's API expects. The raw per-tool schema (name +
    description + parameters) is what `register()` stores; this wrapper
    is the canonical "what the model sees".
    """
    _discover_tools()
    return [
        {"type": "function", "function": entry["schema"]}
        for entry in _REGISTRY.values()
    ]


# Trigger discovery on first use
_discover_tools()
