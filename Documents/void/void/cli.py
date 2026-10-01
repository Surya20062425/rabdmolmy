"""Void CLI — full Hermes-equivalent CLI surface with branded upgrade--- style.

Branding: neon green (#9df133) on black, s symbol, DM Mono aesthetic.
Surface: chat, config, setup, model, auth, fallback, sessions, skills,
         cron, webhooks, mcp, tools, projects, kanban, skins, pets,
         memory, secrets, moa, hooks, logs — all CLI, no gateway.
"""

from __future__ import annotations

import argparse
import sys

from void.agent import run
from void.config import get_api_key, get_base_url, get_model_name, set_key as set_key_func, get, load, ensure_home
from void.model import Model, MissingApiKeyError
from void.model_commands import (
    cmd_model_list, cmd_model_set, cmd_model_show,
    cmd_auth_add, cmd_auth_list, cmd_auth_remove, cmd_auth_status,
    cmd_fallback_list, cmd_fallback_add, cmd_fallback_remove, cmd_fallback_set,
)
from void.commands.sessions_cmd import main as sessions_main
from void.commands.skills_cmd import main as skills_main
from void.commands.cron_cmd import main as cron_main
from void.theme import (
    banner, logo_ascii, header, cmd_entry, bullet, ok, warn, err,
    table, g as green, gb as green_bold, w as white, gr as grey, gd as green_dim, green_line, gd as dim, orange,
    orange_bold, symbol, prompt_text, masked_api_key, tagged, section_divider,
    SYMBOL, BOX_DIV, BOX_VERT, BOX_TL, BOX_TR, BOX_BL, BOX_BR,
    BOX_L, BOX_T, CHECK_MARK, CROSS_MARK, BULLET, ARROW, CIRCLE, DASH,
    CHECK, CROSS,
    white, green_dim as _gd,
    start_screen,
)

# backward-compat: old cli.py aliased orange->red already; keep working
red = orange
red_bold = orange_bold
# Aliases used in f-strings below (match what's imported)
CHECK = CHECK_MARK
CROSS = CROSS_MARK

# Unicode symbols used in help text (imported from void.theme)


# ═══════════════════════════════════════════════════════════════════
# HELP TEXT
# ═══════════════════════════════════════════════════════════════════

# Help-text formatting helpers (used in module-level f-strings above).
# Defined here, not in theme.py, because they are CLI-help-specific and short.


def help_header(title: str, subtitle: str = "") -> str:
    """Help page top — left-aligned title with subtle subtitle."""
    return f"\n  {green_bold(title)}  {green_dim(subtitle)}\n  {green_line(BOX_DIV * 60)}\n"


def help_section_heading(text: str) -> str:
    """A section label inside a help page."""
    return f"\n  {green_bold(text)}\n"


def help_cmd(cmd: str, desc: str = "") -> str:
    """One command line: `cmd` + optional description."""
    return f"    {green(cmd)}  {dim(desc)}"


def help_key_value(key: str, value: str) -> str:
    """A `key: value` line in a help page."""
    return f"    {green_bold(key)}  {dim(value)}"


VOID_HELP = f"""
{help_header('SKULL', 'the CLI agent / CLI-first / neon green on black')}
  {green_dim('A Hermes-equivalent CLI agent. Chat, tools, config,')}
  {green_dim('providers, sessions, skills, cron, and more ' + DASH + '')}
  {green_dim('all from the terminal.')}

  {green_bold(f'symbol: {SYMBOL}')}  {dim('| neon green on black | CLI-first')}

  {green(CHECK)} = ready    {orange(CROSS_MARK)} = warn    {dim('grey')} = muted
"""

DQUOTE = '"'  # double quote for use in help text f-strings

