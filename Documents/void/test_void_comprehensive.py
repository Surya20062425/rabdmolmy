"""Comprehensive Void CLI functionality tests — no API keys, no network needed."""

import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timezone

# --- setup: isolate Void home to a temp dir ---
TMP_VOID = Path(tempfile.mkdtemp(prefix="void_test_"))
os.environ["VOID_HOME"] = str(TMP_VOID)

# Ensure the void package is importable from the project dir
PROJECT = Path("/c/Users/b7993/Documents/void")
sys.path.insert(0, str(PROJECT))

import void
from void import config, providers, theme, sessions
from void.commands import skills_cmd
from void import skills_catalog
from void.tools import registry, system, web, email, example
from void.model import Model, MissingApiKeyError
from void.agent import run, _is_install_command, _inject_skills
from void.cli import (
    cmd_chat, cmd_config, cmd_setup, cmd_model, cmd_auth, cmd_fallback,
    cmd_sessions, cmd_skills, cmd_cron, cmd_webhooks, cmd_mcp, cmd_tools,
    cmd_project, cmd_kanban, cmd_skin, cmd_pets, cmd_memory, cmd_secrets,
    cmd_moa, cmd_hooks, cmd_logs, cmd_doctor, cmd_status, cmd_upgrade,
    _COMMAND_DISPATCH, SUBCOMMAND_HELP, VOID_HELP,
)

passed = 0
failed = 0
errors = []

def report(name, ok_val, detail=""):
    global passed, failed
    if ok_val:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        errors.append((name, detail))
        print(f"  FAIL  {name}: {detail}")

def assert_true(v, d=""):
    return v is True, d or f"expected truthy, got {v!r}"

def assert_false(v, d=""):
    return v is False, d or f"expected falsy, got {v!r}"

def assert_eq(a, b, d=""):
    return a == b, d or f"expected {b!r}, got {a!r}"

def assert_contains(hay, needle, d=""):
    return needle in hay, d or f"expected {needle!r} in {hay!r}"

def assert_isinstance(v, t, d=""):
    return isinstance(v, t), d or f"expected {t.__name__}, got {type(v).__name__}"

print(f"Void home: {TMP_VOID}")
print(f"Python: {sys.version.split()[0]}")
print()

# ═══════════════════════════════════════════════════════════
# 1. PACKAGE / IMPORTS
# ═══════════════════════════════════════════════════════════
print("═══ package / imports ═══")
ok, d = assert_isinstance(void, type(sys))
report("void package importable", ok, d)
ok, d = assert_true(hasattr(void, "cli"), "void.cli missing")
report("void.cli exists", ok, d)

# ═══════════════════════════════════════════════════════════
# 2. CONFIG MODULE
# ═══════════════════════════════════════════════════════════
print("\n═══ config ═══")
cfg = config.load()
report("config.load() returns dict", isinstance(cfg, dict))
report("config.load() empty when fresh", cfg == {})

config.set_key("api_key", "sk-test123")
cfg2 = config.load()
report("config.set_key saves", cfg2.get("api_key") == "sk-test123")

config.set_key("base_url", "https://custom.api/v1")
cfg3 = config.load()
report("config.set_key base_url", cfg3.get("base_url") == "https://custom.api/v1")

val = config.get("api_key")
report("config.get api_key", val == "sk-test123")
val_missing = config.get("nonexistent", "default")
report("config.get missing key returns default", val_missing == "default")

config.set_key("api_key", "")
report("config.get empty key returns None", config.get("api_key") is None or config.get("api_key") == "")

# masked_api_key
mk = theme.masked_api_key("sk-abcdef1234567890abcdef")
report("masked_api_key hides key", mk != "sk-abcdef1234567890abcdef" and "..." in mk)

# ensure_home
home = config.ensure_home()
report("ensure_home returns Path", isinstance(home, Path))
report("ensure_home creates dir", home.exists())

# save/load round-trip
config.save({"a": 1, "b": "hello"})
loaded = config.load()
report("config.save round-trip", loaded.get("a") == 1 and loaded.get("b") == "hello")

