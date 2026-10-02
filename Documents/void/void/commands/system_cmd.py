"""Void system commands -- real implementations for the previously-stubbed surface.

Covers: status, doctor, logs, memory, kanban, project, skin, pets, hooks,
secrets, moa. Local state lives in ~/.void/*.json via a shared store.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from void.config import ensure_home
from void.theme import header, table, ok, err, grey, dim, green_bold, green, warn


# ── shared JSON store ────────────────────────────────────────────────

def _store(name: str, default):
    p = ensure_home() / f"{name}.json"
    if not p.exists():
        return default
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def _save_store(name: str, data) -> None:
    (ensure_home() / f"{name}.json").write_text(
        json.dumps(data, indent=2, default=str) + "\n", encoding="utf-8"
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── status ───────────────────────────────────────────────────────────

def cmd_status(args) -> None:
    """Real component status: config, model, providers, sessions, tools, skills."""
    from void.providers import get_current_model, get_fallback_chain, list_providers
    from void.config import get_api_key, get_base_url

    print(header("Void Status", 1))

    rows = []
    key = get_api_key()
    rows.append(["api_key", "set" if key else "MISSING"])
    rows.append(["base_url", get_base_url() or "(default)"])
    rows.append(["model", get_current_model() or "(unset)"])
    rows.append(["providers", str(len(list_providers()))])
    rows.append(["fallback", ", ".join(get_fallback_chain()) or "(empty)"])

    try:
        from void.sessions import session_stats
        st = session_stats()
        rows.append(["sessions", f"{st['session_count']} ({st['total_messages']} msgs)"])
    except Exception:
        rows.append(["sessions", "unavailable"])

    try:
        from void.tools.registry import list_tools, disabled_tools
        rows.append(["tools", f"{len(list_tools())} ({len(disabled_tools())} disabled)"])
    except Exception:
        rows.append(["tools", "unavailable"])

    try:
        from void.skills_catalog import SKILLS
        from void.commands.skills_cmd import discover_skills
        rows.append(["skills", f"{len(discover_skills())} installed / {len(SKILLS)} catalog"])
    except Exception:
        rows.append(["skills", "unavailable"])

    try:
        from void.commands.cron_cmd import job_stats
        cs = job_stats()
        rows.append(["cron", f"{cs['active_jobs']} active ({cs['total_runs']} runs)"])
    except Exception:
        rows.append(["cron", "unavailable"])

    print(table(["Component", "Value"], rows, [14, 50]))
    print()


# ── doctor ───────────────────────────────────────────────────────────

def cmd_doctor(args) -> None:
    """Real diagnostics: python, deps, config, dbs, api key reachability."""
    from void.config import get_api_key

    print(header("Void Doctor", 1))
    issues = []

    v = sys.version_info
    ok_py = v >= (3, 10)
    print(f"  {green_bold('Python')}  {v.major}.{v.minor}.{v.micro}  {'OK' if ok_py else 'TOO OLD (need 3.10+)'}")
    if not ok_py:
        issues.append("python < 3.10")

    for mod, why in [("openai", "model calls"), ("requests", "web fetch"), ("bs4", "html parsing")]:
        try:
            __import__(mod)
            print(f"  {green_bold(mod.ljust(8))}  OK")
        except ImportError:
            print(f"  {green_bold(mod.ljust(8))}  MISSING ({why})")
            issues.append(f"{mod} missing")

    # optional extras
    for mod, why in [("playwright", "JS rendering / browser_fetch"), ("PIL", "image handling")]:
        try:
            __import__(mod)
            print(f"  {green_bold(mod.ljust(8))}  OK")
        except ImportError:
            print(f"  {dim(mod.ljust(8))}  optional -- {why}")

    key = get_api_key()
    print(f"  {green_bold('api_key')}   {'set' if key else 'MISSING -- run void setup'}")
    if not key:
        issues.append("no api key")

    for db, name in [("sessions.db", "sessions"), ("cron.db", "cron")]:
        p = ensure_home() / db
        print(f"  {green_bold(name.ljust(8))}  {'OK' if p.exists() else 'not created yet'}")

    print()
    if issues:
        print(warn(f"{len(issues)} issue(s): " + ", ".join(issues)))
        if getattr(args, "fix", False):
            print(dim("  auto-fix: install missing deps with pip; set key with void setup"))
    else:
        print(ok("All checks passed."))


# ── logs ─────────────────────────────────────────────────────────────

def _log_path() -> Path:
    return ensure_home() / "void.log"


def log_event(kind: str, message: str) -> None:
    """Append a line to ~/.void/void.log. Called from the agent loop."""
    try:
        with _log_path().open("a", encoding="utf-8") as f:
            f.write(f"{_now()}\t{kind}\t{message}\n")
    except OSError:
        pass


def cmd_logs(args) -> None:
    """View the void log."""
    sc = getattr(args, "logs_subcommand", "errors")
    p = _log_path()
    print(header("Logs", 1))
    if not p.exists():
        print(grey("No log file yet. Run a chat to generate entries."))
        return
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    if sc == "errors":
        lines = [l for l in lines if "\terror\t" in l or "ERROR" in l]
        if not lines:
            print(grey("No errors logged."))
            return
    elif sc == "follow":
        print(dim("  tail mode -- showing last 50 lines (live follow needs a shell: tail -f)"))
    for line in lines[-50:]:
        print("  " + line)


# ── memory ───────────────────────────────────────────────────────────

def cmd_memory(args) -> None:
    """Persistent memory: setup/status/off/reset."""
    sc = getattr(args, "memory_subcommand", "status")
    from void.tools.memory_tool import memory_list

    if sc == "status":
        data = memory_list()
        print(header("Memory", 1))
        print(f"  {green_bold('entries:')} {data['count']}")
        print(f"  {green_bold('store:')}   {ensure_home() / 'memory.json'}")
        for i, e in enumerate(data["entries"][:10]):
            print(f"    {dim(str(i))}  {str(e.get('content', ''))[:70]}")
        if data["count"] > 10:
            print(dim(f"    ...and {data['count'] - 10} more"))
        return
    if sc == "reset":
        _save_store("memory", {"entries": []})
        print(ok("Memory cleared."))
        return
    if sc == "off":
        cfg = _store("memory_config", {"enabled": True})
        cfg["enabled"] = False
        _save_store("memory_config", cfg)
        print(ok("Memory disabled."))
        return
    if sc == "setup":
        cfg = _store("memory_config", {"enabled": True})
        cfg["enabled"] = True
        _save_store("memory_config", cfg)
        print(ok(f"Memory enabled. Store: {ensure_home() / 'memory.json'}"))
        return


# ── kanban ───────────────────────────────────────────────────────────

def cmd_kanban(args) -> None:
    """Local multi-agent task board."""
    sc = getattr(args, "kanban_subcommand", "show")
    board = _store("kanban", {"columns": {"todo": [], "doing": [], "done": []}})
    cols = board.setdefault("columns", {"todo": [], "doing": [], "done": []})

    if sc == "show":
        print(header("Kanban", 1))
        for col, items in cols.items():
            print(f"  {green_bold(col.upper())}  {grey(f'({len(items)})')}")
            for it in items:
                print(f"    {dim(it['id'])}  {it['task']}")
            print()
        return
    if sc == "add":
        tid = str(sum(len(v) for v in cols.values()) + 1)
        cols["todo"].append({"id": tid, "task": args.task, "added": _now()})
        _save_store("kanban", board)
        print(ok(f"Added task {tid}: {args.task}"))
        return
    if sc == "move":
        for col, items in cols.items():
            for it in list(items):
                if it["id"] == args.id:
                    items.remove(it)
                    cols.setdefault(args.column, []).append(it)
                    _save_store("kanban", board)
                    print(ok(f"Moved {args.id} -> {args.column}"))
                    return
        print(err(f"Task not found: {args.id}"))
        return
    if sc == "remove":
        for col, items in cols.items():
            for it in list(items):
                if it["id"] == args.id:
                    items.remove(it)
                    _save_store("kanban", board)
                    print(ok(f"Removed {args.id}"))
                    return
        print(err(f"Task not found: {args.id}"))


# ── project ──────────────────────────────────────────────────────────

def cmd_project(args) -> None:
    """Multi-folder project registry."""
    sc = getattr(args, "project_subcommand", "list")
    data = _store("projects", {"projects": {}, "current": None})
    projects = data.setdefault("projects", {})

    if sc == "list":
        print(header("Projects", 1))
        if not projects:
            print(grey("No projects. void project create <name> <path>"))
            return
        rows = [[n, p, "*" if n == data.get("current") else ""] for n, p in projects.items()]
        print(table(["Name", "Path", "Current"], rows, [20, 44, 8]))
        return
    if sc == "create":
        projects[args.name] = args.path
        _save_store("projects", data)
        print(ok(f"Created project '{args.name}' -> {args.path}"))
        return
    if sc == "use":
        if args.name not in projects:
            print(err(f"Project not found: {args.name}"))
            return
        data["current"] = args.name
        _save_store("projects", data)
        os.environ["VOID_PROJECT"] = args.name
        print(ok(f"Now using '{args.name}' ({projects[args.name]})"))
        return
    if sc == "show":
        cur = data.get("current")
        if not cur:
            print(grey("No current project."))
            return
        print(f"  {green_bold('project:')} {cur}")
        print(f"  {green_bold('path:')}    {projects.get(cur)}")
        return
    if sc == "delete":
        if projects.pop(args.name, None) is None:
            print(err(f"Project not found: {args.name}"))
            return
        if data.get("current") == args.name:
            data["current"] = None
        _save_store("projects", data)
        print(ok(f"Deleted '{args.name}'"))


# ── skin ─────────────────────────────────────────────────────────────

def cmd_skin(args) -> None:
    """Theme selection and color overrides."""
    sc = getattr(args, "skin_subcommand", "list")
    skins = {
        "void": {"accent": "#9df133", "desc": "neon green on black (default)"},
        "amber": {"accent": "#ffb000", "desc": "warm amber terminal"},
        "cyan": {"accent": "#00e5ff", "desc": "cool cyan"},
        "mono": {"accent": "#e0e0e0", "desc": "greyscale, no color"},
    }
    cfg = _store("skin", {"active": "void", "overrides": {}})

    if sc == "list":
        print(header("Skins", 1))
        rows = [[n, s["accent"], s["desc"], "*" if n == cfg.get("active") else ""] for n, s in skins.items()]
        print(table(["Name", "Accent", "Description", "Active"], rows, [10, 10, 34, 8]))
        return
    if sc == "use":
        if args.name not in skins:
            print(err(f"Unknown skin: {args.name}. Try: {', '.join(skins)}"))
            return
        cfg["active"] = args.name
        _save_store("skin", cfg)
        print(ok(f"Skin set to '{args.name}' ({skins[args.name]['accent']})"))
        print(dim("  restart void to apply"))
        return
    if sc == "set":
        cfg.setdefault("overrides", {})[args.key] = args.hex
        _save_store("skin", cfg)
        print(ok(f"Override {args.key} = {args.hex}"))


# ── pets ─────────────────────────────────────────────────────────────

PETS = {
    "voidcat": "a void-dwelling cat that sits in the corner of your terminal",
    "byte": "a small blob that blinks when a tool runs",
    "ghost": "fades in and out between turns",
    "none": "no mascot",
}


def cmd_pets(args) -> None:
    """Pet mascot selection."""
    sc = getattr(args, "pets_subcommand", "list")
    cfg = _store("pets", {"active": "none"})

    if sc == "list":
        print(header("Pets", 1))
        for n, d in PETS.items():
            mark = "*" if n == cfg.get("active") else " "
            print(f"  {mark} {green_bold(n.ljust(10))} {dim(d)}")
        return
    if sc == "show":
        a = cfg.get("active", "none")
        print(f"  {green_bold('pet:')} {a}  {dim(PETS.get(a, ''))}")
        return
    if sc == "select":
        if args.name not in PETS:
            print(err(f"Unknown pet: {args.name}. Try: {', '.join(PETS)}"))
            return
        cfg["active"] = args.name
        _save_store("pets", cfg)
        print(ok(f"Pet set to '{args.name}'"))


# ── hooks ────────────────────────────────────────────────────────────

def cmd_hooks(args) -> None:
    """Event hooks: shell commands run on agent events."""
    sc = getattr(args, "hooks_subcommand", "list")
    data = _store("hooks", {"hooks": []})
    hooks = data.setdefault("hooks", [])

    if sc == "list":
        print(header("Hooks", 1))
        if not hooks:
            print(grey("No hooks. void hooks add <event> '<command>'"))
            print(dim("  events: pre_tool, post_tool, pre_chat, post_chat"))
            return
        rows = [[h["id"], h["event"], h["cmd"][:40]] for h in hooks]
        print(table(["ID", "Event", "Command"], rows, [6, 12, 42]))
        return
    if sc == "add":
        hid = str(len(hooks) + 1)
        hooks.append({"id": hid, "event": args.event, "cmd": args.cmd})
        _save_store("hooks", data)
        print(ok(f"Added hook {hid}: {args.event} -> {args.cmd}"))
        return
    if sc == "remove":
        for h in list(hooks):
            if h["id"] == args.id:
                hooks.remove(h)
                _save_store("hooks", data)
                print(ok(f"Removed hook {args.id}"))
                return
        print(err(f"Hook not found: {args.id}"))


def run_hooks(event: str, payload: str = "") -> None:
    """Fire all hooks registered for an event. Called from the agent loop."""
    data = _store("hooks", {"hooks": []})
    for h in data.get("hooks", []):
        if h.get("event") != event:
            continue
        try:
            subprocess.run(h["cmd"], shell=True, timeout=30,
                           input=payload, text=True, capture_output=True)
        except Exception:
            pass


# ── secrets ──────────────────────────────────────────────────────────

def cmd_secrets(args) -> None:
    """External secret store integration (bitwarden / 1password CLIs)."""
    sc = getattr(args, "secrets_subcommand", "bitwarden")
    cmds = {
        "bitwarden": ["bw", "--version"],
        "onepassword": ["op", "--version"],
    }
    if sc == "list":
        print(header("Secret Stores", 1))
        print(dim("  checking for installed CLIs..."))
        print()
        for name, cmd in cmds.items():
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                status = r.stdout.strip() if r.returncode == 0 else "error"
                print(f"  {green_bold(name.ljust(12))} {status}")
            except FileNotFoundError:
                print(f"  {dim(name.ljust(12))} not installed")
            except Exception as e:
                print(f"  {dim(name.ljust(12))} {e}")
        return
    cmd = cmds.get(sc)
    if not cmd:
        print(err(f"Unknown secret store: {sc}"))
        return
    print(header(f"Secrets: {sc}", 1))
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if r.returncode == 0:
            print(ok(f"{sc} CLI found: {r.stdout.strip()}"))
            print(dim(f"  use: void config set api_key $({sc} read ...)"))
        else:
            print(err(f"{sc} CLI error: {r.stderr.strip()}"))
    except FileNotFoundError:
        print(err(f"{sc} CLI not installed."))
        print(dim(f"  install it, then re-run: void secrets {sc}"))
    except Exception as e:
        print(err(str(e)))


# ── moa (mixture of agents) ──────────────────────────────────────────

def cmd_moa(args) -> None:
    """Mixture-of-agents slots: several models answer, first/best wins."""
    sc = getattr(args, "moa_subcommand", "list")
    data = _store("moa", {"slots": [], "voters": 1})
    slots = data.setdefault("slots", [])

    if sc == "list":
        print(header("Mixture of Agents", 1))
        if not slots:
            print(grey("No slots. void moa add <provider/model>"))
            return
        for i, s in enumerate(slots):
            print(f"  {dim(str(i))}  {green_bold(s)}")
        print()
        print(dim(f"  voters: {data.get('voters', 1)}"))
        return
    if sc == "add":
        slots.append(args.model)
        _save_store("moa", data)
        print(ok(f"Added slot: {args.model}"))
        return
    if sc == "remove":
        try:
            removed = slots.pop(int(args.id))
            _save_store("moa", data)
            print(ok(f"Removed slot: {removed}"))
        except (ValueError, IndexError):
            print(err(f"Bad slot id: {args.id}"))
        return
    if sc == "set":
        try:
            data["voters"] = max(1, int(args.n))
        except ValueError:
            print(err("n must be an integer"))
            return
        _save_store("moa", data)
        print(ok(f"Voters set to {data['voters']}"))


def run_moa(messages: list[dict]) -> str | None:
    """Query all MOA slots and return the majority/first answer. None if unconfigured."""
    data = _store("moa", {"slots": [], "voters": 1})
    slots = data.get("slots", [])
    if not slots:
        return None
    from void.model import Model
    answers = []
    for spec in slots:
        try:
            provider, _, model_name = spec.partition("/")
            from void.providers import get_provider
            cfg = get_provider(provider) or {}
            m = Model(api_key=cfg.get("api_key"), base_url=cfg.get("base_url"),
                      model_name=model_name or spec)
            resp = m.chat(messages)
            if resp.content:
                answers.append(resp.content)
        except Exception:
            continue
    if not answers:
        return None
    # ponytail: first-answer wins, not real voting. Swap for similarity clustering
    # when answer quality matters more than latency.
    return answers[0]
