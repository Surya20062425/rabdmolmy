"""Void config — persist API key, base URL, model name in ~/.void/config.json.

Pattern: CLI flags override config file; config file overrides env; env overrides built-in defaults.
Secrets live here for a personal CLI (same as .env); for team use, swap in keyring/bitwarden.
"""

import json
import os
from pathlib import Path
from typing import Any

VOID_HOME = Path(os.environ.get("VOID_HOME", Path.home() / ".void"))
CONFIG_PATH = VOID_HOME / "config.json"


def ensure_home() -> Path:
    VOID_HOME.mkdir(parents=True, exist_ok=True)
    return VOID_HOME


def load() -> dict[str, Any]:
    ensure_home()
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save(data: dict[str, Any]) -> None:
    ensure_home()
    cfg = load()
    cfg.update(data)
    CONFIG_PATH.write_text(
        json.dumps(cfg, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def get(key: str, default: Any = None) -> Any:
    """Read a single config value. CLI flag > config file > env > default."""
    return load().get(key, default)


def set_key(key: str, value: str) -> None:
    save({key: value})


def get_api_key() -> str | None:
    """Resolve API key: explicit CLI arg > config > env > None."""
    return get("api_key") or os.getenv("OPENAI_API_KEY")


def get_base_url() -> str | None:
    return get("base_url") or os.getenv("OPENAI_BASE_URL")


def get_model_name() -> str:
    from void.providers import get_current_model
    return get_current_model() or os.getenv("VOID_MODEL") or "gpt-4o-mini"
