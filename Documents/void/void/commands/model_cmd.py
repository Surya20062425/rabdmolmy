"""Model commands — list, set, pick models across providers."""

import sys
from void.providers import (
    list_providers,
    get_provider,
    set_current_model,
    get_current_model,
    resolve_model,
)
from void.theme import green, green_bold, grey, dim, err, ok, header, table

BUILTIN_MODELS = {
    "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    "openrouter": ["openai/gpt-4o", "openai/gpt-4o-mini", "anthropic/claude-3.5-sonnet", "google/gemini-2.0-flash"],
    "gemini": ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-pro"],
    "anthropic": ["claude-3-5-sonnet", "claude-3-opus", "claude-3-haiku"],
    "deepseek": ["deepseek-chat", "deepseek-reasoner"],
    "local": ["local-model"],
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
        if name == (current.split("/")[0] if current and "/" in current else None):
            print(f"  ^ active provider")
        print()


def cmd_model_set(args) -> None:
    """Set the current model."""
    model_spec = args.model
    if not model_spec:
        print("usage: void model set <provider/model>")
        print("       void model set gpt-4o-mini  (uses first provider with that model)")
        return

    if "/" in model_spec:
        provider_name, model_name = model_spec.split("/", 1)
        provider = get_provider(provider_name)
        if not provider:
            print(f"Error: provider '{provider_name}' not found. Available: {', '.join(p for p, _ in list_providers()) or '(none)'}")
            sys.exit(1)
        if model_name not in (provider.get("models") or []):
            print(f"Note: model '{model_name}' not in {provider_name}'s known model list")
    else:
        found = None
        for name, cfg in list_providers():
            if model_spec in (cfg.get("models") or []):
                found = name
                break
        if not found:
            print(f"Error: model '{model_spec}' not found in any provider")
            print("Available models:")
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
