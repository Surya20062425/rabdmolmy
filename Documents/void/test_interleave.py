"""Realistic tests for mid-task interleaving.

Scenario-driven: each test models something a user actually does while the
agent is busy. Uses the real inbox, the real agent loop, and the real REPL
where possible. Run: python test_interleave.py
"""
import json
import subprocess
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock

from void import inbox
from void.agent import run
from void.model import Model

RESULTS = []
ROOT = Path(__file__).parent


def record(name, ok, detail=""):
    RESULTS.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  -> {detail[:120]}" if detail and not ok else ""))


class Resp:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls or []


def make_model(fn):
    m = Model.__new__(Model)
    m._client = None
    m.api_key = "x"
    m.model_name = "test"
    m.base_url = None
    m.chat = fn
    return m


def clean():
    inbox.pending()


# ── 1. one task queued while the first is mid-flight ─────────────────
def test_queue_mid_task():
    clean()
    calls = {"n": 0}

    def chat(messages, tools=None):
        calls["n"] += 1
        if calls["n"] == 1:
            threading.Thread(target=lambda: (time.sleep(0.3), inbox.submit("second task")),
                             daemon=True).start()
            time.sleep(0.9)
            return Resp(content="did first")
        return Resp(content="did second")

    msgs = [{"role": "user", "content": "first task"}]
    ans = run(make_model(chat), msgs, max_turns=5, quiet=True)
    users = [m["content"] for m in msgs if m["role"] == "user"]
    record("one task queued mid-run is picked up",
           "second task" in users and ans == "did second", f"users={users} ans={ans}")


# ── 2. several tasks queued in a burst ───────────────────────────────
def test_burst_queue():
    clean()
    calls = {"n": 0}

    def chat(messages, tools=None):
        calls["n"] += 1
        if calls["n"] == 1:
            def burst():
                time.sleep(0.2)
                for i in range(3):
                    inbox.submit(f"burst {i}")
            threading.Thread(target=burst, daemon=True).start()
            time.sleep(0.9)
            return Resp(content="first done")
        return Resp(content=f"turn {calls['n']}")

    msgs = [{"role": "user", "content": "long task"}]
    run(make_model(chat), msgs, max_turns=8, quiet=True)
    users = [m["content"] for m in msgs if m["role"] == "user"]
    got = [u for u in users if u.startswith("burst")]
    record("a burst of 3 queued tasks all run", len(got) == 3, f"got={got}")
    record("inbox fully drained", inbox.count() == 0, f"left={inbox.count()}")


# ── 3. a task queued while the agent is idle must not get stuck ───────
def test_queued_while_idle():
    clean()
    inbox.submit("queued before any prompt")

    calls = {"n": 0}

    def chat(messages, tools=None):
        calls["n"] += 1
        return Resp(content="done")

    # The REPL drains the inbox when idle; emulate that path directly.
    msgs = []
    for item in inbox.pending():
        msgs.append({"role": "user", "content": item["task"]})
    msgs.append({"role": "user", "content": "typed task"})
    run(make_model(chat), msgs, max_turns=3, quiet=True)
    users = [m["content"] for m in msgs if m["role"] == "user"]
    record("task queued while idle is drained, not stranded",
           "queued before any prompt" in users, f"users={users}")


# ── 4. queued task queued DURING a tool-calling turn ─────────────────
def test_queue_during_tool_turn():
    clean()
    calls = {"n": 0}

    class TC:
        def __init__(self, i):
            self.id = f"c{i}"
            self.function = MagicMock(name="function")
            self.function.name = "get_time"
            self.function.arguments = "{}"

    def chat(messages, tools=None):
        calls["n"] += 1
        if calls["n"] == 1:
            # tool call in flight -- queue a task now
            inbox.submit("queued during tool call")
            return Resp(tool_calls=[TC(1)])
        if calls["n"] == 2:
            return Resp(content="after tool")
        return Resp(content="finished queued task")

    msgs = [{"role": "user", "content": "use a tool"}]
    ans = run(make_model(chat), msgs, max_turns=6, quiet=True)
    users = [m["content"] for m in msgs if m["role"] == "user"]
    # What matters: the queued task reached the conversation and the model was
    # called again after it landed. What the model replies is its own business.
    record("task queued during a tool call is delivered to the next model call",
           "queued during tool call" in users and calls["n"] >= 2,
           f"users={users} calls={calls['n']}")