# ═══════════════════════════════════════════════════════════
# 3. PROVIDERS MODULE
# ═══════════════════════════════════════════════════════════
print("\n═══ providers ═══")
providers.add_provider("testp", "key-test", "https://api.test.com/v1", ["model-a", "model-b"], "test provider")
p = providers.get_provider("testp")
report("add_provider returns config", p is not None)
report("add_provider api_key", p["api_key"] == "key-test")
report("add_provider base_url", p["base_url"] == "https://api.test.com/v1")
report("add_provider models", p["models"] == ["model-a", "model-b"])
report("add_provider description", p["description"] == "test provider")

all_provs = providers.list_providers()
report("list_providers returns list", isinstance(all_provs, list))
names = [n for n, _ in all_provs]
report("list_providers includes testp", "testp" in names)

providers.add_fallback("testp")
chain = providers.get_fallback_chain()
report("add_fallback adds to chain", "testp" in chain)

providers.set_current_model("testp/model-a")
current = providers.get_current_model()
report("set_current_model / get_current_model", current == "testp/model-a")

pn, bu, ak = providers.resolve_model()
report("resolve_model returns provider info", pn == "testp")
report("resolve_model base_url", bu == "https://api.test.com/v1")
report("resolve_model api_key", ak == "key-test")

providers.remove_provider("testp")
report("remove_provider deletes provider", providers.get_provider("testp") is None)
chain2 = providers.get_fallback_chain()
report("remove_provider scrubs fallback", "testp" not in chain2)

# ═══════════════════════════════════════════════════════════
# 4. THEME MODULE
# ═══════════════════════════════════════════════════════════
print("\n═══ theme ═══")

# color helpers
green_hello = theme.g("hello")
report("g() wraps text", "\033[38;2;0;255;65m" in green_hello and "\033[0m" in green_hello)
report("gb() wraps bold", "\033[1m" in theme.gb("hello"))
report("w() wraps white", "\033[38;2;224;224;224m" in theme.w("hello"))
report("gr() wraps grey", "\033[38;2;136;136;136m" in theme.gr("hello"))
report("r() wraps red", "\033[38;2;255;51;51m" in theme.r("hello"))

# symbols
report("CHECK is checkmark", theme.CHECK == "\u2713")
report("CROSS is crossmark", theme.CROSS == "\u2717")
report("BLOCK is block", theme.BLOCK == "\u2588")
report("DASH is em-dash", theme.DASH == "\u2014")

# logos
lv = theme.logo_void()
report("logo_void() returns string", isinstance(lv, str) and len(lv) > 0)
lbs = theme.logo_big_s()
report("logo_big_s() returns string", isinstance(lbs, str) and len(lbs) > 0)

# MatrixRain
mr = theme.MatrixRain(width=10, height=5)
frame = mr.frame()
report("MatrixRain.frame() returns string", isinstance(frame, str) and len(frame) > 0)
lines = frame.split("\n")
report("MatrixRain.frame() has correct height", len(lines) == 5)

# status bar
sb = theme.status_bar(ctx="testctx", progress=0.5, latency_s=2.3)
report("status_bar() returns string", isinstance(sb, str) and len(sb) > 0)
report("status_bar contains ctx", "testctx" in sb)

# input_line
il = theme.input_line("test prompt")
report("input_line() returns string", isinstance(il, str))
report("input_line contains > prompt char", ">" in il)

# box wrapping
boxed = theme.box(["line one", "line two"])
report("box() wraps content", "┌" in boxed and "┐" in boxed)

# section / table / header
sh = theme.section("Test")
report("section() returns string", isinstance(sh, str) and "Test" in sh)

tbl = theme.table(["Col1", "Col2"], [["a", "b"], ["c", "d"]], [10, 10])
report("table() returns string", isinstance(tbl, str) and "Col1" in tbl)

hdr = theme.header("Test Header", 1)
report("header() returns string", isinstance(hdr, str) and "Test Header" in hdr)

