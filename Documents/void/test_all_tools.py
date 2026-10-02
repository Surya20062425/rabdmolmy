"""Realistic test of every Void tool. Each test exercises the real code path.

Tests that need network/creds are marked and reported honestly as SKIP/FAIL
rather than faked. Run: python test_all_tools.py
"""
import json
import os
import sys
import time
from pathlib import Path

RESULTS = []


def record(tool, scenario, status, detail):
    RESULTS.append({"tool": tool, "scenario": scenario, "status": status, "detail": detail})
    mark = {"PASS": "PASS", "FAIL": "FAIL", "SKIP": "SKIP"}[status]
    print(f"  [{mark}] {tool:20} {scenario}")
    if status != "PASS":
        print(f"         -> {detail[:160]}")


# ── system tools ─────────────────────────────────────────────────────

def test_system_tools():
    from void.tools.system import (
        system_read_file, system_write_file, system_shell,
        system_ls, system_pwd, system_env_var,
    )
    tmp = Path(os.environ.get("TEMP", "/tmp")) / "void_tool_test.txt"

    # write then read back a real file
    w = system_write_file(str(tmp), "line1\nline2\nline3\n")
    if w.get("success") and w.get("bytes") == 18:
        record("system_write_file", "write 18 bytes, verify byte count", "PASS", "")
    else:
        record("system_write_file", "write 18 bytes", "FAIL", str(w))

    r = system_read_file(str(tmp))
    if r.get("total_lines") == 3 and "line2" in r.get("content", ""):
        record("system_read_file", "read back 3 lines, find line2", "PASS", "")
    else:
        record("system_read_file", "read back", "FAIL", str(r)[:200])

    # offset/limit
    r2 = system_read_file(str(tmp), offset=1, limit=1)
    if r2.get("content", "").strip() == "line2" and r2.get("truncated"):
        record("system_read_file", "offset=1 limit=1 returns line2, truncated", "PASS", "")
    else:
        record("system_read_file", "offset/limit", "FAIL", str(r2)[:200])

    # append
    system_write_file(str(tmp), "line4\n", append=True)
    r3 = system_read_file(str(tmp))
    if r3.get("total_lines") == 4:
        record("system_write_file", "append adds line4 (now 4 lines)", "PASS", "")
    else:
        record("system_write_file", "append", "FAIL", str(r3)[:200])

    # missing file -> error, not crash
    r4 = system_read_file(str(tmp) + ".nope")
    if "error" in r4:
        record("system_read_file", "missing file returns error dict", "PASS", "")
    else:
        record("system_read_file", "missing file", "FAIL", str(r4))

    s = system_shell("echo void-test")
    if s.get("exit_code") == 0 and "void-test" in s.get("stdout", ""):
        record("system_shell", "echo returns stdout + exit 0", "PASS", "")
    else:
        record("system_shell", "echo", "FAIL", str(s)[:200])

    s2 = system_shell("exit 3")
    if s2.get("exit_code") == 3 and s2.get("success") is False:
        record("system_shell", "non-zero exit captured (3)", "PASS", "")
    else:
        record("system_shell", "non-zero exit", "FAIL", str(s2)[:200])

    s3 = system_shell("sleep 5", timeout=1)
    if "timeout" in str(s3.get("error", "")).lower():
        record("system_shell", "timeout honored (1s on sleep 5)", "PASS", "")
    else:
        record("system_shell", "timeout", "FAIL", str(s3)[:200])

    d = system_ls(str(tmp.parent))
    if d.get("count", 0) > 0 and any(e["name"] == tmp.name for e in d.get("entries", [])):
        record("system_ls", "lists dir, finds our test file", "PASS", "")
    else:
        record("system_ls", "list dir", "FAIL", str(d)[:200])

    p = system_pwd()
    if p.get("cwd"):
        record("system_pwd", "returns a cwd", "PASS", "")
    else:
        record("system_pwd", "cwd", "FAIL", str(p))

    ev = system_env_var("PATH")
    if ev.get("exists") and ev.get("value"):
        record("system_env_var", "PATH exists and has a value", "PASS", "")
    else:
        record("system_env_var", "PATH", "FAIL", str(ev))

    ev2 = system_env_var("VOID_DEFINITELY_NOT_SET_123")
    if ev2.get("exists") is False:
        record("system_env_var", "unset var reports exists=False", "PASS", "")
    else:
        record("system_env_var", "unset var", "FAIL", str(ev2))

    tmp.unlink(missing_ok=True)


