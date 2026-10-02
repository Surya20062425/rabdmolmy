"""Delegation tools -- spawn isolated sub-agents.

Runs a separate agent loop with its own message list so intermediate tool
output doesn't pollute the parent's context. Returns only the final answer.
"""

import json
import threading

from void.tools.registry import register

_results: dict[str, dict] = {}


def _run_subagent(task_id: str, goal: str, context: str, max_turns: int) -> None:
    """Run one sub-agent to completion and stash its answer."""
    try:
        from void.cli import build_model
        from void.agent import run as agent_run
        import argparse

        model = build_model(argparse.Namespace(api_key=None, base_url=None, model=None))
        prompt = goal if not context else f"{goal}\n\nContext:\n{context}"
        answer = agent_run(model, [{"role": "user", "content": prompt}], max_turns=max_turns)
        _results[task_id] = {"status": "done", "result": answer}
    except Exception as e:
        _results[task_id] = {"status": "error", "error": str(e)}


def delegate_task(goal: str, context: str = "", max_turns: int = 10) -> dict:
    """Run a sub-agent in an isolated context. Returns its final answer.

    Synchronous: blocks until the child finishes, because the parent needs the
    result to continue.
    """
    import uuid
    task_id = str(uuid.uuid4())[:8]
    _results[task_id] = {"status": "running"}
    t = threading.Thread(target=_run_subagent, args=(task_id, goal, context, max_turns), daemon=True)
    t.start()
    t.join(timeout=300)
    if t.is_alive():
        return {"task_id": task_id, "status": "timeout", "error": "sub-agent exceeded 300s"}
    return {"task_id": task_id, **_results.get(task_id, {})}


def delegate_list() -> dict:
    """List sub-agent runs from this process."""
    return {"count": len(_results), "tasks": _results}


register(
    "delegate_task",
    {
        "name": "delegate_task",
        "description": "Spawn a sub-agent with its own isolated context to do a reasoning-heavy subtask; returns only its final answer.",
        "parameters": {
            "type": "object",
            "properties": {
                "goal": {"type": "string", "description": "What the sub-agent must accomplish"},
                "context": {"type": "string", "description": "Background the sub-agent needs (it knows nothing of this conversation)"},
                "max_turns": {"type": "integer", "default": 10},
            },
            "required": ["goal"],
        },
    },
    delegate_task,
)
register(
    "delegate_list",
    {
        "name": "delegate_list",
        "description": "List sub-agent runs started in this process.",
        "parameters": {"type": "object", "properties": {}},
    },
    delegate_list,
)


if __name__ == "__main__":
    from void.tools.registry import list_tools
    assert "delegate_task" in list_tools()
    assert "delegate_list" in list_tools()
    print("delegate tools OK")