# banner / logo_ascii
bn = theme.banner("Test Banner")
report("banner() returns string", isinstance(bn, str) and "Test Banner" in bn)

logo = theme.logo_ascii()
report("logo_ascii() returns string", isinstance(logo, str) and len(logo) > 0)

# ok / err / warn
ok_msg = theme.ok("success")
report("ok() prefixes success", "success" in ok_msg)
err_msg = theme.err("failure")
report("err() prefixes failure", "failure" in err_msg)
warn_msg = theme.warn("caution")
report("warn() prefixes caution", "caution" in warn_msg)

# cmd_entry
ce = theme.cmd_entry("void chat", "run chat")
report("cmd_entry() returns string", isinstance(ce, str))

# bullet
bl = theme.bullet("item")
report("bullet() returns string", isinstance(bl, str) and "item" in bl)

# section_divider / divider
sd = theme.section_divider()
report("section_divider() returns string", isinstance(sd, str))
div = theme.divider()
report("divider() returns string", isinstance(div, str))

# tagged
tg = theme.tagged("key", "value")
report("tagged() returns string", isinstance(tg, str))

# masked_api_key
import re as _re
mk2 = theme.masked_api_key("sk-12345678901234567890")
report("masked_api_key has ellipsis", "..." in mk2)
_visible = _re.sub(r"\x1b\[[0-9;]*m", "", mk2)
report("masked_api_key shorter than raw (20)", len(_visible) < 20)

# symbol
sym = theme.symbol("s")
report("symbol() returns string", isinstance(sym, str))

# prompt_text
pt = theme.prompt_text(">")
report("prompt_text() returns string", isinstance(pt, str))

# start_screen
ss = theme.start_screen()
report("start_screen() returns string", isinstance(ss, str) and len(ss) > 0)

# green_line
gl = theme.green_line("---")
report("green_line() returns string", isinstance(gl, str))

# ═══════════════════════════════════════════════════════════
# 5. TOOL REGISTRY
# ═══════════════════════════════════════════════════════════
print("\n═══ tool registry ═══")

# Clear registry for clean test
from void.tools import registry as reg_mod
reg_mod.reset_registry()

reg_mod.register("test_tool", {"name": "test_tool", "description": "test", "parameters": {"type": "object", "properties": {}}}, lambda: "hello")
tools = reg_mod.list_tools()
report("register + list_tools", "test_tool" in tools)

schemas = reg_mod.get_schemas()
report("get_schemas returns list", isinstance(schemas, list))
report("get_schemas has correct shape", any(s.get("type") == "function" for s in schemas))

result = reg_mod.dispatch("test_tool", {})
report("dispatch test_tool returns hello directly", result == "hello")

err_result = reg_mod.dispatch("nonexistent_tool", {})
report("dispatch unknown tool returns error JSON", "error" in err_result)

# dispatch a valid tool — system_pwd (returns JSON)
# registry is already populated via auto-discovery above; dispatch needs it populated
pwd_result = reg_mod.dispatch("system_pwd", {})
report("dispatch system_pwd returns JSON string", isinstance(pwd_result, str))
pwd_obj = json.loads(pwd_result)
report("dispatch system_pwd has cwd", "cwd" in pwd_obj)

# Test auto-discovery: tools should be registered after a fresh reset
reg_mod.reset_registry()
all_tools = reg_mod.list_tools()
report("auto-discovery finds system tools", "system_read_file" in all_tools)
report("auto-discovery finds web tools", "web_fetch" in all_tools)
report("auto-discovery finds example tool", "get_time" in all_tools)
report("auto-discovery finds task tools", "task_list" in all_tools)
report("auto-discovery finds delegate tools", "delegate_task" in all_tools)

# ═══════════════════════════════════════════════════════════
# 6. SYSTEM TOOLS
# ═══════════════════════════════════════════════════════════
print("\n═══ system tools ═══")

