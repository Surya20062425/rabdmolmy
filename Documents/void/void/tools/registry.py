"""Tool registry — register tools, dispatch calls. Auto-discovers tools/*.py."""

import importlib
import json
import os
import pkgutil
import sys
from pathlib import Path
from typing import Any

from void.theme import g, gd, gb  # type: ignore[import-not-found]

_REGISTRY: dict[str, dict[str, Any]] = {}
_DISCOVERED = False


def _discover_tools() -> None:
    """Import every module under the tools package so its top-level register() runs.

    Guarded by an explicit flag, not "is the registry non-empty" — a caller that
    registers one tool before discovery would otherwise suppress discovery.
    """
    global _DISCOVERED
    if _DISCOVERED:
        return
    here = Path(__file__).resolve().parent
    for mod in pkgutil.iter_modules([str(here)]):
        if mod.name == "registry":
            continue  # reloading this module would rebind _REGISTRY and wipe it
        full = f"void.tools.{mod.name}"
        try:
            if full in sys.modules:
                importlib.reload(sys.modules[full])
            else:
                importlib.import_module(full)
        except Exception:
            pass  # bad tool module — skip, don't break startup
    _DISCOVERED = True


def _discovered() -> bool:
    return _DISCOVERED


def reset_registry() -> None:
    """Clear the registry and force re-discovery on next use (tests, reloads)."""
    global _DISCOVERED
    _REGISTRY.clear()
    _DISCOVERED = False
    for name in list(sys.modules):
        if name.startswith("void.tools.") and name != "void.tools.registry":
            sys.modules.pop(name, None)


def register(name: str, schema: dict, handler) -> None:
    """Register a tool. Schema is an OpenAI-format function tool def."""
    _REGISTRY[name] = {"schema": schema, "handler": handler}


def dispatch(name: str, args: dict) -> str:
    """Call a registered tool's handler with args. Returns a JSON string."""
    _discover_tools()  # self-heal: dispatch works even if called before list_tools()
    if name not in _REGISTRY:
        return json.dumps({"error": f"unknown tool: {name}"})
    print(f"{gb('s')} {gd('running')} {g(name)}", end="\r", flush=True)
    try:
        result = _REGISTRY[name]["handler"](**args)
    except TypeError as e:
        return json.dumps({"error": f"handler args mismatch: {e}"})
    except Exception as e:
        return json.dumps({"error": str(e)})
    print(" " * 40, end="\r", flush=True)
    # Normalise return to a JSON string
    if isinstance(result, str):
        return result
    return json.dumps(result)


def list_tools() -> list[str]:
    _discover_tools()
    return list(_REGISTRY.keys())


def disabled_tools() -> set[str]:
    """Tools the user disabled via `void tools disable`."""
    home = Path(os.environ.get("VOID_HOME", Path.home() / ".void"))
    p = home / "tool_state.json"
    if not p.exists():
        return set()
    try:
        return set(json.loads(p.read_text(encoding="utf-8")).get("disabled", []))
    except (json.JSONDecodeError, OSError):
        return set()


def get_schemas() -> list[dict]:
    """Return OpenAI-format function tool defs, ready to pass to the model.

    Disabled tools (via `void tools disable`) are filtered out here — this is
    the single choke point every model call routes through.
    """
    _discover_tools()
    off = disabled_tools()
    return [
        {"type": "function", "function": entry["schema"]}
        for name, entry in _REGISTRY.items()
        if name not in off
    ]


# Trigger discovery on first use
_discovered()