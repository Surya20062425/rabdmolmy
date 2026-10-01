"""Provider configuration — store API keys, base URLs, model lists per provider.

Pattern: one config entry per provider, plus a fallback chain.
Resolution: pick a provider → load its key → call its base_url.
"""

import json
import os
from pathlib import Path
from typing import Any

from void.config import load, save, ensure_home, CONFIG_PATH

PROVIDERS_KEY = "providers"
FALLBACK_KEY = "fallback_chain"
CURRENT_MODEL_KEY = "current_model"


def get_providers() -> dict[str, dict[str, Any]]:
    """Return dict of provider_name -> provider_config."""
    return load().get(PROVIDERS_KEY, {})


def get_provider(name: str) -> dict[str, Any] | None:
    return get_providers().get(name)


def add_provider(
    name: str,
    api_key: str,
    base_url: str | None = None,
    models: list[str] | None = None,
    description: str = "",
) -> dict[str, Any]:
    """Register or update a provider."""
    providers = get_providers()
    providers[name] = {
        "api_key": api_key,
        "base_url": base_url,
        "models": models or [],
        "description": description,
    }
    cfg = load()
    cfg[PROVIDERS_KEY] = providers
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return providers[name]


def remove_provider(name: str) -> bool:
    """Remove a provider. Returns True if it existed."""
    providers = get_providers()
    if name not in providers:
        return False
    del providers[name]
    cfg = load()
    cfg[PROVIDERS_KEY] = providers
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    # Also scrub from fallback chain
    _remove_from_fallback(name)
    return True


def list_providers() -> list[tuple[str, dict[str, Any]]]:
    """Return list of (name, config) sorted by name."""
    providers = get_providers()
    return sorted(providers.items())


def get_fallback_chain() -> list[str]:
    """Return ordered list of provider names to try as fallbacks."""
    return load().get(FALLBACK_KEY, [])


def set_fallback_chain(chain: list[str]) -> None:
    """Set the full fallback chain (ordered provider names)."""
    cfg = load()
    cfg[FALLBACK_KEY] = chain
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def add_fallback(provider_name: str) -> None:
    """Add a provider to the end of the fallback chain."""
    chain = get_fallback_chain()
    if provider_name not in chain:
        chain.append(provider_name)
        set_fallback_chain(chain)


def remove_fallback(provider_name: str) -> bool:
    """Remove a provider from the fallback chain."""
    chain = get_fallback_chain()
    if provider_name in chain:
        chain.remove(provider_name)
        set_fallback_chain(chain)
        return True
    return False


def _remove_from_fallback(name: str) -> None:
    """Internal: scrub provider from fallback chain on removal."""
    chain = get_fallback_chain()
    if name in chain:
        chain.remove(name)
        set_fallback_chain(chain)


def set_current_model(model_spec: str) -> None:
    """Set the current model (format: provider/model or just model name)."""
    cfg = load()
    cfg[CURRENT_MODEL_KEY] = model_spec
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def get_current_model() -> str | None:
    return load().get(CURRENT_MODEL_KEY)


def resolve_model() -> tuple[str | None, str | None, str | None]:
    """Resolve the current model to (provider_name, base_url, api_key).

    Returns (provider, base_url, api_key) or (None, None, None) if unresolvable.
    """
    model_spec = get_current_model()
    if not model_spec:
        return None, None, None

    # Format: provider/model or just model name
    if "/" in model_spec:
        provider_name, model_name = model_spec.split("/", 1)
    else:
        # Try to find a provider that has this model
        for name, cfg in get_providers().items():
            if model_spec in (cfg.get("models") or []):
                provider_name = name
                model_name = model_spec
                break
        else:
            return None, None, None

    provider = get_provider(provider_name)
    if not provider:
        return None, None, None

    return provider_name, provider.get("base_url"), provider.get("api_key")


def provider_has_model(provider_name: str, model_name: str) -> bool:
    provider = get_provider(provider_name)
    if not provider:
        return False
    models = provider.get("models") or []
    return model_name in models