# system_pwd
pwd_result = system.system_pwd()
report("system_pwd returns dict", isinstance(pwd_result, dict))
report("system_pwd has cwd", "cwd" in pwd_result)
report("system_pwd cwd matches os.getcwd()", pwd_result["cwd"] == os.getcwd())

# system_ls
ls_result = system.system_ls(str(TMP_VOID))
report("system_ls returns dict", isinstance(ls_result, dict))
report("system_ls has entries", "entries" in ls_result)
report("system_ls has count", ls_result.get("count", 0) >= 0)

# system_ls nonexistent
ls_bad = system.system_ls("/nonexistent/path_12345")
report("system_ls nonexistent path returns error", "error" in ls_bad)

# system_read_file / system_write_file
test_file = TMP_VOID / "test_write.txt"
write_result = system.system_write_file(str(test_file), "hello world")
report("system_write_file success", write_result.get("success") is True)
report("system_write_file returns bytes", "bytes" in write_result)

read_result = system.system_read_file(str(test_file))
report("system_read_file success", read_result.get("content") == "hello world")
report("system_read_file total_lines", read_result.get("total_lines") == 1)

# system_read_file nonexistent
read_bad = system.system_read_file("/nonexistent/file.txt")
report("system_read_file missing returns error", "error" in read_bad)

# system_write_file append
system.system_write_file(str(test_file), "\nappended", append=True)
read2 = system.system_read_file(str(test_file))
report("system_write_file append", "appended" in read2["content"])

# system_shell
sh_result = system.system_shell("echo hello_void")
report("system_shell success", sh_result.get("success") is True)
report("system_shell stdout", "hello_void" in sh_result.get("stdout", ""))
report("system_shell has exit_code", "exit_code" in sh_result)
report("system_shell has stderr", "stderr" in sh_result)

# system_shell timeout
sh_timeout = system.system_shell("timeout 5 /t 5 >nul 2>&1 || echo slow", timeout=1)
report("system_shell handles timeout", "error" in sh_timeout or sh_timeout.get("exit_code") is not None)

# system_env_var
ev_result = system.system_env_var("VOID_HOME")
report("system_env_var returns dict", isinstance(ev_result, dict))
report("system_env_var VOID_HOME set", ev_result.get("exists") is True)
report("system_env_var value matches", ev_result.get("value") == str(TMP_VOID))

# ═══════════════════════════════════════════════════════════
# 7. WEB TOOLS
# ═══════════════════════════════════════════════════════════
print("\n═══ web tools ═══")

# web_fetch invalid URL
wf = web.web_fetch("not-a-url")
report("web_fetch invalid URL returns error", "error" in wf)

# web_extract_text invalid URL
we = web.web_extract_text("not-a-url")
report("web_extract_text invalid URL returns error", "error" in we)

# web_search invalid query (no network — should error gracefully)
ws = web.web_search("test query")
report("web_search returns dict", isinstance(ws, dict))
# Either has results or error (offline)
report("web_search has result_count or error", "result_count" in ws or "error" in ws)

# ═══════════════════════════════════════════════════════════
# 8. EMAIL TOOLS
# ═══════════════════════════════════════════════════════════
print("\n═══ email tools ═══")

# All email tools require credentials — test missing-credential paths
el = email.email_list()
report("email_list no creds returns error", "error" in el)

er = email.email_read("1")
report("email_read no creds returns error", "error" in er)

es = email.email_send("to@test.com", "subj", "body")
report("email_send no creds returns error", "error" in es)

ese = email.email_search()
report("email_search no creds returns error", "error" in ese)

# Test credential caching
email._cache_creds("testlabel", imap_host="imap.test.com", imap_port=993, imap_user="u", imap_pass="p")
creds = email._get_creds("testlabel")
report("email _cache_creds saves", creds.get("imap_host") == "imap.test.com")
report("email _cache_creds saves user", creds.get("imap_user") == "u")

email._cfg()  # load registry
cfg = email._cfg()
report("email _cfg returns dict", isinstance(cfg, dict))
report("email _cfg has email key", "email" in cfg)