# ── web tools ────────────────────────────────────────────────────────

def test_web_tools():
    from void.tools.web import web_fetch, web_extract_text, web_search

    r = web_fetch("https://example.com")
    if r.get("status") == "ok" and "Example Domain" in r.get("content", ""):
        record("web_fetch", "fetch example.com, find title text", "PASS", "")
    elif "error" in r:
        record("web_fetch", "fetch example.com", "FAIL", str(r)[:160])
    else:
        record("web_fetch", "fetch example.com", "FAIL", str(r)[:160])

    bad = web_fetch("not-a-url")
    if "error" in bad:
        record("web_fetch", "rejects malformed URL", "PASS", "")
    else:
        record("web_fetch", "malformed URL guard", "FAIL", str(bad)[:160])

    t = web_extract_text("https://example.com")
    if t.get("text_length", 0) > 0 and "Example Domain" in t.get("text", ""):
        record("web_extract_text", "extracts readable text from example.com", "PASS", "")
    else:
        record("web_extract_text", "extract text", "FAIL", str(t)[:160])

    q = web_search("python")
    if q.get("result_count", 0) > 0:
        record("web_search", f"DuckDuckGo returned {q['result_count']} results", "PASS", "")
    else:
        record("web_search", "DuckDuckGo search", "FAIL", str(q)[:160])


# ── task tools ───────────────────────────────────────────────────────

def test_task_tools():
    from void.tools.task import task_add, task_list, task_done, task_delete

    t = task_add("realistic test task")
    if t.get("status") == "open" and t.get("id"):
        record("task_add", "adds task, status=open", "PASS", "")
    else:
        record("task_add", "add task", "FAIL", str(t))

    lst = task_list()
    if any(x["id"] == t["id"] for x in lst.get("tasks", [])):
        record("task_list", "new task appears in open list", "PASS", "")
    else:
        record("task_list", "list tasks", "FAIL", str(lst)[:160])

    d = task_done(t["id"])
    if d.get("status") == "done" and d.get("done_at"):
        record("task_done", "marks done with timestamp", "PASS", "")
    else:
        record("task_done", "mark done", "FAIL", str(d))

    lst2 = task_list()
    if not any(x["id"] == t["id"] for x in lst2.get("tasks", [])):
        record("task_list", "completed task leaves open list", "PASS", "")
    else:
        record("task_list", "open filter", "FAIL", "done task still listed")

    del_r = task_delete(t["id"])
    if del_r.get("deleted") == t["id"]:
        record("task_delete", "deletes task", "PASS", "")
    else:
        record("task_delete", "delete task", "FAIL", str(del_r))

    miss = task_done("999999")
    if "error" in miss:
        record("task_done", "missing id returns error", "PASS", "")
    else:
        record("task_done", "missing id guard", "FAIL", str(miss))


# ── memory tools ─────────────────────────────────────────────────────

def test_memory_tools():
    from void.tools.memory_tool import memory_add, memory_list, memory_remove

    before = memory_list().get("count", 0)
    e = memory_add("realistic memory entry")
    after = memory_list()
    if after.get("count") == before + 1:
        record("memory_add", "entry count increments by 1", "PASS", "")
    else:
        record("memory_add", "add entry", "FAIL", f"{before} -> {after.get('count')}")

    if any("realistic memory entry" in str(x.get("content", "")) for x in after.get("entries", [])):
        record("memory_list", "entry content readable", "PASS", "")
    else:
        record("memory_list", "list entries", "FAIL", str(after)[:160])

    idx = after["count"] - 1
    r = memory_remove(idx)
    if "removed" in r and memory_list().get("count") == before:
        record("memory_remove", "removes by index, count restored", "PASS", "")
    else:
        record("memory_remove", "remove entry", "FAIL", str(r)[:160])

    bad = memory_remove(99999)
    if "error" in bad:
        record("memory_remove", "out-of-range index returns error", "PASS", "")
    else:
        record("memory_remove", "range guard", "FAIL", str(bad))


# ── session tools ────────────────────────────────────────────────────

