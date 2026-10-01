"""Fallback chain commands."""

import sys

from void.providers import (
    get_fallback_chain,
    set_fallback_chain,
    add_fallback,
    remove_fallback,
    get_provider,
    list_providers,
)
from void.theme import green, green_bold, grey, dim, err, ok, header, table


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

    for name in args.providers:
        if not get_provider(name):
            print(f"Error: provider '{name}' not configured.")
            sys.exit(1)

    set_fallback_chain(list(args.providers))
    print(f"Fallback chain set: {' -> '.join(args.providers)}")