# Cleanup email config
if "email" in cfg:
    del cfg["email"]
    email.CONFIG.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")

# ═══════════════════════════════════════════════════════════
# 9. EXAMPLE TOOL
# ═══════════════════════════════════════════════════════════
print("\n═══ example tool ═══")

time_result = example.get_time("UTC")
report("get_time returns dict", isinstance(time_result, dict))
report("get_time has time field", "time" in time_result)
report("get_time has tz field", time_result.get("tz") == "UTC")
report("get_time time is ISO format", "T" in time_result.get("time", ""))

# ═══════════════════════════════════════════════════════════
# 10. MODEL MODULE
# ═══════════════════════════════════════════════════════════
print("\n═══ model ═══")

# MissingApiKeyError when no key
try:
    Model()
    report("Model() without key raises MissingApiKeyError", False)
except MissingApiKeyError:
    report("Model() without key raises MissingApiKeyError", True)
except Exception as e:
    report("Model() without key raises MissingApiKeyError", False, f"got {type(e).__name__}: {e}")

# Mock Model.chat
mock_model = MagicMock()
mock_model.chat.return_value = MagicMock(content="hello from model", tool_calls=[])
resp = mock_model.chat([{"role": "user", "content": "hi"}])
report("Model.chat returns ChatResponse-like", resp.content == "hello from model")

# ChatResponse with tool_calls
from void.model import ChatResponse
cr = ChatResponse(content=None, tool_calls=[MagicMock(id="c1", function=MagicMock(name="fn", arguments="{}"))])
report("ChatResponse stores tool_calls", len(cr.tool_calls) == 1)

# ═══════════════════════════════════════════════════════════
# 11. AGENT LOOP
# ═══════════════════════════════════════════════════════════
print("\n═══ agent loop ═══")

# _is_install_command
report("_is_install_command pip install", _is_install_command("pip install requests") is True)
report("_is_install_command npm install", _is_install_command("npm install lodash") is True)
report("_is_install_command safe command", _is_install_command("echo hello") is False)
report("_is_install_command case insensitive", _is_install_command("PIP INSTALL foo") is True)
report("_is_install_command apt install", _is_install_command("apt install python3") is True)

# _inject_skills with no skills — should not crash
msgs = [{"role": "user", "content": "hi"}]
_inject_skills(msgs)
report("_inject_skills no skills doesn't crash", msgs[0]["content"] == "hi")

# _inject_skills with mock skills — injection now sources from the catalog +
# vendored dir, so point VOID_SKILLS_DIR at a temp skill and name it in the msg.
import tempfile as _tf
_tmp_skills = Path(_tf.mkdtemp(prefix="void_skills_"))
_skill_dir = _tmp_skills / "testskill"
_skill_dir.mkdir()
(_skill_dir / "SKILL.md").write_text("---\nname: testskill\ndescription: a test skill\n---\nbody here\n", encoding="utf-8")

with patch.object(skills_catalog, "VOID_SKILLS_DIR", _tmp_skills):
    msgs2 = [{"role": "user", "content": "please use testskill now"}]
    _inject_skills(msgs2)
    # injection prepends a system message, so the list grows; the skill text
    # lands in the system message, not the user's.
    injected = any("testskill" in m.get("content", "") for m in msgs2)
    report("_inject_skills injects a named vendored skill", injected)

# Agent loop with mocked model — text response only
mock_m = MagicMock()
mock_m.chat.return_value = MagicMock(content="the answer is 42", tool_calls=[])
from void.model import Model as RealModel
m = RealModel.__new__(RealModel)
m._client = None
m.chat = mock_m.chat
result = run(m, [{"role": "user", "content": "what is 2+2?"}])
report("agent loop returns text answer", "42" in result)