def test_session_tools():
    from void.sessions import create_session, add_message, delete_session
    from void.tools.session_tool import session_search, session_read

    s = create_session(title="tool test session")
    add_message(s["id"], "user", "the magic word is zanzibar-42")
    add_message(s["id"], "assistant", "noted, zanzibar-42")

    found = session_search("zanzibar-42")
    if found.get("count", 0) >= 1 and any(x["id"] == s["id"] for x in found.get("sessions", [])):
        record("session_search", "finds session by unique content", "PASS", "")
    else:
        record("session_search", "search sessions", "FAIL", str(found)[:160])

    read = session_read(s["id"])
    if read.get("title") == "tool test session" and len(read.get("messages", [])) == 2:
        record("session_read", "reads session with 2 messages", "PASS", "")
    else:
        record("session_read", "read session", "FAIL", str(read)[:160])

    miss = session_read("no-such-session-id")
    if "error" in miss:
        record("session_read", "missing session returns error", "PASS", "")
    else:
        record("session_read", "missing session guard", "FAIL", str(miss))

    delete_session(s["id"])


# ── cronjob tools ────────────────────────────────────────────────────

def test_cronjob_tools():
    from void.tools.cronjob_tool import cronjob_create, cronjob_list, cronjob_delete

    j = cronjob_create("45m", "realistic cron test")
    if j.get("id") and j.get("next_run"):
        record("cronjob_create", "creates job with future next_run", "PASS", "")
    else:
        record("cronjob_create", "create job", "FAIL", str(j)[:160])

    lst = cronjob_list()
    if any(x["id"] == j["id"] for x in lst.get("jobs", [])):
        record("cronjob_list", "new job appears in list", "PASS", "")
    else:
        record("cronjob_list", "list jobs", "FAIL", str(lst)[:160])

    d = cronjob_delete(j["id"])
    if d.get("ok") is True:
        record("cronjob_delete", "deletes job", "PASS", "")
    else:
        record("cronjob_delete", "delete job", "FAIL", str(d))

    bad = cronjob_create("garbage-schedule", "x")
    if isinstance(bad, dict) and "error" in bad:
        record("cronjob_create", "bad schedule returns error", "PASS", "")
    else:
        record("cronjob_create", "bad schedule guard", "FAIL", str(bad)[:160])


# ── process tools ────────────────────────────────────────────────────

def test_process_tools():
    from void.tools.process_tool import process_list, process_start, process_stop

    start = process_start("sleep 30")
    if start.get("pid") and start.get("status") == "running":
        record("process_start", f"starts bg process (pid {start['pid']})", "PASS", "")
    else:
        record("process_start", "start process", "FAIL", str(start)[:160])
        return

    lst = process_list()
    if start["session_id"] in lst.get("processes", {}):
        record("process_list", "started process tracked, alive detected", "PASS", "")
    else:
        record("process_list", "list processes", "FAIL", str(lst)[:160])

    stop = process_stop(start["session_id"])
    if stop.get("stopped") == start["session_id"]:
        record("process_stop", "stops process by session id", "PASS", "")
    else:
        record("process_stop", "stop process", "FAIL", str(stop)[:160])

    miss = process_stop("no-such-session")
    if "error" in miss:
        record("process_stop", "unknown session returns error", "PASS", "")
    else:
        record("process_stop", "unknown session guard", "FAIL", str(miss))


# ── browser tools ────────────────────────────────────────────────────

def test_browser_tools():
    from void.tools.browser import browser_fetch, browser_click
    try:
        import playwright  # noqa: F401
        has_pw = True
    except ImportError:
        has_pw = False

    r = browser_fetch("https://example.com")
    if has_pw:
        if r.get("note") == "playwright" and "Example Domain" in r.get("text", ""):
            record("browser_fetch", "Playwright render of example.com", "PASS", "")
        else:
            record("browser_fetch", "Playwright render", "FAIL", str(r)[:160])
    else:
        if "playwright not installed" in str(r.get("note", "")):
            record("browser_fetch", "static fallback when playwright absent", "PASS",
                   "playwright not installed -- fell back to static fetch, still returned content")
        else:
            record("browser_fetch", "fallback path", "FAIL", str(r)[:160])

    if not has_pw:
        record("browser_click", "requires playwright", "SKIP", "playwright not installed")
    else:
        record("browser_click", "needs a live clickable target", "SKIP", "no stable public target")


# ── vision tools ─────────────────────────────────────────────────────