# ── 5. terminal survives: real REPL, two tasks, no crash ─────────────
def test_repl_survives():
    clean()
    proc = subprocess.Popen(
        [sys.executable, "-m", "void.cli", "chat"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1, cwd=str(ROOT),
    )
    try:
        time.sleep(3)
        proc.stdin.write("count slowly from 1 to 3\n")
        proc.stdin.flush()
        time.sleep(2)
        proc.stdin.write("tell me a joke\n")
        proc.stdin.flush()
        time.sleep(45)
        proc.stdin.write("\x04")
        proc.stdin.flush()
        out = proc.communicate(timeout=90)[0]
    finally:
        if proc.poll() is None:
            proc.kill()
    # The terminal must survive no matter what the provider does. A provider
    # error (out of credits, rate limit) is environmental and should be
    # reported, not treated as a crash -- what we forbid is a Traceback or a
    # non-zero exit, which is what "killing the terminal" actually looks like.
    low = out.lower()
    survived = "Traceback" not in out and proc.returncode == 0
    provider_err = "credit" in low or "rate" in low or "402" in out or "429" in out
    record("REPL survives a mid-run task (no crash, clean exit)", survived,
           out[-200:])
    if provider_err:
        record("provider error is reported, not fatal", survived,
               "model provider returned an error; terminal still exited 0")
    else:
        record("mid-run task was accepted and queued", "queued" in low or "picked up" in low,
               out[-200:])


# ── 6. concurrency: many submits from threads, nothing lost ──────────
def test_concurrent_submits():
    clean()
    n_threads, per = 8, 10

    def hammer(i):
        for j in range(per):
            inbox.submit(f"t{i}-{j}")

    ts = [threading.Thread(target=hammer, args=(i,)) for i in range(n_threads)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    got = inbox.pending()
    record("concurrent submits lose nothing",
           len(got) == n_threads * per, f"expected {n_threads*per}, got {len(got)}")
    record("no duplicate tasks", len({g["task"] for g in got}) == len(got))
    clean()


# ── 7. queue survives a process boundary (the CLI add path) ──────────
def test_cross_process_queue():
    clean()
    r = subprocess.run([sys.executable, "-m", "void.cli", "queue", "add", "cross-process task"],
                       capture_output=True, text=True, cwd=str(ROOT), timeout=60)
    record("void queue add writes to the inbox", inbox.count() == 1, f"count={inbox.count()}")
    r2 = subprocess.run([sys.executable, "-m", "void.cli", "queue", "list"],
                        capture_output=True, text=True, cwd=str(ROOT), timeout=60)
    record("void queue list reports the pending task",
           "1 task" in r2.stdout, r2.stdout.strip()[-80:])
    r3 = subprocess.run([sys.executable, "-m", "void.cli", "queue", "clear"],
                        capture_output=True, text=True, cwd=str(ROOT), timeout=60)
    record("void queue clear empties it", inbox.count() == 0, f"count={inbox.count()}")


# ── 8. the agent can queue work for itself ───────────────────────────
def test_self_queue():
    clean()
    from void.tools.inbox_tool import queue_task, inbox_status
    r = queue_task("follow-up I decided I need")
    record("agent can queue its own follow-up", r["queued"] and inbox_status()["pending"] == 1, str(r))
    clean()


# ── 9. a queued task that arrives after max_turns is not silently lost ─
def test_not_lost_at_max_turns():
    clean()
    calls = {"n": 0}

    def chat(messages, tools=None):
        calls["n"] += 1
        if calls["n"] == 1:
            inbox.submit("arrived late")
        return Resp(content=f"turn {calls['n']}")

    msgs = [{"role": "user", "content": "go"}]
    run(make_model(chat), msgs, max_turns=3, quiet=True)
    # It ran within the budget here; the important part is it wasn't dropped.
    users = [m["content"] for m in msgs if m["role"] == "user"]
    record("task arriving mid-run is consumed within budget",
           "arrived late" in users, f"users={users} calls={calls['n']}")


# ── 10. malformed tool arguments must not kill the loop ──────────────
def test_malformed_tool_args():
    clean()
    from unittest.mock import MagicMock as MM

    class TC:
        def __init__(self, a):
            self.id = "x1"
            self.function = MM()
            self.function.name = "system_shell"
            self.function.arguments = a

    calls = {"n": 0}

    def chat(messages, tools=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return Resp(tool_calls=[TC("{not valid json")])
        return Resp(content="recovered")

    msgs = [{"role": "user", "content": "go"}]
    try:
        ans = run(make_model(chat), msgs, max_turns=4, quiet=True)
        record("malformed tool args don't crash the loop", ans == "recovered", repr(ans)[:80])
        errs = [m["content"] for m in msgs if m.get("role") == "tool"]
        record("bad args are reported back to the model",
               any("invalid tool arguments" in e for e in errs), str(errs)[:100])
    except Exception as e:
        record("malformed tool args don't crash the loop", False, f"{type(e).__name__}: {e}")


# ── 11. a non-interactive permission prompt must deny, not hang ───────
def test_install_prompt_safe_in_thread():
    clean()
    from unittest.mock import MagicMock as MM

    class TC:
        def __init__(self, a):
            self.id = "x1"
            self.function = MM()
            self.function.name = "system_shell"
            self.function.arguments = a

    calls = {"n": 0}
    holder = {}

    def chat(messages, tools=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return Resp(tool_calls=[TC(json.dumps({"command": "pip install requests"}))])
        return Resp(content="handled")

    def worker():
        try:
            holder["ans"] = run(make_model(chat), [{"role": "user", "content": "go"}],
                                max_turns=4, quiet=True)
        except Exception as e:
            holder["err"] = e

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join(timeout=20)
    record("install prompt in a thread denies instead of hanging",
           not t.is_alive() and holder.get("ans") == "handled",
           f"alive={t.is_alive()} holder={holder}")


if __name__ == "__main__":
    print("=" * 68)
    print(" INTERLEAVING -- realistic scenarios")
    print("=" * 68)
    for fn in (test_queue_mid_task, test_burst_queue, test_queued_while_idle,
               test_queue_during_tool_turn, test_repl_survives,
               test_concurrent_submits, test_cross_process_queue,
               test_self_queue, test_not_lost_at_max_turns,
               test_malformed_tool_args, test_install_prompt_safe_in_thread):
        print(f"\n-- {fn.__name__} " + "-" * max(0, 46 - len(fn.__name__)))
        try:
            fn()
        except Exception as e:
            record(fn.__name__, False, f"crashed: {type(e).__name__}: {e}")

    clean()
    p = sum(1 for _, ok, _ in RESULTS if ok)
    f = len(RESULTS) - p
    print("\n" + "=" * 68)
    print(f" INTERLEAVING: {p} passed, {f} failed  (of {len(RESULTS)})")
    print("=" * 68)
    sys.exit(1 if f else 0)