# Agent loop with tool call then text
mock_m2 = MagicMock()
mock_m2.chat.side_effect = [
    MagicMock(content=None, tool_calls=[MagicMock(id="c1", function=MagicMock(name="system_pwd", arguments="{}"))]),
    MagicMock(content="your cwd is /tmp", tool_calls=[]),
]
m2 = RealModel.__new__(RealModel)
m2._client = None
m2.chat = mock_m2.chat
result2 = run(m2, [{"role": "user", "content": "where am I?"}])
report("agent loop dispatches tool and returns final", "cwd" in result2 or "/tmp" in result2)
report("agent loop made 2 model calls", mock_m2.chat.call_count == 2)

# ═══════════════════════════════════════════════════════════
# 12. CLI — SUBCOMMAND DISPATCH
# ═══════════════════════════════════════════════════════════
print("\n═══ CLI dispatch ═══")

report("all commands in dispatch table", len(_COMMAND_DISPATCH) >= 24)
expected_cmds = ["chat","config","setup","model","auth","fallback","sessions","skills",
                 "cron","webhooks","mcp","tools","project","kanban","skin","pets",
                 "memory","secrets","moa","hooks","logs","doctor","status","upgrade"]
for cmd in expected_cmds:
    in_dispatch = cmd in _COMMAND_DISPATCH
    report(f"dispatch has '{cmd}'", in_dispatch)

# ═══════════════════════════════════════════════════════════
# 13. CLI — HELP TEXT
# ═══════════════════════════════════════════════════════════
print("\n═══ CLI help text ═══")

report("VOID_HELP is non-empty", len(VOID_HELP) > 100)
report("VOID_HELP mentions agent", "agent" in VOID_HELP.lower())
report("VOID_HELP mentions neon green", "neon" in VOID_HELP.lower())

# void --help: cli_main takes no args (argparse calls sys.exit, so test differently)
# Instead test that main() is callable without crashing on --help via subprocess

for cmd_name, help_text in SUBCOMMAND_HELP.items():
    report(f"SUBCOMMAND_HELP['{cmd_name}'] non-empty", len(help_text) > 50)

# ═══════════════════════════════════════════════════════════
# 14. CLI — COMMAND HANDLERS (stubs & simple ones)
# ═══════════════════════════════════════════════════════════
print("\n═══ CLI command handlers ═══")

# cmd_config show (empty config)
class ArgsShow:
    config_cmd = "show"
    show = True
cmd_config(ArgsShow())
report("cmd_config show runs without error", True)  # if it raised, test would fail

# cmd_config set/get
class ArgsSet:
    config_cmd = "set"
    set_key = "test_key"
    set_value = "test_value"
    show = False
    get_key_opt = None
cmd_config(ArgsSet())
cfg_check = config.load()
report("cmd_config set saves value", cfg_check.get("test_key") == "test_value")

class ArgsGet:
    config_cmd = "get"
    get_key = "test_key"
    show = False
    set_key_opt = None
    set_value = None
# capture stdout
import io
import subprocess
from contextlib import redirect_stdout
buf = io.StringIO()
with redirect_stdout(buf):
    cmd_config(ArgsGet())
output = buf.getvalue()
report("cmd_config get prints value", "test_value" in output)

# cmd_tools list
class ArgsToolsList:
    tools_subcommand = "list"
    pass
buf2 = io.StringIO()
with redirect_stdout(buf2):
    cmd_tools(ArgsToolsList())
output2 = buf2.getvalue()
report("cmd_tools list runs", "Tool" in output2 or "tool" in output2.lower())

# cmd_stub commands — each stub handler needs specific attrs to avoid getattr crash
stub_handlers = {
    "webhooks": (cmd_webhooks, ["name"]),
    "mcp": (cmd_mcp, ["name"]),
    "project": (cmd_project, []),
    "kanban": (cmd_kanban, []),
    "skin": (cmd_skin, []),
    "pets": (cmd_pets, []),
    "memory": (cmd_memory, []),
    "secrets": (cmd_secrets, []),
    "moa": (cmd_moa, []),
    "hooks": (cmd_hooks, []),
    "logs": (cmd_logs, []),
    "doctor": (cmd_doctor, []),
    "status": (cmd_status, []),
}
for stub_cmd, (stub_handler, needed) in stub_handlers.items():
    class StubArgs:
        pass
    sa = StubArgs()
    for attr in needed:
        setattr(sa, attr, None)
    # stub handlers just print, shouldn't crash
    buf3 = io.StringIO()
    with redirect_stdout(buf3):
        stub_handler(sa)
    report(f"cmd_{stub_cmd} stub runs", True)

