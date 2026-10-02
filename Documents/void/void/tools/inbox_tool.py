"""Task inbox tool -- let the agent queue follow-up work for itself.

The loop drains the inbox between turns, so a queued task runs as soon as the
current one finishes.
"""

from void import inbox
from void.tools.registry import register


def queue_task(task: str) -> dict:
    """Queue a task for the agent to pick up when it finishes the current one."""
    inbox.submit(task, source="agent")
    return {"queued": task, "pending": inbox.count()}


def inbox_status() -> dict:
    """How many tasks are waiting in the inbox."""
    return {"pending": inbox.count()}


register(
    "queue_task",
    {
        "name": "queue_task",
        "description": "Queue a follow-up task for yourself; it runs after the current task finishes.",
        "parameters": {
            "type": "object",
            "properties": {"task": {"type": "string", "description": "The task to queue"}},
            "required": ["task"],
        },
    },
    queue_task,
)
register(
    "inbox_status",
    {
        "name": "inbox_status",
        "description": "Report how many queued tasks are waiting.",
        "parameters": {"type": "object", "properties": {}},
    },
    inbox_status,
)


if __name__ == "__main__":
    from void.tools.registry import list_tools
    assert "queue_task" in list_tools() and "inbox_status" in list_tools()
    assert inbox_status()["pending"] >= 0
    print("inbox tool OK")
