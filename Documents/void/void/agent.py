"""Agent loop — call model, dispatch tools, round-trip until text."""

import json
import threading
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from void.model import Model
from void.theme import thinking, spinner_frame, gb, g, gd
from void.tools.registry import get_schemas, dispatch
from void.commands.skills_cmd import discover_skills
from void.skills_catalog import match_skills, SKILLS as CATALOG


def _is_install_command(command: str) -> bool:
    """Check if a shell command is an install operation."""
    install_patterns = [
        "pip install", "pip3 install", "npm install", "yarn add",
        "apt install", "apt-get install", "brew install", "choco install",
        "gem install", "cargo install", "go install", "docker pull",
    ]
    cmd_lower = command.lower().strip()
    return any(p in cmd_lower for p in install_patterns)


def _ask_permission(prompt: str) -> bool:
    """Ask user for permission. Returns True if allowed."""
    try:
        answer = input(f"\n  {prompt}\n  Allow? (y/N): ").strip().lower()
        return answer == "y"
    except (EOFError, KeyboardInterrupt):
        return False


def run(model: Model, messages: list[dict], max_turns: int = 20) -> str:
    """Run the agent loop.

    1. Call model with messages + available tool schemas.
    2. If tool_calls → dispatch each, append tool results, continue.
    3. If text → return it.
    4. Bail after max_turns.
    """
    tools = get_schemas()
    # Inject installed skills as system context
    _inject_skills(messages)
    print(thinking(), end="\r", flush=True)
    result = None
    _done = threading.Event()

    def _spin():
        i = 0
        while not _done.is_set():
            print(spinner_frame(i), end="\r", flush=True)
            i += 1
            _done.wait(0.1)

    t = threading.Thread(target=_spin, daemon=True)
    t.start()
    try:
        for _ in range(max_turns):
            resp = model.chat(messages, tools=tools if tools else None)
            if resp.tool_calls:
                assistant_msg = {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in resp.tool_calls
                    ],
                }
                messages.append(assistant_msg)
                for tc in resp.tool_calls:
                    name = tc.function.name
                    args = json.loads(tc.function.arguments)
                    if name == "system_shell" and _is_install_command(args.get("command", "")):
                        _done.clear()  # pause spinner so input() is readable
                        allowed = _ask_permission(f"Install command: {args['command']}")
                        _done.set()    # resume spinner
                        if not allowed:
                            result = '{"error": "permission denied by user"}'
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc.id,
                                "content": result,
                            })
                            continue
                    _done.clear()
                    result = dispatch(name, args)
                    _done.set()
                    _log("tool", f"{name} -> {result[:200]}")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })
            else:
                result = resp.content or ""
                break
        else:
            result = "max turns reached — no final answer"
    except Exception as e:
        _log("error", f"agent loop: {e}")
        raise
    finally:
        _done.set()
        t.join()
        print(" " * 40, end="\r", flush=True)
    return result


def _log(kind: str, message: str) -> None:
    """Append to ~/.void/void.log (best effort, never fatal)."""
    try:
        from void.commands.system_cmd import log_event
        log_event(kind, message)
    except Exception:
        pass


def _inject_skills(messages: list[dict]) -> None:
    """Prepend contextually-relevant skills as system context.

    Only skills that match the user's message are injected — dumping the whole
    library would blow the context window. Sources: catalog trigger matches,
    then vendored skills whose name the message mentions.
    """
    from void.skills_catalog import load_skill_content, VOID_SKILLS_DIR

    if not messages:
        return
    last = messages[-1].get("content", "").lower()
    if not last:
        return

    parts = []
    seen = set()

    # 1. Vendored skills named directly in the message — most relevant, first,
    #    so they survive the size cap below.
    if VOID_SKILLS_DIR.exists():
        for d in VOID_SKILLS_DIR.iterdir():
            if not d.is_dir() or len(d.name) < 4:
                continue
            if d.name.replace("-", " ") in last or d.name in last:
                md = d / "SKILL.md"
                if not md.exists():
                    continue
                try:
                    parts.append(f"Skill: {d.name}\n{md.read_text(encoding='utf-8')}")
                    seen.add(d.name)
                except OSError:
                    continue

    # 2. Catalog skills matching a trigger
    for name, info in CATALOG.items():
        if name in seen or not _matches(last, info["trigger"]):
            continue
        content = load_skill_content(name)
        parts.append(f"Skill: {name}\n{content}" if content else f"Skill: {name}\n{info['description']}")
        seen.add(name)

    if not parts:
        return
    # ponytail: cap total injected skill text so one huge SKILL.md can't blow
    # the context window. Raise if you routinely need several large skills at once.
    MAX_SKILL_CHARS = 60000
    system_text = "\n\n---\n\n".join(parts)[:MAX_SKILL_CHARS]
    inserted = False
    for i, m in enumerate(messages):
        if m.get("role") == "system":
            messages[i] = {"role": "system", "content": m.get("content", "") + "\n\n" + system_text}
            inserted = True
            break
    if not inserted:
        messages.insert(0, {"role": "system", "content": system_text})


def _matches(text: str, trigger: str) -> bool:
    """True if a distinctive trigger word appears in the text."""
    stop = {
        "the", "a", "an", "and", "or", "to", "for", "of", "in", "on", "my", "me", "it", "is",
        "search", "write", "make", "create", "build", "add", "get", "set", "use", "code",
        "file", "files", "text", "data", "full", "all", "new", "with", "from", "into",
    }
    words = [w.strip(".,!?:;") for w in trigger.lower().replace(",", " ").split()]
    return any(len(w) > 3 and w not in stop and w in text for w in words)


def demo() -> None:
    """Self-check: mock the model, exercise the full tool-calling loop."""
    mock = MagicMock()
    # Model asks for get_time, then answers
    mock.chat.side_effect = [
        type("Resp", (), {
            "content": None,
            "tool_calls": [MagicMock(id="call_1", function=MagicMock(
                name="get_time", arguments='{"tz": "UTC"}'))],
        })(),
        type("Resp", (), {
            "content": "The current UTC time is 2026-09-30T17:12:31+00:00.",
            "tool_calls": [],
        })(),
    ]
    model = Model.__new__(Model)
    model._client = None
    model.chat = mock.chat

    messages = [{"role": "user", "content": "what time is it?"}]
    answer = run(model, messages)
    assert "2026-09-30" in answer, f"expected timestamp in answer, got: {answer}"
    assert mock.chat.call_count == 2
    assert any(
        m.get("role") == "tool" and "get_time" in m.get("content", "")
        for m in messages
    ), "tool result not appended to messages"
    print("demo OK:", answer)


if __name__ == "__main__":
    demo()