SUBCOMMAND_HELP = {
    "chat": f"""
{help_header('chat', 'interactive REPL or one-shot')}
  {dim('Chat with the Void agent. Tools dispatched automatically.')}

  {help_section_heading('usage')}
  {help_cmd('void chat', 'interactive REPL session')}
  {help_cmd(f'void chat -q {DQUOTE}question{DQUOTE}', 'one-shot query, print answer only')}
  {help_cmd('void chat --resume <id>', 'resume a past session (coming soon)')}
  {help_cmd('void chat --model <name>', 'override model for this run')}
  {help_cmd('void chat --api-key <key>', 'override API key for this run')}
  {help_cmd('void chat --max-turns 10', 'cap tool-call iterations')}

  {help_section_heading('flags')}
  {help_key_value('--api-key', 'API key (overrides config)')}
  {help_key_value('--base-url', 'override base URL')}
  {help_key_value('--model', 'model name (overrides config)')}
  {help_key_value('--max-turns', 'tool-call iteration cap (default: 20)')}
  {help_key_value('-q, --query', 'one-shot prompt')}
  {help_key_value('--resume', 'resume session ID')}
""",
    "config": f"""
{help_header('config', 'view and edit config')}
  {dim('Stored in ')}{green('~/.void/config.json')}{dim('.')}

  {help_section_heading('usage')}
  {help_cmd('void config show', 'show all config (keys masked)')}
  {help_cmd('void config set <key> <value>', 'set a config value')}
  {help_cmd('void config get <key>', 'get a specific config value')}
  {help_cmd('void config set api_key', 'prompt for API key (hidden input)')}

  {help_section_heading('keys')}
  {help_key_value('api_key', 'OpenAI-compatible API key')}
  {help_key_value('base_url', 'API base URL (default: https://api.openai.com/v1)')}
  {help_key_value('model', 'default model name')}
""",
    "setup": f"""
{help_header('setup', 'interactive setup wizard')}

  {dim('Walks you through API key, base URL, and model selection.')}

  {help_section_heading('usage')}
  {help_cmd('void setup', 'run the interactive wizard')}

  {help_section_heading('what it does')}
    1. prompts for your API key (hidden)
    2. asks for a custom base URL (optional)
    3. asks for a default model (optional)
    4. saves everything to ~/.void/config.json
""",
    "model": f"""
{help_header('model', 'manage providers and models')}
  {dim('Hermes-style provider system with fallback chains.')}

  {help_section_heading('usage')}
  {help_cmd('void model list', 'list all configured providers + models')}
  {help_cmd('void model set <provider/model>', 'set the active model')}
  {help_cmd('void model show', 'show current model + resolution')}

  {help_section_heading('model format')}
    provider/model     e.g. openai/gpt-4o-mini
    model              just the name (resolved from providers)

  {help_section_heading('built-in presets')}
    openai, openrouter, gemini, anthropic, deepseek, local
""",
    "auth": f"""
{help_header('auth', 'manage API credentials')}
  {dim('Each provider has its own key, base URL, and model list.')}

  {help_section_heading('usage')}
  {help_cmd('void auth add [name]', 'add/update a provider credential')}
  {help_cmd('void auth list', 'list all configured credentials')}
  {help_cmd('void auth remove <name>', 'remove a provider')}
  {help_cmd('void auth status', 'show credential health + fallback status')}

  {help_section_heading('built-in provider names')}
    openai, openrouter, gemini, anthropic, deepseek, local
""",
    "fallback": f"""
{help_header('fallback', 'manage fallback chain')}
  {dim('When a model call fails, Void walks the chain to find a working provider.')}

  {help_section_heading('usage')}
  {help_cmd('void fallback list', 'show current fallback chain')}
  {help_cmd('void fallback add <name>', 'add a provider to the chain')}
  {help_cmd('void fallback remove <name>', 'remove a provider from the chain')}
  {help_cmd('void fallback set <n1> <n2> ...', 'set the entire chain (order matters)')}

  {help_section_heading('example')}
    void fallback set openai openrouter gemini
    {dim(DASH + ' tries openai first, then openrouter, then gemini')}
""",
    "sessions": f"""
{help_header('sessions', 'session management')}
  {dim('Sessions stored in SQLite. Use --resume to continue a past conversation.')}

  {help_section_heading('usage')}
  {help_cmd('void sessions list', 'list all saved sessions')}
  {help_cmd('void sessions browse', 'browse sessions interactively')}
  {help_cmd('void sessions rename <id> <title>', 'rename a session')}
  {help_cmd('void sessions delete <id>', 'delete a session')}
  {help_cmd('void sessions export <out>', 'export a session to file')}
  {help_cmd('void sessions prune', 'remove old/expired sessions')}
  {help_cmd('void sessions stats', 'session count + size stats')}
""",
    "skills": f"""
{help_header('skills', 'skill management')}
  {dim('Skills are markdown files (SKILL.md) injected into the')}
  {dim('system prompt + optional tool registrations.')}

  {help_section_heading('usage')}
  {help_cmd('void skills list', 'list installed skills')}
  {help_cmd('void skills browse', 'browse available skills')}
  {help_cmd('void skills search <query>', 'search skills by keyword')}
  {help_cmd('void skills inspect <id>', 'show skill details')}
  {help_cmd('void skills install <url>', 'install a skill from URL/GitHub')}
  {help_cmd('void skills config', 'enable/disable skills per platform')}
  {help_cmd('void skills check', 'check for skill updates')}
  {help_cmd('void skills update', 'update all installed skills')}
  {help_cmd('void skills uninstall <name>', 'remove a skill')}
  {help_cmd('void skills publish <path>', 'publish a skill to the hub')}
  {help_cmd('void skills tap add <repo>', 'add a GitHub repo as skill source')}
""",
    "cron": f"""
{help_header('cron', 'scheduled jobs')}
  {dim('Jobs stored in SQLite. Supports intervals and cron expressions.')}

  {help_section_heading('usage')}
  {help_cmd('void cron list', 'list all scheduled jobs')}
  {help_cmd('void cron create <schedule> <prompt>', 'create a scheduled job')}
  {help_cmd('void cron edit <id>', 'edit a job')}
  {help_cmd('void cron pause <id>', 'pause a job')}
  {help_cmd('void cron resume <id>', 'resume a paused job')}
  {help_cmd('void cron run <id>', 'run a job now')}
  {help_cmd('void cron remove <id>', 'delete a job')}
  {help_cmd('void cron status', 'show job statuses')}

  {help_section_heading('schedule formats')}
    30m          every 30 minutes
    every 2h     every 2 hours
    0 9 * * *    cron expression (daily at 9am)
    ISO timestamp   run once at this time
""",
    "webhooks": f"""
{help_header('webhooks', 'webhook routes')}
  {dim('Event-driven agent runs.')}

  {help_section_heading('usage')}
  {help_cmd('void webhook subscribe <name>', 'create a webhook endpoint')}
  {help_cmd('void webhook list', 'list all webhook routes')}
  {help_cmd('void webhook remove <name>', 'delete a webhook')}
  {help_cmd('void webhook test <name>', 'send a test payload')}
""",
    "mcp": f"""
{help_header('mcp', 'MCP server support')}
  {dim('Model Context Protocol — connect external tool servers.')}

  {help_section_heading('usage')}
  {help_cmd('void mcp add <name> --url <url>', 'add an MCP server by URL')}
  {help_cmd('void mcp add <name> --command <cmd>', 'add an MCP server by command')}
  {help_cmd('void mcp remove <name>', 'remove an MCP server')}
  {help_cmd('void mcp list', 'list configured MCP servers')}
  {help_cmd('void mcp test <name>', 'test an MCP server connection')}
  {help_cmd('void mcp catalog', 'list available MCP servers')}
  {help_cmd('void mcp install <name>', 'install from catalog')}
  {help_cmd('void mcp configure <name>', 'toggle tool selection')}
  {help_cmd('void mcp serve', 'run Void as an MCP server')}
""",
    "tools": f"""
{help_header('tools', 'tool management')}
  {dim('View and manage available tools.')}

  {help_section_heading('usage')}
  {help_cmd('void tools list', 'list all registered tools')}
  {help_cmd('void tools enable <name>', 'enable a tool')}
  {help_cmd('void tools disable <name>', 'disable a tool')}
""",
    "project": f"""
{help_header('project', 'multi-folder workspaces')}
  {dim('Named workspaces spanning multiple folders.')}

  {help_section_heading('usage')}
  {help_cmd('void project list', 'list projects')}
  {help_cmd('void project create <name> <path>', 'create a project')}
  {help_cmd('void project use <name>', 'switch to a project')}
  {help_cmd('void project show', 'show current project')}
  {help_cmd('void project delete <name>', 'delete a project')}
""",
    "kanban": f"""
{help_header('kanban', 'multi-agent work-queue board')}
  {dim('Board for coordinating tasks across agents.')}

  {help_section_heading('usage')}
  {help_cmd('void kanban show', 'show the board')}
  {help_cmd('void kanban add <task>', 'add a task')}
  {help_cmd('void kanban move <id> <column>', 'move a task')}
  {help_cmd('void kanban remove <id>', 'remove a task')}
""",
    "skin": f"""
{help_header('skin', 'theme switching')}
  {dim('Void uses a neon green / black theme by default.')}

  {help_section_heading('usage')}
  {help_cmd('void skin list', 'list available themes')}
  {help_cmd('void skin use <name>', 'switch to a theme')}
  {help_cmd('void skin set <key> <hex>', 'change one color in current theme')}
""",
    "pets": f"""
{help_header('pets', 'pet mascots')}
  {dim('Cosmetic pet mascots for the terminal.')}

  {help_section_heading('usage')}
  {help_cmd('void pets list', 'list available pets')}
  {help_cmd('void pets show', 'show current pet')}
  {help_cmd('void pets select <name>', 'select a pet')}
""",
    "memory": f"""
{help_header('memory', 'persistent memory')}
  {dim('Persistent memory across sessions.')}

  {help_section_heading('usage')}
  {help_cmd('void memory setup', 'configure memory backend')}
  {help_cmd('void memory status', 'show memory status')}
  {help_cmd('void memory off', 'disable memory')}
  {help_cmd('void memory reset', 'clear all memory')}
""",
    "secrets": f"""
{help_header('secrets', 'external secret stores')}
  {dim('Bitwarden, 1Password, etc.')}

  {help_section_heading('usage')}
  {help_cmd('void secrets bitwarden', 'connect bitwarden')}
  {help_cmd('void secrets onepassword', 'connect 1password')}
""",
    "moa": f"""
{help_header('moa', 'mixture of agents')}
  {dim(DASH + ' multi-model voting ensemble.')}

  {help_section_heading('usage')}
  {help_cmd('void moa list', 'list MOA slots')}
  {help_cmd('void moa add <model>', 'add a model slot')}
  {help_cmd('void moa remove <id>', 'remove a slot')}
  {help_cmd('void moa set <n>', 'set number of voters')}
""",
    "hooks": f"""
{help_header('hooks', 'event hooks')}
  {dim('Trigger commands on events (tool use, session end, etc).')}

  {help_section_heading('usage')}
  {help_cmd('void hooks list', 'list hooks')}
  {help_cmd('void hooks add <event> <cmd>', 'add a hook')}
  {help_cmd('void hooks remove <id>', 'remove a hook')}
""",
    "logs": f"""
{help_header('logs', 'view logs')}
  {dim('Agent and error logs.')}

  {help_section_heading('usage')}
  {help_cmd('void logs', 'show recent logs')}
  {help_cmd('void logs -f', 'follow logs live')}
  {help_cmd('void logs errors', 'show only errors')}
""",
    "doctor": f"""
{help_header('doctor', 'diagnostics')}
  {dim('Check dependencies and configuration.')}

  {help_section_heading('usage')}
  {help_cmd('void doctor', 'run diagnostics')}
  {help_cmd('void doctor --fix', 'attempt to auto-fix issues')}
""",
    "status": f"""
{help_header('status', 'component status')}
  {dim('Show component status at a glance.')}

  {help_section_heading('usage')}
  {help_cmd('void status', 'show core status')}
  {help_cmd('void status --all', 'show all components')}
""",
}


