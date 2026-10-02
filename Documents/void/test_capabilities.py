"""Self-check for the capability fixes: sessions, cron, tools gating, skills, fallback.

Run: python test_capabilities.py
"""


def test_sessions_persist():
    """Chat messages land in the session DB and resume reads them back."""
    from void.sessions import create_session, add_message, get_session, delete_session
    s = create_session(title="capability test")
    add_message(s["id"], "user", "hello")
    add_message(s["id"], "assistant", "hi there")
    back = get_session(s["id"])
    assert back["message_count"] == 2, f"expected 2 messages, got {back['message_count']}"
    roles = [m["role"] for m in back["messages"]]
    assert roles == ["user", "assistant"], roles
    assert back["messages"][1]["content"] == "hi there"
    delete_session(s["id"])
    print("OK: sessions persist + resume reads history")


def test_tool_gating():
    """Disabled tools are filtered from the schemas the model sees."""
    import json
    from pathlib import Path
    from void.config import ensure_home
    from void.tools.registry import get_schemas, disabled_tools

    p = ensure_home() / "tool_state.json"
    original = p.read_text(encoding="utf-8") if p.exists() else None
    try:
        p.write_text(json.dumps({"disabled": ["web_search"]}), encoding="utf-8")
        names = [s["function"]["name"] for s in get_schemas()]
        assert "web_search" not in names, "disabled tool still sent to model"
        assert "system_shell" in names, "enabled tool was dropped"
        assert disabled_tools() == {"web_search"}
    finally:
        if original is None:
            p.unlink(missing_ok=True)
        else:
            p.write_text(original, encoding="utf-8")
    print("OK: tool gating filters disabled tools")


def test_cron_schedule_advance():
    """An interval job gets a future next_run after firing."""
    from void.commands.cron_cmd import create_job, _advance, delete_job
    job = create_job("30m", "noop test prompt")
    nxt = _advance(job, "2026-10-02T00:00:00+00:00")
    assert nxt is not None and nxt > "2026-10-02T00:00:00", f"bad next_run: {nxt}"
    # once jobs do not reschedule
    once = create_job("2026-10-02T09:00:00", "one shot")
    assert _advance(once, "2026-10-02T00:00:00+00:00") is None
    delete_job(job["id"])
    delete_job(once["id"])
    print("OK: cron reschedules intervals, retires one-shot jobs")


def test_cron_due_detection():
    """A job scheduled in the past is due; one in the future is not."""
    from void.commands.cron_cmd import _conn, create_job, due_jobs, delete_job
    job = create_job("30m", "due test")
    conn = _conn()
    try:
        conn.execute("UPDATE cron_jobs SET next_run = ? WHERE id = ?",
                     ("2020-01-01T00:00:00+00:00", job["id"]))
        conn.commit()
    finally:
        conn.close()
    ids = [j["id"] for j in due_jobs()]
    assert job["id"] in ids, "past-due job not detected"
    delete_job(job["id"])
    print("OK: cron due detection")


def test_skill_content_loads():
    """Catalog skills resolve to real SKILL.md content when on disk."""
    from void.skills_catalog import load_skill_content, find_skill_md, SKILLS
    path = find_skill_md("humanizer")
    if path is None:
        print("SKIP: no skills dir present -- catalog-only mode")
        return
    content = load_skill_content("humanizer")
    assert content and len(content) > 100, "skill content too short to be real"
    print(f"OK: skill content loads from disk ({len(content)} chars)")


def test_fallback_walks_chain():
    """Model.chat falls through to a fallback provider when the first fails."""
    from unittest.mock import MagicMock, patch
    from void.model import Model

    m = Model.__new__(Model)
    m.api_key = "bad"
    m.base_url = None
    m.model_name = "primary-model"
    m._client = MagicMock()
    m._client.chat.completions.create.side_effect = RuntimeError("primary down")

    alt_client = MagicMock()
    alt_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="from fallback", tool_calls=[]))]
    )
    with patch("void.model.OpenAI", return_value=alt_client), \
         patch("void.providers.get_fallback_chain", return_value=["backup"]), \
         patch("void.providers.get_provider", return_value={"api_key": "k2", "base_url": "http://x", "models": ["backup-model"]}):
        resp = m.chat([{"role": "user", "content": "hi"}])
    assert resp.content == "from fallback", f"fallback not used: {resp.content}"
    assert m.model_name == "backup-model", f"model not swapped: {m.model_name}"
    print("OK: fallback chain is consulted on failure")


if __name__ == "__main__":
    test_sessions_persist()
    test_tool_gating()
    test_cron_schedule_advance()
    test_cron_due_detection()
    test_skill_content_loads()
    test_fallback_walks_chain()
    print("\nAll capability checks passed.")
