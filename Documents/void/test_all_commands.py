"""Realistic test of every Void CLI command. Runs each against real state.

Run: python test_all_commands.py
"""
import json
import subprocess
import sys
from pathlib import Path

RESULTS = []
ROOT = Path(__file__).parent


def run(args, timeout=90):
    r = subprocess.run([sys.executable, "-m", "void.cli"] + args,
                       capture_output=True, text=True, timeout=timeout, cwd=ROOT)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def check(label, args, must_contain=None, must_not_contain=None, allow_fail=False):
    try:
        code, out = run(args)
    except subprocess.TimeoutExpired:
        RESULTS.append((label, "FAIL", "timeout"))
        print(f"  [FAIL] {label:34} timeout")
        return ""
    bad = []
    if must_contain and not any(s.lower() in out.lower() for s in must_contain):
        bad.append(f"missing {must_contain}")
    if must_not_contain:
        for s in must_not_contain:
            if s.lower() in out.lower():
                bad.append(f"contains {s!r}")
    if code != 0 and not allow_fail:
        bad.append(f"exit {code}")
    if bad:
        RESULTS.append((label, "FAIL", "; ".join(bad)))
        print(f"  [FAIL] {label:34} {'; '.join(bad)}")
    else:
        RESULTS.append((label, "PASS", ""))
        print(f"  [PASS] {label:34} {out.strip().splitlines()[-1][:44] if out.strip() else ''}")
    return out


BANNED = ["coming soon", "Traceback", "NameError", "ModuleNotFoundError"]

print("=" * 70)
print(" VOID CLI COMMAND TEST SUITE -- realistic")
print("=" * 70)

print("\n-- top level " + "-" * 57)
check("void --help", ["--help"], must_contain=["chat", "skills", "cron"], must_not_contain=BANNED)

print("\n-- status / doctor " + "-" * 52)
out = check("void status", ["status"], must_contain=["model", "tools"], must_not_contain=BANNED)
check("void doctor", ["doctor"], must_contain=["Python", "openai"], must_not_contain=BANNED)

print("\n-- config " + "-" * 58)
check("void config show", ["config", "show"], must_not_contain=BANNED)
check("void config get model", ["config", "get", "model"], must_not_contain=BANNED)

print("\n-- model / auth / fallback " + "-" * 44)
check("void model list", ["model", "list"], must_not_contain=BANNED)
check("void model show", ["model", "show"], must_not_contain=BANNED)
check("void auth list", ["auth", "list"], must_not_contain=BANNED)
check("void auth status", ["auth", "status"], must_not_contain=BANNED)
check("void fallback list", ["fallback", "list"], must_not_contain=BANNED)

print("\n-- sessions " + "-" * 57)
check("void sessions list", ["sessions", "list"], must_not_contain=BANNED)
check("void sessions stats", ["sessions", "stats"], must_contain=["Sessions"], must_not_contain=BANNED)
check("void sessions browse", ["sessions", "browse"], must_not_contain=BANNED)

print("\n-- skills " + "-" * 58)
check("void skills list", ["skills", "list"], must_not_contain=BANNED)
check("void skills browse", ["skills", "browse"], must_contain=["skills available"], must_not_contain=BANNED)
check("void skills search humanizer", ["skills", "search", "humanizer"], must_contain=["humanizer"], must_not_contain=BANNED)
check("void skills inspect humanizer", ["skills", "inspect", "humanizer"], must_contain=["humanizer"], must_not_contain=BANNED)

print("\n-- tools " + "-" * 58)
out = check("void tools list", ["tools", "list"], must_contain=["system_shell"], must_not_contain=BANNED)
check("void tools disable get_time", ["tools", "disable", "get_time"], must_contain=["Disabled"], must_not_contain=BANNED)
code, o = run(["-c", "from void.tools.registry import get_schemas; print('get_time' in [s['function']['name'] for s in get_schemas()])"])
check("void tools enable get_time", ["tools", "enable", "get_time"], must_contain=["Enabled"], must_not_contain=BANNED)

print("\n-- cron " + "-" * 59)
check("void cron list", ["cron", "list"], must_not_contain=BANNED)
out = check("void cron create 60m 'cmd test'", ["cron", "create", "60m", "cmd test"], must_contain=["Created"], must_not_contain=BANNED)
import re
m = re.search(r"Created job (\w+)", out)
job_id = m.group(1) if m else None
if job_id:
    full = None
    code, o = run(["-c", f"from void.commands.cron_cmd import list_jobs; print([j['id'] for j in list_jobs() if j['id'].startswith('{job_id}')][0])"])
    full = o.strip() if code == 0 else None
    if full:
        check("void cron pause", ["cron", "pause", full], must_contain=["Paused"], must_not_contain=BANNED)
        check("void cron resume", ["cron", "resume", full], must_contain=["Resumed"], must_not_contain=BANNED)
        check("void cron remove", ["cron", "remove", full], must_contain=["Removed"], must_not_contain=BANNED)
check("void cron status", ["cron", "status"], must_not_contain=BANNED)
check("void cron tick", ["cron", "tick"], must_not_contain=BANNED)
check("void cron logs", ["cron", "logs"], must_not_contain=BANNED)

print("\n-- memory / kanban / project " + "-" * 42)
check("void memory status", ["memory", "status"], must_contain=["entries"], must_not_contain=BANNED)
check("void kanban show", ["kanban", "show"], must_contain=["TODO"], must_not_contain=BANNED)
check("void kanban add 'cli test task'", ["kanban", "add", "cli test task"], must_contain=["Added"], must_not_contain=BANNED)
check("void project list", ["project", "list"], must_not_contain=BANNED)

print("\n-- skin / pets / hooks " + "-" * 47)
check("void skin list", ["skin", "list"], must_contain=["void"], must_not_contain=BANNED)
check("void pets list", ["pets", "list"], must_contain=["voidcat"], must_not_contain=BANNED)
check("void hooks list", ["hooks", "list"], must_not_contain=BANNED)
check("void hooks add pre_tool 'echo hi'", ["hooks", "add", "pre_tool", "echo hi"], must_contain=["Added"], must_not_contain=BANNED)

print("\n-- secrets / moa / mcp / webhooks " + "-" * 36)
check("void secrets list", ["secrets", "list"], must_not_contain=BANNED)
check("void moa list", ["moa", "list"], must_not_contain=BANNED)
check("void mcp list", ["mcp", "list"], must_not_contain=BANNED)
check("void mcp catalog", ["mcp", "catalog"], must_contain=["filesystem"], must_not_contain=BANNED)
check("void webhooks list", ["webhooks", "list"], must_not_contain=BANNED)
check("void webhooks subscribe test-hook", ["webhooks", "subscribe", "test-hook"], must_contain=["Subscribed"], must_not_contain=BANNED)

print("\n-- logs " + "-" * 60)
check("void logs errors", ["logs", "errors"], must_not_contain=BANNED)

p = sum(1 for _, s, _ in RESULTS if s == "PASS")
f = sum(1 for _, s, _ in RESULTS if s == "FAIL")
print("\n" + "=" * 70)
print(f" COMMANDS: {p} passed, {f} failed  (of {len(RESULTS)} checks)")
print("=" * 70)
if f:
    print("\nfailures:")
    for label, s, d in RESULTS:
        if s == "FAIL":
            print(f"  {label}: {d}")

Path(ROOT / "command_test_results.json").write_text(
    json.dumps([{"cmd": l, "status": s, "detail": d} for l, s, d in RESULTS], indent=2), encoding="utf-8")
sys.exit(1 if f else 0)