# ═══════════════════════════════════════════════════════════════════
# COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════════

def cmd_chat(args) -> None:
    """Chat with the agent — interactive or one-shot."""
    try:
        model = build_model(args)
    except MissingApiKeyError as e:
        print(err(str(e)))
        print()
        print(white("Set up first:  void setup"))
        print(white("Or one-shot:   void auth add openai"))
        print(white("Then:          void model set openai/gpt-4o-mini"))
        sys.exit(1)

    if args.query:
        messages = [{"role": "user", "content": args.query}]
        answer = run(model, messages, max_turns=args.max_turns)
        print(answer)
        return

    # Interactive REPL
    print(start_screen())
    print(section_divider())
    messages: list[dict] = []
    try:
        while True:
            prompt = prompt_text("")
            try:
                line = input(prompt)
            except EOFError:
                break
            if not line.strip():
                continue
            messages.append({"role": "user", "content": line})
            answer = run(model, messages, max_turns=args.max_turns)
            print(answer)
            print(section_divider())
            messages.append({"role": "assistant", "content": answer})
    except KeyboardInterrupt:
        print()
    print()


def build_model(args) -> Model:
    """Build a Model from CLI args, falling back to config/providers/env.

    Resolution:
      1. Explicit CLI flags (--api-key / --base-url / --model)
      2. Top-level config values (what `void config set` writes)
      3. Provider system (current_model + providers.<name>.api_key)
      4. Env vars
      5. Built-in defaults (then Model raises MissingApiKeyError)
    """
    # 1. Explicit CLI flags beat everything.
    if args.api_key:
        return Model(
            api_key=args.api_key,
            base_url=args.base_url,
            model_name=args.model,
        )

    # 2. Top-level config values (the `void config set api_key` path).
    #    These live at the top level of config.json, separate from the
    #    per-provider keys in providers.<name>.
    cfg = load()
    cfg_key = cfg.get("api_key")
    if cfg_key:
        return Model(
            api_key=cfg_key,
            base_url=cfg.get("base_url") or args.base_url,
            model_name=args.model or cfg.get("model"),
        )

    # 3. Provider system: current_model + providers.<name>.api_key
    model_name = args.model
    if model_name and "/" in model_name:
        from void.providers import get_provider
        provider_name, model_name_only = model_name.split("/", 1)
        provider = get_provider(provider_name)
        if provider and provider.get("api_key"):
            return Model(
                api_key=provider["api_key"],
                base_url=provider.get("base_url"),
                model_name=model_name_only,
            )

    from void.providers import resolve_model, get_current_model
    current = get_current_model()
    if current:
        provider_name, base_url, api_key = resolve_model()
        if provider_name and api_key:
            return Model(
                api_key=api_key,
                base_url=base_url,
                model_name=current.split("/", 1)[1] if "/" in current else current,
            )

    # 4. Nothing resolved — let Model try env + built-in defaults,
    #    and raise MissingApiKeyError if still nothing.
    return Model(
        api_key=None,
        base_url=args.base_url,
        model_name=args.model,
    )


