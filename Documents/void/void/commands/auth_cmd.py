"""Auth commands — add/list/remove providers."""

import sys
import getpass

from void.providers import (
    add_provider,
    remove_provider,
    list_providers,
    get_provider,
    get_fallback_chain,
    add_fallback,
    get_current_model,
    resolve_model,
)
from void.theme import green, green_bold, grey, dim, err, ok

BUILTIN_MODELS = {
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    "openrouter": ["openai/gpt-4o", "openai/gpt-4o-mini", "anthropic/claude-3.5-sonnet", "google/gemini-2.0-flash"],
    "gemini": ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-pro"],
    "anthropic": ["claude-3-5-sonnet", "claude-3-opus", "claude-3-haiku"],
    "deepseek": ["deepseek-chat", "deepseek-reasoner"],
    "local": ["local-model"],
}


def cmd_auth_add(args) -> None:
    """Add or update an API key for a provider."""
    provider_name = args.provider
    if not provider_name:
        print("usage: void auth add <provider-name>")
        print("\nBuilt-in providers:")
        for name in sorted(BUILTIN_MODELS.keys()):
            print(f"  {name}")
        sys.exit(1)

    existing = get_provider(provider_name)
    if existing:
        print(f"Provider '{provider_name}' exists:")
        print(f"  Current key: {existing['api_key'][:4]}...{existing['api_key'][-4:] if len(existing['api_key']) > 8 else ''}")
        change = input("Update key? (y/N): ").strip().lower()
        if change != "y":
            print("Skipped.")
            return
        api_key = getpass.getpass("API key: ")
    else:
        api_key = getpass.getpass("API key: ")

    base_url = input(f"Base URL [{existing['base_url'] if existing else 'https://api.openai.com/v1'}]: ").strip() or None
    if existing and not base_url:
        base_url = existing.get("base_url")

    desc = input(f"Description [{existing.get('description', '') if existing else ''}]: ").strip() or ""

    if existing and existing.get("models"):
        default_models = ", ".join(existing["models"])
    elif provider_name in BUILTIN_MODELS:
        default_models = ", ".join(BUILTIN_MODELS[provider_name])
    else:
        default_models = ""

    models_input = input(f"Models (comma-separated) [{default_models}]: ").strip()
    models = [m.strip() for m in models_input.split(",") if m.strip()] if models_input else (existing.get("models") if existing else None)

    if not models and provider_name in BUILTIN_MODELS:
        models = BUILTIN_MODELS[provider_name]

    add_provider(
        name=provider_name,
        api_key=api_key,
        base_url=base_url,
        models=models,
        description=desc,
    )
    print(f"\nProvider '{provider_name}' saved.")

    chain = get_fallback_chain()
    if provider_name not in chain:
        add_fallback(provider_name)
        print(f"Added to fallback chain.")


def cmd_auth_list(args) -> None:
    """List all configured credentials."""
    providers = list_providers()
    if not providers:
        print("No credentials configured.")
        print("Add one with: void auth add <provider-name>")
        return

    print("Configured credentials:\n")
    for i, (name, cfg) in enumerate(providers, 1):
        api_key = cfg.get("api_key")
        masked = f"{api_key[:4]}...{api_key[-4:]}" if api_key and len(api_key) > 8 else "(not set)"
        models = cfg.get("models") or []
        print(f"{i}. {name}")
        print(f"   API key: {masked}")
        print(f"   Base URL: {cfg.get('base_url') or '(default)'}")
        print(f"   Models: {len(models)} configured")
        print(f"   Description: {cfg.get('description', '(none)')}")
        in_fallback = name in get_fallback_chain()
        print(f"   In fallback chain: {'yes' if in_fallback else 'no'}")
        print()


def cmd_auth_remove(args) -> None:
    """Remove a provider credential."""
    provider_name = args.provider
    if not provider_name:
        print("usage: void auth remove <provider-name>")
        sys.exit(1)

    if remove_provider(provider_name):
        print(f"Removed provider '{provider_name}'.")
    else:
        print(f"Provider '{provider_name}' not found.")


def cmd_auth_status(args) -> None:
    """Show credential status and which can actually be used."""
    providers = list_providers()
    if not providers:
        print("No credentials configured.")
        return

    print("Credential status:\n")
    for name, cfg in providers:
        api_key = cfg.get("api_key")
        status = "OK" if api_key and len(api_key) > 10 else "MISSING"
        models = cfg.get("models") or []
        print(f"[{status}] {name}: {len(models)} models, base_url={cfg.get('base_url') or '(default)'}")

    chain = get_fallback_chain()
    print(f"\nFallback chain ({len(chain)} providers): {', '.join(chain) if chain else '(empty)'}")

    current = get_current_model()
    print(f"\nCurrent model: {current or '(none)'}")
    if current:
        pn, _, _ = resolve_model()
        if pn:
            print(f"  -> Resolves to: {pn}")
        else:
            print(f"  -> WARNING: cannot resolve")