# ═══════════════════════════════════════════════════════════
# 15. CLI — ARG PARSING
# ═══════════════════════════════════════════════════════════
print("\n═══ CLI arg parsing ═══")

# We can test the CLI entry by importing and running parser directly
from void.cli import main as cli_main
import argparse

# Test: void --help should not crash. main() reads sys.argv, so drive it via
# subprocess rather than passing args.
buf4 = io.StringIO()
try:
    _r = subprocess.run([sys.executable, "-m", "void.cli", "--help"],
                        capture_output=True, text=True, timeout=60)
    help_output = (_r.stdout or "") + (_r.stderr or "")
    report("void --help prints usage", "usage:" in help_output.lower() or "SKULL" in help_output)
except Exception as e:
    report("void --help", False, str(e)[:100])

# Test: void config --help
buf5 = io.StringIO()
try:
    _r5 = subprocess.run([sys.executable, "-m", "void.cli", "config", "--help"],
                         capture_output=True, text=True, timeout=60)
    config_help = (_r5.stdout or "") + (_r5.stderr or "")
    report("void config --help works", "config" in config_help.lower())
except Exception as e:
    report("void config --help", False, str(e)[:100])

# ═══════════════════════════════════════════════════════════
# 16. SESSIONS MODULE
# ═══════════════════════════════════════════════════════════
print("\n═══ sessions ═══")

# list_sessions (empty)
sess_list = sessions.list_sessions()
report("sessions.list_sessions returns list", isinstance(sess_list, list))
report("sessions empty when fresh", len(sess_list) == 0)

# create_session — returns a session dict
sess_created = sessions.create_session("test session")
report("sessions.create_session returns dict", isinstance(sess_created, dict))
sid = sess_created["id"]
report("sessions.create_session has id", isinstance(sid, str) and len(sid) > 0)

# get_session
sess = sessions.get_session(sid)
report("sessions.get_session returns dict", isinstance(sess, dict))
report("sessions.get_session title", sess.get("title") == "test session")

# add_message
sessions.add_message(sid, "user", "hello")
sessions.add_message(sid, "assistant", "hi there")
msgs = sessions.list_messages(sid)
report("sessions.add_message + list_messages", len(msgs) == 2)
report("sessions message roles", msgs[0]["role"] == "user" and msgs[1]["role"] == "assistant")

# sessions.rename_session — returns the updated session dict
renamed = sessions.rename_session(sid, "renamed session")
report("sessions.rename_session returns dict", isinstance(renamed, dict))
report("sessions.rename_session has new title", renamed.get("title") == "renamed session")
sess2 = sessions.get_session(sid)
report("sessions.get_session after rename", sess2.get("title") == "renamed session")

# session_stats
stats = sessions.session_stats()
report("sessions.session_stats returns dict", isinstance(stats, dict))
report("sessions.session_stats has count", stats.get("session_count", 0) >= 1)

# export_session
export_path = TMP_VOID / "export_test.json"
exp = sessions.export_session(sid, str(export_path))
report("sessions.export_session returns path", isinstance(exp, str) and Path(exp).exists())

# delete_session
del_ok = sessions.delete_session(sid)
report("sessions.delete_session", del_ok is True)
report("sessions deleted", sessions.get_session(sid) is None)

# ═══════════════════════════════════════════════════════════
# 17. SKILLS MODULE
# ═══════════════════════════════════════════════════════════
print("\n═══ skills ═══")

# discover_skills (empty registry)
skills = skills_cmd.discover_skills()
report("skills.discover_skills returns list", isinstance(skills, list))
report("skills empty when no registry", len(skills) == 0)

