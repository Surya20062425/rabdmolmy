"""Model commands — list, set, pick models across providers.

Mirrors Hermes `hermes model` + `hermes fallback` semantics.
"""

import sys
from void.providers import (
    get_providers,
    list_providers,
    get_provider,
    add_provider,
    remove_provider,
    get_fallback_chain,
    set_fallback_chain,
    add_fallback,
    remove_fallback,
    set_current_model,
    get_current_model,
    resolve_model,
    provider_has_model,
)


BUILTIN_MODELS = {
    "openai": [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
    ],
    "openrouter": [
        "openai/gpt-4o",
        "openai/gpt-4o-mini",
        "anthropic/claude-3.5-sonnet",
        "google/gemini-2.0-flash",
    ],
    "gemini": [
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-pro",
    ],
    "anthropic": [
        "claude-3-5-sonnet",
        "claude-3-opus",
        "claude-3-haiku",
    ],
    "deepseek": [
        "deepseek-chat",
        "deepseek-reasoner",
    ],
    "local": [
        "local-model",  # placeholder, user sets base_url to LM Studio/vLLM
    ],
}


def cmd_model_list(args) -> None:
    """List all configured providers and their models."""
    providers = list_providers()
    if not providers:
        print("No providers configured. Add one with `void auth add <name>`")
        print("\nBuilt-in provider presets:")
        for name, models in sorted(BUILTIN_MODELS.items()):
            print(f"  {name}: {', '.join(models[:3])}{'...' if len(models) > 3 else ''}")
        return

    current = get_current_model()
    print(f"Current model: {current or '(none)'}\n")

    for name, cfg in providers:
        api_key = cfg.get("api_key")
        masked = f"{api_key[:4]}...{api_key[-4:]}" if api_key and len(api_key) > 8 else "(not set)"
        models = cfg.get("models") or []
        print(f"[{name}]")
        print(f"  API key: {masked}")
        print(f"  Base URL: {cfg.get('base_url') or '(default)'}")
        if models:
            print(f"  Models: {', '.join(models)}")
        else:
            print(f"  Models: (none configured)")
        if name == (current.split('/')[0] if current and '/' in current else None):
            print(f"  ^ active provider")
        print()


def cmd_model_set(args) -> None:
    """Set the current model."""
    model_spec = args.model
    if not model_spec:
        print("usage: void model set <provider/model>")
        print("       void model set gpt-4o-mini  (uses first provider with that model)")
        return

    # Validate
    if "/" in model_spec:
        provider_name, model_name = model_spec.split("/", 1)
        provider = get_provider(provider_name)
        if not provider:
            print(f"Error: provider '{provider_name}' not found. Available: {', '.join(p for p, _ in list_providers()) or '(none)'}")
            sys.exit(1)
        if model_name not in (provider.get("models") or []):
            # Allow setting even if not in list — user may add custom models
            print(f"Note: model '{model_name}' not in {provider_name}'s known model list")
    else:
        # Find provider with this model
        found = None
        for name, cfg in list_providers():
            if model_spec in (cfg.get("models") or []):
                found = name
                break
        if not found:
            print(f"Error: model '{model_spec}' not found in any provider")
            print(f"Available models:")
            for name, cfg in list_providers():
                models = cfg.get("models") or []
                if models:
                    print(f"  [{name}] {', '.join(models)}")
            sys.exit(1)
        model_spec = f"{found}/{model_spec}"

    set_current_model(model_spec)
    print(f"Current model set to: {model_spec}")


def cmd_model_show(args) -> None:
    """Show current model and resolve it."""
    current = get_current_model()
    if not current:
        print("No current model set.")
        print("Set one with: void model set <provider/model>")
        return

    print(f"Current model: {current}\n")
    provider_name, base_url, api_key = resolve_model()
    if provider_name:
        print(f"Resolved to provider: {provider_name}")
        print(f"  Base URL: {base_url or '(default)'}")
        print(f"  API key: {api_key[:4]}...{api_key[-4:] if api_key and len(api_key) > 8 else ''}")
        provider = get_provider(provider_name)
        if provider:
            models = provider.get("models") or []
            print(f"  Known models: {', '.join(models) if models else '(none)'}")
    else:
        print("Warning: could not resolve to a configured provider.")
        print("The model may not be in any provider's model list.")


def cmd_auth_add(args) -> None:
    """Add or update an API key for a provider."""
    import getpass

    provider_name = args.provider
    if not provider_name:
        print("usage: void auth add <provider-name>")
        print("\nBuilt-in providers:")
        for name in sorted(BUILTIN_MODELS.keys()):
            print(f"  {name}")
        sys.exit(1)

    # Check if provider exists
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

    # Prompt for optional fields
    base_url = input(f"Base URL [{existing['base_url'] if existing else 'https://api.openai.com/v1'}]: ").strip() or None
    if existing and not base_url:
        base_url = existing.get("base_url")

    desc = input(f"Description [{existing.get('description', '') if existing else ''}]: ").strip() or ""

    # Model list
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

    # Add to fallback if not already
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


def cmd_fallback_list(args) -> None:
    """List the fallback chain."""
    chain = get_fallback_chain()
    if not chain:
        print("Fallback chain is empty.")
        print("Add providers with `void auth add <name>` — they're added to fallback automatically.")
        return

    print("Fallback chain (order = attempt order):\n")
    for i, name in enumerate(chain, 1):
        cfg = get_provider(name)
        if cfg:
            models = cfg.get("models") or []
            print(f"{i}. {name} ({len(models)} models)")
        else:
            print(f"{i}. {name} (config missing)")
    print()


def cmd_fallback_add(args) -> None:
    """Add a provider to the fallback chain."""
    provider_name = args.provider
    if not provider_name:
        print("usage: void fallback add <provider-name>")
        sys.exit(1)

    if not get_provider(provider_name):
        print(f"Error: provider '{provider_name}' not configured. Add it first with `void auth add {provider_name}`")
        sys.exit(1)

    add_fallback(provider_name)
    print(f"Added '{provider_name}' to fallback chain.")


def cmd_fallback_remove(args) -> None:
    """Remove a provider from the fallback chain."""
    provider_name = args.provider
    if not provider_name:
        print("usage: void fallback remove <provider-name>")
        sys.exit(1)

    if remove_fallback(provider_name):
        print(f"Removed '{provider_name}' from fallback chain.")
    else:
        print(f"Provider '{provider_name}' not in fallback chain.")


def cmd_fallback_set(args) -> None:
    """Set the entire fallback chain."""
    if not args.providers:
        print("usage: void fallback set <provider1> <provider2> ...")
        print("       Order matters: leftmost is tried first.")
        sys.exit(1)

    # Validate all exist
    for name in args.providers:
        if not get_provider(name):
            print(f"Error: provider '{name}' not configured.")
            sys.exit(1)

    set_fallback_chain(list(args.providers))
    print(f"Fallback chain set: {' -> '.join(args.providers)}")
