"""Test the paths no suite covered: log_event, run_hooks, run_moa, cron daemon.

Run: python test_untested.py
"""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RESULTS = []


def record(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  -> {detail[:110]}" if detail and not ok else ""))


def test_log_event():
    from void.commands.system_cmd import log_event, _log_path
    p = _log_path()
    before = p.read_text(encoding="utf-8").count("\n") if p.exists() else 0
    log_event("test", "untested-path probe")
    after = p.read_text(encoding="utf-8")
    ok = "untested-path probe" in after and after.count("\n") > before
    record("log_event appends a line to void.log", ok, after[-80:] if not ok else "")


def test_agent_logs_tool_calls():
    """The agent loop calls _log on every tool dispatch -- verify it reaches disk."""
    from void.agent import _log
    from void.commands.system_cmd import _log_path
    _log("tool", "probe-from-agent")
    txt = _log_path().read_text(encoding="utf-8")
    record("agent _log writes tool events", "probe-from-agent" in txt)


def test_run_hooks():
    from void.commands.system_cmd import cmd_hooks, run_hooks, _store, _save_store
    import argparse

    # isolate: snapshot + restore the hook store
    data = _store("hooks", {"hooks": []})
    original = [dict(h) for h in data.get("hooks", [])]

    out = Path(tempfile.gettempdir()) / "void_hook_probe.txt"
    out.unlink(missing_ok=True)

    try:
        cmd_hooks(argparse.Namespace(hooks_subcommand="add", event="pre_tool",
                                     cmd=f'echo hook-fired > "{out}"', id=None))
        run_hooks("pre_tool", "payload")
        fired = out.exists() and "hook-fired" in out.read_text()
        record("run_hooks fires a registered shell hook", fired)

        # a different event must NOT fire
        out.unlink(missing_ok=True)
        run_hooks("post_tool", "payload")
        record("run_hooks ignores other events", not out.exists())

        # a broken hook command must not raise
        _save_store("hooks", {"hooks": [{"id": "1", "event": "pre_chat", "cmd": "definitely-not-a-real-cmd-xyz"}]})
        try:
            run_hooks("pre_chat", "")
            record("run_hooks survives a failing command", True)
        except Exception as e:
            record("run_hooks survives a failing command", False, f"{type(e).__name__}: {e}")
    finally:
        _save_store("hooks", {"hooks": original})
        out.unlink(missing_ok=True)


def test_run_moa():
    from void.commands.system_cmd import run_moa, _store, _save_store

    data = _store("moa", {"slots": [], "voters": 1})
    original = list(data.get("slots", []))

    try:
        _save_store("moa", {"slots": [], "voters": 1})
        r = run_moa([{"role": "user", "content": "hi"}])
        record("run_moa returns None when unconfigured", r is None, repr(r))

        # a slot pointing at a nonexistent provider must be skipped, not crash
        _save_store("moa", {"slots": ["nope/not-a-model"], "voters": 1})
        try:
            r2 = run_moa([{"role": "user", "content": "hi"}])
            record("run_moa survives an unreachable slot", r2 is None or isinstance(r2, str), repr(r2)[:80])
        except Exception as e:
            record("run_moa survives an unreachable slot", False, f"{type(e).__name__}: {e}")
    finally:
        _save_store("moa", {"slots": original, "voters": data.get("voters", 1)})


def test_cron_daemon():
    """The daemon loop: start it, let it fire a due job, kill it.

    Isolates itself: pauses every other job first so the daemon doesn't spend
    its first polls on leftovers from earlier tests, then restores them.
    Polls the DB instead of sleeping a fixed time -- the agent call inside the
    job can take a while.
    """
    from void.commands.cron_cmd import (
        _conn, create_job, get_job, delete_job, list_jobs, pause_job, resume_job,
    )

    others = [j["id"] for j in list_jobs() if j["status"] == "active"]
    for jid in others:
        pause_job(jid)

    job = create_job("30m", "Reply with exactly: daemon-ok")
    conn = _conn()
    try:
        conn.execute("UPDATE cron_jobs SET next_run = ? WHERE id = ?",
                     ("2020-01-01T00:00:00+00:00", job["id"]))
        conn.commit()
    finally:
        conn.close()

    # stdout -> file, not PIPE: the daemon prints a spinner continuously and a
    # full pipe buffer would block the child before it finishes the job.
    log = Path(tempfile.gettempdir()) / "void_daemon_test.log"
    with log.open("w", encoding="utf-8", errors="replace") as fh:
        proc = subprocess.Popen(
            [sys.executable, "-m", "void.cli", "cron", "daemon", "--interval", "5"],
            stdout=fh, stderr=subprocess.STDOUT,
            cwd=str(Path(__file__).parent),
        )
        try:
            deadline = time.time() + 150
            runs = 0
            while time.time() < deadline:
                time.sleep(3)
                runs = (get_job(job["id"]) or {}).get("runs", 0)
                if runs >= 1:
                    break

            j = get_job(job["id"]) or {}
            record("cron daemon starts and fires due jobs", runs >= 1, f"runs={runs}")
            record("cron daemon stores the job result", bool(j.get("last_result")),
                   repr(j.get("last_result"))[:100])
            record("cron daemon reschedules after firing", bool(j.get("next_run")),
                   repr(j.get("next_run"))[:60])
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            delete_job(job["id"])
            for jid in others:
                resume_job(jid)


if __name__ == "__main__":
    print("=" * 66)
    print(" UNTESTED PATHS")
    print("=" * 66)
    for fn in (test_log_event, test_agent_logs_tool_calls, test_run_hooks,
               test_run_moa, test_cron_daemon):
        print(f"\n-- {fn.__name__} " + "-" * (48 - len(fn.__name__)))
        try:
            fn()
        except Exception as e:
            record(fn.__name__, False, f"crashed: {type(e).__name__}: {e}")

    p = sum(1 for _, ok, _ in RESULTS if ok)
    f = len(RESULTS) - p
    print("\n" + "=" * 66)
    print(f" UNTESTED PATHS: {p} passed, {f} failed  (of {len(RESULTS)})")
    print("=" * 66)
    sys.exit(1 if f else 0)
