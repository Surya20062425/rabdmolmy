"""Agent loop — call model, dispatch tools, round-trip until text."""

import json
from unittest.mock import MagicMock, patch
from void.model import Model
from void.tools.registry import get_schemas, dispatch
from void.commands.skills_cmd import discover_skills


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
    import sys
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
    for _ in range(max_turns):
        resp = model.chat(messages, tools=tools if tools else None)
        if resp.tool_calls:
            # OpenAI requires the assistant tool_calls message BEFORE any tool result.
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
                # Ask permission for install commands
                if name == "system_shell" and _is_install_command(args.get("command", "")):
                    if not _ask_permission(f"Install command: {args['command']}"):
                        result = '{"error": "permission denied by user"}'
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": result,
                        })
                        continue
                result = dispatch(name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
        else:
            return resp.content or ""
    return "max turns reached — no final answer"


def _inject_skills(messages: list[dict]) -> None:
    """Prepend installed skills as system context to the message list."""
    skills = discover_skills()
    if not skills:
        return
    parts = []
    for s in skills:
        path = s.get("path")
        if not path:
            continue
        from pathlib import Path
        try:
            content = Path(path).read_text(encoding="utf-8")
        except Exception:
            continue
        parts.append(f"Skill: {s['name']}\\n{content}")
    if not parts:
        return
    system_text = "\\n\\n---\\n\\n".join(parts)
    # Insert after the system message or at the front
    inserted = False
    for i, m in enumerate(messages):
        if m.get("role") == "system":
            messages[i] = {"role": "system", "content": m.get("content", "") + "\\n\\n" + system_text}
            inserted = True
            break
    if not inserted:
        messages.insert(0, {"role": "system", "content": system_text})


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