def cmd_config(args) -> None:
    ensure_home()
    cfg_cmd = getattr(args, "config_cmd", None)

    # Subcommand form: void config show|set|get
    if cfg_cmd == "show" or args.show:
        cfg = load()
        if not cfg:
            print(white("config: (empty)"))
            print(dim("  Use void setup or void config set <key> <value>"))
            return
        print(header("Config", 1))
        for k, v in sorted(cfg.items()):
            if k == "api_key" and v:
                print(tagged(k, masked_api_key(v), green, grey))
            else:
                print(tagged(k, str(v)))
        return

    if cfg_cmd == "set":
        set_key = getattr(args, "set_key", None) or getattr(args, "set_key_opt", None)
        set_value = getattr(args, "set_value", None)
    else:
        # Legacy positional form: void config KEY [VALUE]
        set_key = getattr(args, "set_key", None)
        set_value = getattr(args, "set_value", None)

    if set_key and set_value is None:
        import getpass
        set_value = getpass.getpass(f"{green_bold(set_key)}: ")

    if set_key and set_value is not None:
        set_key_func(set_key, set_value)
        print(ok(f"set {set_key}"))
        if set_key == "api_key":
            print(dim("  verify: void config get api_key"))
        return

    # Get
    get_key = None
    if cfg_cmd == "get":
        get_key = getattr(args, "get_key", None)
    if get_key is None:
        get_key = getattr(args, "get_key_opt", None)

    if get_key:
        val = get(get_key)
        if val is None:
            print(tagged(get_key, "(not set)", grey, grey))
        elif get_key == "api_key":
            print(tagged(get_key, masked_api_key(val)))
        else:
            print(tagged(get_key, str(val)))
        return

    print(SUBCOMMAND_HELP["config"])