# install_skill — requires URL or repo; test the ValueError path
try:
    skills_cmd.install_skill("bad", url=None, repo=None)
    report("install_skill no source raises ValueError", False)
except ValueError as e:
    report("install_skill no source raises ValueError", "No content source" in str(e))

# install_skill from URL (mocked)
skill_content = """---
name: test-skill
description: A test skill
version: 0.1.0
---
# Test Skill

This is a test.
"""
with patch("void.commands.skills_cmd.urllib.request.urlopen") as mock_url:
    mock_resp = MagicMock()
    mock_resp.read.return_value = skill_content.encode("utf-8")
    mock_url.return_value.__enter__ = lambda s: mock_resp
    mock_url.return_value.__exit__ = MagicMock(return_value=False)
    installed = skills_cmd.install_skill("test-skill", url="https://example.com/SKILL.md")
report("skills.install_skill returns dict", isinstance(installed, dict))
report("skills.install_skill has name", installed.get("name") == "test-skill")
report("skills.install_skill has version", installed.get("version") == "0.1.0")

# discover after install
skills2 = skills_cmd.discover_skills()
report("skills.discover_skills after install", len(skills2) == 1)
report("skills discover has path", skills2[0].get("path") is not None)

# get_skill
skill_detail = skills_cmd.get_skill("test-skill")
report("skills.get_skill returns dict", isinstance(skill_detail, dict))
report("skills.get_skill name", skill_detail.get("name") == "test-skill")

# search_skills
search_results = skills_cmd.search_skills("test")
report("skills.search_skills finds skill", len(search_results) >= 1)

# update_skill — requires mock because it calls install_skill which conflicts with existing
with patch("void.commands.skills_cmd.install_skill", return_value={"name": "test-skill", "version": "0.1.0"}):
    updated = skills_cmd.update_skill("test-skill", repo="user/repo")
report("skills.update_skill returns dict", isinstance(updated, dict))

# uninstall_skill
uninst = skills_cmd.uninstall_skill("test-skill")
report("skills.uninstall_skill", uninst is True)
skills3 = skills_cmd.discover_skills()
report("skills empty after uninstall", len(skills3) == 0)

# ═══════════════════════════════════════════════════════════
# 18. SESSIONS — EDGE CASES
# ═══════════════════════════════════════════════════════════
print("\n═══ sessions edge cases ═══")

# get non-existent session
missing = sessions.get_session("nonexistent-id")
report("get_session nonexistent returns None", missing is None)

# delete non-existent session
del_missing = sessions.delete_session("nonexistent-id")
report("delete_session nonexistent returns False", del_missing is False)

# export non-existent session
try:
    sessions.export_session("nonexistent-id", str(TMP_VOID / "x.json"))
    report("export_session nonexistent raises", False)
except ValueError:
    report("export_session nonexistent raises ValueError", True)

# ═══════════════════════════════════════════════════════════
# 19. CLI — CONFIG SUB_COMMANDS
# ═══════════════════════════════════════════════════════════
print("\n═══ CLI config subcommands ═══")

# config show with data
buf6 = io.StringIO()
with redirect_stdout(buf6):
    cmd_config(ArgsShow())
show_out = buf6.getvalue()
report("cmd_config show prints config", len(show_out) > 0)

# config set via legacy positional
class ArgsSetPos:
    config_cmd = None
    set_key = "positional_key"
    set_value = "positional_val"
    show = False
    get_key_opt = None
cmd_config(ArgsSetPos())
cfg_pos = config.load()
report("cmd_config legacy set works", cfg_pos.get("positional_key") == "positional_val")

# ═══════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════
print("\n" + "=" * 50)
print(f"RESULTS: {passed} passed, {failed} failed")
print("=" * 50)
if errors:
    print("\nFailures:")
    for name, detail in errors:
        print(f"  - {name}: {detail}")

# Cleanup
shutil.rmtree(TMP_VOID, ignore_errors=True)

if failed > 0:
    sys.exit(1)
else:
    print("\nAll Void functionality tests passed.")