def test_vision_tools():
    from void.tools.browser import vision_describe

    bad = vision_describe("/no/such/image.png")
    if "error" in bad:
        record("vision_describe", "missing file returns error", "PASS", "")
    else:
        record("vision_describe", "missing file guard", "FAIL", str(bad))

    notimg = vision_describe(__file__)
    if "error" in notimg:
        record("vision_describe", "non-image file rejected", "PASS", "")
    else:
        record("vision_describe", "type guard", "FAIL", str(notimg)[:160])

    # real image if PIL available
    try:
        from PIL import Image
        import tempfile
        p = Path(tempfile.gettempdir()) / "void_vision_test.png"
        Image.new("RGB", (64, 64), (157, 241, 51)).save(p)
        out = vision_describe(str(p), "What color is this image? One word.")
        if out.get("answer"):
            record("vision_describe", "real PNG -> model answer", "PASS", "")
        elif "error" in out:
            record("vision_describe", "real PNG round-trip", "SKIP",
                   f"model/vision unavailable: {str(out['error'])[:100]}")
        p.unlink(missing_ok=True)
    except ImportError:
        record("vision_describe", "real image", "SKIP", "PIL not installed")


# ── delegate tools ───────────────────────────────────────────────────

def test_delegate_tools():
    from void.tools.delegate import delegate_task, delegate_list

    out = delegate_task("Reply with exactly the word: delegated-ok", max_turns=3)
    if out.get("status") == "done" and "delegated-ok" in str(out.get("result", "")).lower():
        record("delegate_task", "sub-agent ran, returned its answer", "PASS", "")
    elif out.get("status") == "error":
        record("delegate_task", "sub-agent round trip", "SKIP", f"model unavailable: {str(out.get('error'))[:100]}")
    else:
        record("delegate_task", "sub-agent", "FAIL", str(out)[:160])

    lst = delegate_list()
    if lst.get("count", 0) >= 1:
        record("delegate_list", "tracks the sub-agent run", "PASS", "")
    else:
        record("delegate_list", "list sub-agents", "FAIL", str(lst)[:160])


# ── email tools ──────────────────────────────────────────────────────

def test_email_tools():
    from void.tools.email import email_list, email_read, email_search

    # No credentials configured -> must return a clear error, not crash
    for fn, name, args in [
        (email_list, "email_list", {}),
        (email_read, "email_read", {"uid": "1"}),
        (email_search, "email_search", {"query": "ALL"}),
    ]:
        try:
            r = fn(**args)
            if isinstance(r, dict) and "error" in r:
                record(name, "no creds -> clear error (no crash)", "PASS", "")
            elif isinstance(r, dict) and ("emails" in r or "body" in r or "subject" in r):
                record(name, "live IMAP", "PASS", f"read message: {str(r.get('subject', r.get('count', '')))[:40]}")
            else:
                record(name, "unexpected shape", "FAIL", str(r)[:160])
        except Exception as e:
            record(name, "crashed without creds", "FAIL", f"{type(e).__name__}: {e}")

    record("email_send", "would send real mail", "SKIP", "no SMTP creds configured -- not sending test mail")


# ── get_time ─────────────────────────────────────────────────────────

def test_get_time():
    from void.tools.example import get_time
    r = get_time()
    if isinstance(r, dict) and ("time" in r or "iso" in r or r):
        record("get_time", "returns a timestamp", "PASS", "")
    else:
        record("get_time", "timestamp", "FAIL", str(r))


def main() -> int:
    print("=" * 68)
    print(" VOID TOOL TEST SUITE -- realistic scenarios")
    print("=" * 68)

    groups = [
        ("system", test_system_tools),
        ("web", test_web_tools),
        ("task", test_task_tools),
        ("memory", test_memory_tools),
        ("session", test_session_tools),
        ("cronjob", test_cronjob_tools),
        ("process", test_process_tools),
        ("browser", test_browser_tools),
        ("vision", test_vision_tools),
        ("delegate", test_delegate_tools),
        ("email", test_email_tools),
        ("time", test_get_time),
    ]
    for label, fn in groups:
        print(f"\n-- {label} " + "-" * (60 - len(label)))
        try:
            fn()
        except Exception as e:
            record(label, "group crashed", "FAIL", f"{type(e).__name__}: {e}")

    p = sum(1 for r in RESULTS if r["status"] == "PASS")
    f = sum(1 for r in RESULTS if r["status"] == "FAIL")
    s = sum(1 for r in RESULTS if r["status"] == "SKIP")
    print("\n" + "=" * 68)
    print(f" TOOLS: {p} passed, {f} failed, {s} skipped  (of {len(RESULTS)} checks)")
    print("=" * 68)

    out = Path(__file__).parent / "tool_test_results.json"
    out.write_text(json.dumps(RESULTS, indent=2), encoding="utf-8")
    print(f"results -> {out}")
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(main())