def cmd_setup(args) -> None:
    """Interactive setup wizard."""
    ensure_home()
    import getpass

    print(start_screen())
    print(green_bold("=== Void Setup ==="))
    print(dim("Let's get you connected.\n"))

    # API key
    existing = get("api_key")
    if existing:
        print(tagged("current key", masked_api_key(existing)))
        change = input(grey("Change it? (y/N): ")).strip().lower()
        if change != "y":
            api_key = existing
            print(dim("  keeping current key."))
        else:
            api_key = getpass.getpass(f"{green_bold('API key')}: ")
            set_key("api_key", api_key)
            print(ok("API key saved."))
    else:
        api_key = getpass.getpass(f"{green_bold('API key')}: ")
        set_key("api_key", api_key)
        print(ok("API key saved."))

    # Base URL
    existing_url = get("base_url")
    default_url = existing_url or "https://api.openai.com/v1"
    base_url = input(f"{green_bold('Base URL')} [{dim(default_url)}]: ").strip()
    if base_url:
        set_key("base_url", base_url)
        print(ok("Base URL saved."))
    elif not existing_url:
        print(dim("  Using default: https://api.openai.com/v1"))

    # Model name
    existing_model = get("model")
    default_model = existing_model or "gpt-4o-mini"
    model_name = input(f"{green_bold('Model name')} [{dim(default_model)}]: ").strip()
    if model_name:
        set_key("model", model_name)
        print(ok("Model name saved."))
    elif not existing_model:
        print(dim("  Using default: gpt-4o-mini"))

    print()
    print(green_bold("Setup complete."))
    print()
    print(cmd_entry("void chat -q 'hello'", "test your connection"))
    print(cmd_entry("void chat", "start interactive session"))
    print()
    print(dim("Want another provider?  void auth add openrouter"))


def cmd_model(args) -> None:
    if args.model_cmd == "list":
        cmd_model_list(args)
    elif args.model_cmd == "set":
        cmd_model_set(args)
    elif args.model_cmd == "show":
        cmd_model_show(args)


def cmd_auth(args) -> None:
    if args.auth_cmd == "add":
        cmd_auth_add(args)
    elif args.auth_cmd == "list":
        cmd_auth_list(args)
    elif args.auth_cmd == "remove":
        cmd_auth_remove(args)
    elif args.auth_cmd == "status":
        cmd_auth_status(args)


def cmd_fallback(args) -> None:
    if args.fallback_cmd == "list":
        cmd_fallback_list(args)
    elif args.fallback_cmd == "add":
        cmd_fallback_add(args)
    elif args.fallback_cmd == "remove":
        cmd_fallback_remove(args)
    elif args.fallback_cmd == "set":
        cmd_fallback_set(args)


# ═══════════════════════════════════════════════════════════════════
# STUB HANDLERS (coming soon)
# ═══════════════════════════════════════════════════════════════════

def cmd_stub(name: str, args) -> None:
    """Print 'coming soon' message for unimplemented commands."""
    desc = SUBCOMMAND_HELP.get(name, f"{name} command")
    print(header(name, 1))
    print(dim("This command is coming soon."))
    print()
    print(dim("Current Void surface: chat, config, setup, model, auth, fallback"))
    print(dim("Full Hermes CLI equivalence is in progress."))
    print()
    print(green_bold(BOX_DIV * 62))
    print(desc)
    print(green_bold(BOX_DIV * 62))


def cmd_sessions(args) -> None:
    # Wire to real sessions command module
    sc = getattr(args, "sessions_subcommand", None)
    if sc:
        args.subcommand = sc
    sessions_main(args)

def cmd_skills(args) -> None:
    # Wire to real skills command module
    sc = getattr(args, "skills_subcommand", None)
    if sc:
        args.subcommand = sc
    skills_main(args)

def cmd_cron(args) -> None:
    # Wire to real cron command module
    sc = getattr(args, "cron_subcommand", None)
    if sc:
        args.subcommand = sc
    cron_main(args)

def cmd_webhooks(args) -> None:
    cmd_stub("webhooks", args)

def cmd_mcp(args) -> None:
    cmd_stub("mcp", args)

def _tool_state_path() -> Path:
    from pathlib import Path
    import os
    home = Path(os.environ.get("VOID_HOME", Path.home() / ".void"))
    home.mkdir(parents=True, exist_ok=True)
    return home / "tool_state.json"


def _load_tool_state() -> dict:
    p = _tool_state_path()
    if not p.exists():
        return {"disabled": []}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"disabled": []}


def _save_tool_state(state: dict) -> None:
    _tool_state_path().write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def cmd_tools(args) -> None:
    sc = getattr(args, "tools_subcommand", None)
    if sc == "list":
        from void.tools.registry import list_tools
        all_tools = list_tools()
        state = _load_tool_state()
        disabled = set(state.get("disabled", []))
        rows = [[t, "disabled" if t in disabled else "enabled"] for t in sorted(all_tools)]
        print(header("Tools", 1))
        if not rows:
            print(grey("No tools registered."))
            return
        print(table(["Tool", "Status"], rows, [26, 12]))
        print()
        print(dim(f"  {len(all_tools)} tool(s) total  ·  {len(disabled)} disabled"))
        return
    if sc == "enable":
        name = getattr(args, "name", None)
        if not name:
            print(err("Usage: void tools enable <name>"))
            return
        state = _load_tool_state()
        disabled = set(state.get("disabled", []))
        if name not in disabled:
            print(ok(f"{name} already enabled"))
            return
        disabled.remove(name)
        state["disabled"] = sorted(disabled)
        _save_tool_state(state)
        print(ok(f"Enabled: {name}"))
        return
    if sc == "disable":
        name = getattr(args, "name", None)
        if not name:
            print(err("Usage: void tools disable <name>"))
            return
        state = _load_tool_state()
        disabled = set(state.get("disabled", []))
        if name in disabled:
            print(ok(f"{name} already disabled"))
            return
        disabled.add(name)
        state["disabled"] = sorted(disabled)
        _save_tool_state(state)
        print(ok(f"Disabled: {name}"))
        return
    cmd_stub("tools", args)

def cmd_project(args) -> None:
    cmd_stub("project", args)

def cmd_kanban(args) -> None:
    cmd_stub("kanban", args)

def cmd_skin(args) -> None:
    cmd_stub("skin", args)

def cmd_pets(args) -> None:
    cmd_stub("pets", args)

def cmd_memory(args) -> None:
    cmd_stub("memory", args)

def cmd_secrets(args) -> None:
    cmd_stub("secrets", args)

def cmd_moa(args) -> None:
    cmd_stub("moa", args)

def cmd_hooks(args) -> None:
    cmd_stub("hooks", args)

def cmd_logs(args) -> None:
    cmd_stub("logs", args)

def cmd_doctor(args) -> None:
    cmd_stub("doctor", args)

def cmd_status(args) -> None:
    cmd_stub("status", args)


# ═══════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════

_COMMAND_DISPATCH = {
    "chat":       cmd_chat,
    "config":     cmd_config,
    "setup":      cmd_setup,
    "model":      cmd_model,
    "auth":       cmd_auth,
    "fallback":   cmd_fallback,
    "sessions":   cmd_sessions,
    "skills":     cmd_skills,
    "cron":       cmd_cron,
    "webhooks":   cmd_webhooks,
    "mcp":        cmd_mcp,
    "tools":      cmd_tools,
    "project":    cmd_project,
    "kanban":     cmd_kanban,
    "skin":       cmd_skin,
    "pets":       cmd_pets,
    "memory":     cmd_memory,
    "secrets":    cmd_secrets,
    "moa":        cmd_moa,
    "hooks":      cmd_hooks,
    "logs":       cmd_logs,
    "doctor":     cmd_doctor,
    "status":     cmd_status,
}


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="void",
        description="Void CLI agent (/s " + DASH + " the CLI agent)",
        epilog="",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ── chat ──
    chat = sub.add_parser("chat", help="Chat with the agent")
    chat.add_argument("--api-key", type=str, help="API key (overrides config)")
    chat.add_argument("--base-url", type=str, help="Override base URL")
    chat.add_argument("--model", type=str, help="Model name (overrides config)")
    chat.add_argument("--max-turns", type=int, default=20, help="Tool-call cap")
    chat.add_argument("-q", "--query", type=str, help="One-shot query")
    chat.add_argument("--resume", type=str, help="Resume session (coming soon)")

    # ── config ──
    cfg = sub.add_parser("config", help="View and edit config")
    cfg_sub = cfg.add_subparsers(dest="config_cmd", required=False)
    # `void config set KEY [VALUE]` — value prompts hidden if omitted
    cfg_set = cfg_sub.add_parser("set", help="Set a config value")
    cfg_set.add_argument("set_key", help="Key to set (e.g. api_key, base_url, model)")
    cfg_set.add_argument("set_value", nargs="?", default=None, help="Value to set (prompts if omitted for sensitive keys)")
    # `void config get KEY`
    cfg_get = cfg_sub.add_parser("get", help="Get a config value")
    cfg_get.add_argument("get_key", help="Key to get")
    # `void config show`
    cfg_sub.add_parser("show", help="Show full config (keys masked)")
    cfg.add_argument("--show", action="store_true", help="Show full config (flags form)")
    cfg.add_argument("--get", dest="get_key_opt", type=str, help="Get a specific key (flags form)")

    # ── setup ──
    sub.add_parser("setup", help="Interactive setup wizard")

    # ── model ──
    mp = sub.add_parser("model", help="Manage models and providers")
    msub = mp.add_subparsers(dest="model_cmd", required=True)
    msub.add_parser("list", help="List providers and models")
    mset = msub.add_parser("set", help="Set current model")
    mset.add_argument("model", nargs="?", help="provider/model or just model")
    msub.add_parser("show", help="Show current model resolution")

    # ── auth ──
    ap = sub.add_parser("auth", help="Manage credentials")
    asub = ap.add_subparsers(dest="auth_cmd", required=True)
    aa = asub.add_parser("add", help="Add/update a provider")
    aa.add_argument("provider", nargs="?", help="Provider name")
    asub.add_parser("list", help="List all credentials")
    ar = asub.add_parser("remove", help="Remove a provider")
    ar.add_argument("provider", help="Provider name")
    asub.add_parser("status", help="Show credential status")

    # ── fallback ──
    fp = sub.add_parser("fallback", help="Manage fallback chain")
    fsub = fp.add_subparsers(dest="fallback_cmd", required=True)
    fsub.add_parser("list", help="List fallback chain")
    fa = fsub.add_parser("add", help="Add to fallback chain")
    fa.add_argument("provider", help="Provider name")
    fr = fsub.add_parser("remove", help="Remove from fallback chain")
    fr.add_argument("provider", help="Provider name")
    fs = fsub.add_parser("set", help="Set entire fallback chain")
    fs.add_argument("providers", nargs="+", help="Provider names in order")

    # ── sessions ──
    sp = sub.add_parser("sessions", help="Session management")
    sp.sub = sp.add_subparsers(dest="sessions_subcommand", required=True)
    sp.sub.add_parser("list", help="List all sessions")
    sp.sub.add_parser("browse", help="Browse sessions")
    sp_rename = sp.sub.add_parser("rename", help="Rename a session")
    sp_rename.add_argument("id", help="Session ID")
    sp_rename.add_argument("title", help="New title")
    sp_delete = sp.sub.add_parser("delete", help="Delete a session")
    sp_delete.add_argument("id", help="Session ID")
    sp_export = sp.sub.add_parser("export", help="Export a session")
    sp_export.add_argument("id", help="Session ID")
    sp_export.add_argument("output", nargs="?", help="Output path")
    sp.sub.add_parser("prune", help="Prune old sessions")
    sp.sub.add_parser("stats", help="Session statistics")

    # ── skills ──
    sp = sub.add_parser("skills", help="Skill management")
    sp.sub = sp.add_subparsers(dest="skills_subcommand", required=True)
    sp.sub.add_parser("list", help="List installed skills")
    sp.sub.add_parser("browse", help="Browse skill catalog")
    sp_search = sp.sub.add_parser("search", help="Search skills")
    sp_search.add_argument("query", help="Search query")
    sp_inspect = sp.sub.add_parser("inspect", help="Inspect a skill")
    sp_inspect.add_argument("id", help="Skill ID")
    sp_install = sp.sub.add_parser("install", help="Install a skill")
    sp_install.add_argument("url", nargs="?", help="Skill URL")
    sp_install.add_argument("--path", type=str, help="Local SKILL.md file")
    sp.sub.add_parser("uninstall", help="Uninstall a skill").add_argument("name", help="Skill name")
    sp.sub.add_parser("update", help="Update all skills")
    sp.sub.add_parser("config", help="Configure skills")
    sp.sub.add_parser("check", help="Check for updates")
    sp_publish = sp.sub.add_parser("publish", help="Publish a skill")
    sp_publish.add_argument("path", help="Skill file path")
    sp_tap = sp.sub.add_parser("tap", help="Add skill source")
    sp_tap_sub = sp_tap.add_subparsers(dest="tap_subcommand", required=True)
    sp_tap_add = sp_tap_sub.add_parser("add", help="Add a GitHub repo")
    sp_tap_add.add_argument("repo", help="owner/repo")

    # ── cron ──
    sp = sub.add_parser("cron", help="Scheduled jobs")
    sp.sub = sp.add_subparsers(dest="cron_subcommand", required=True)
    sp.sub.add_parser("list", help="List jobs")
    sp_create = sp.sub.add_parser("create", help="Create a job")
    sp_create.add_argument("schedule", help="Schedule (30m, '0 9 * * *', ISO)")
    sp_create.add_argument("prompt", help="Prompt to run")
    sp_edit = sp.sub.add_parser("edit", help="Edit a job")
    sp_edit.add_argument("id", help="Job ID")
    sp_edit.add_argument("--schedule", type=str, help="New schedule")
    sp_edit.add_argument("--prompt", type=str, help="New prompt")
    sp.sub.add_parser("pause", help="Pause a job").add_argument("id", help="Job ID")
    sp.sub.add_parser("resume", help="Resume a job").add_argument("id", help="Job ID")
    sp.sub.add_parser("run", help="Run a job now").add_argument("id", help="Job ID")
    sp.sub.add_parser("remove", help="Remove a job").add_argument("id", help="Job ID")
    sp.sub.add_parser("status", help="Job statuses")

    # ── webhooks ──
    sp = sub.add_parser("webhooks", help="Webhook routes")
    sp.sub = sp.add_subparsers(dest="webhooks_subcommand", required=True)
    sp.sub.add_parser("list", help="List webhook routes")
    sp_subscribe = sp.sub.add_parser("subscribe", help="Create a webhook endpoint")
    sp_subscribe.add_argument("name", help="Webhook name")
    sp.sub.add_parser("remove", help="Remove a webhook").add_argument("name", help="Webhook name")
    sp.sub.add_parser("test", help="Test a webhook").add_argument("name", help="Webhook name")

    # ── mcp ──
    sp = sub.add_parser("mcp", help="MCP servers")
    sp.sub = sp.add_subparsers(dest="mcp_subcommand", required=True)
    sp.sub.add_parser("list", help="List MCP servers")
    sp_add = sp.sub.add_parser("add", help="Add an MCP server")
    sp_add.add_argument("name", help="Server name")
    sp_add.add_argument("--url", type=str, help="MCP server URL")
    sp_add.add_argument("--command", type=str, help="MCP server command")
    sp.sub.add_parser("remove", help="Remove an MCP server").add_argument("name", help="Server name")
    sp.sub.add_parser("test", help="Test an MCP server").add_argument("name", help="Server name")
    sp.sub.add_parser("catalog", help="List available MCP servers")
    sp.sub.add_parser("install", help="Install from catalog").add_argument("name", help="Server name")
    sp.sub.add_parser("configure", help="Configure a server").add_argument("name", help="Server name")
    sp.sub.add_parser("serve", help="Run Void as an MCP server")

    # ── tools ──
    sp = sub.add_parser("tools", help="Tool management")
    sp.sub = sp.add_subparsers(dest="tools_subcommand", required=True)
    sp.sub.add_parser("list", help="List all tools")
    sp.sub.add_parser("enable", help="Enable a tool").add_argument("name", help="Tool name")
    sp.sub.add_parser("disable", help="Disable a tool").add_argument("name", help="Tool name")

    # ── project ──
    sp = sub.add_parser("project", help="Multi-folder projects")
    sp.sub = sp.add_subparsers(dest="project_subcommand", required=True)
    sp.sub.add_parser("list", help="List projects")
    sp_create = sp.sub.add_parser("create", help="Create a project")
    sp_create.add_argument("name", help="Project name")
    sp_create.add_argument("path", help="Project path")
    sp.sub.add_parser("use", help="Switch to a project").add_argument("name", help="Project name")
    sp.sub.add_parser("show", help="Show current project")
    sp.sub.add_parser("delete", help="Delete a project").add_argument("name", help="Project name")

    # ── kanban ──
    sp = sub.add_parser("kanban", help="Multi-agent board")
    sp.sub = sp.add_subparsers(dest="kanban_subcommand", required=True)
    sp.sub.add_parser("show", help="Show the board")
    sp.sub.add_parser("add", help="Add a task").add_argument("task", help="Task description")
    sp_sub_task_move = sp.sub.add_parser("move", help="Move a task")
    sp_sub_task_move.add_argument("id", help="Task ID")
    sp_sub_task_move.add_argument("column", help="Column name")
    sp.sub.add_parser("remove", help="Remove a task").add_argument("id", help="Task ID")

    # ── skin ──
    sp = sub.add_parser("skin", help="Themes")
    sp.sub = sp.add_subparsers(dest="skin_subcommand", required=True)
    sp.sub.add_parser("list", help="List available themes")
    sp.sub.add_parser("use", help="Switch to a theme").add_argument("name", help="Theme name")
    sp_set = sp.sub.add_parser("set", help="Change a color")
    sp_set.add_argument("key", help="Color key")
    sp_set.add_argument("hex", help="Hex color (e.g. #9df133)")

    # ── pets ──
    sp = sub.add_parser("pets", help="Pet mascots")
    sp.sub = sp.add_subparsers(dest="pets_subcommand", required=True)
    sp.sub.add_parser("list", help="List available pets")
    sp.sub.add_parser("show", help="Show current pet")
    sp.sub.add_parser("select", help="Select a pet").add_argument("name", help="Pet name")

    # ── memory ──
    sp = sub.add_parser("memory", help="Persistent memory")
    sp.sub = sp.add_subparsers(dest="memory_subcommand", required=True)
    sp.sub.add_parser("setup", help="Configure memory backend")
    sp.sub.add_parser("status", help="Show memory status")
    sp.sub.add_parser("off", help="Disable memory")
    sp.sub.add_parser("reset", help="Clear all memory")

    # ── secrets ──
    sp = sub.add_parser("secrets", help="External secret stores")
    sp.sub = sp.add_subparsers(dest="secrets_subcommand", required=True)
    sp.sub.add_parser("bitwarden", help="Connect bitwarden")
    sp.sub.add_parser("onepassword", help="Connect 1password")

    # ── moa ──
    sp = sub.add_parser("moa", help="Mixture of Agents")
    sp.sub = sp.add_subparsers(dest="moa_subcommand", required=True)
    sp.sub.add_parser("list", help="List MOA slots")
    sp.sub.add_parser("add", help="Add a model slot").add_argument("model", help="Model name")
    sp.sub.add_parser("remove", help="Remove a slot").add_argument("id", help="Slot ID")
    sp.sub.add_parser("set", help="Set number of voters").add_argument("n", help="Number of voters")

    # ── hooks ──
    sp = sub.add_parser("hooks", help="Event hooks")
    sp.sub = sp.add_subparsers(dest="hooks_subcommand", required=True)
    sp.sub.add_parser("list", help="List hooks")
    sp_add_hook = sp.sub.add_parser("add", help="Add a hook")
    sp_add_hook.add_argument("event", help="Event name")
    sp_add_hook.add_argument("cmd", help="Command to run")
    sp.sub.add_parser("remove", help="Remove a hook").add_argument("id", help="Hook ID")

    # ── logs ──
    sp = sub.add_parser("logs", help="View logs")
    sp.sub = sp.add_subparsers(dest="logs_subcommand", required=True)
    sp.sub.add_parser("errors", help="Show only errors")
    sp.sub.add_parser("follow", help="Follow logs live")

    # ── doctor ──
    sp = sub.add_parser("doctor", help="Diagnostics")
    sp.set_defaults(_stub_cmd="doctor")
    sp.add_argument("--fix", action="store_true", help="Attempt to auto-fix issues")

    # ── status ──
    sp = sub.add_parser("status", help="Component status")
    sp.set_defaults(_stub_cmd="status")
    sp.add_argument("--all", action="store_true", help="Show all components")

    args = parser.parse_args()

    # Dispatch
    if hasattr(args, "_stub_cmd"):
        cmd_stub(args._stub_cmd, args)
    elif args.command in _COMMAND_DISPATCH:
        _COMMAND_DISPATCH[args.command](args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
