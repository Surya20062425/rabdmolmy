"""Self-check for the expanded tool surface + skill catalog.

Run: python test_surface.py
"""


def test_tools_registered():
    from void.tools.registry import list_tools
    tools = set(list_tools())
    expected = {
        # system
        "system_read_file", "system_write_file", "system_shell",
        "system_ls", "system_pwd", "system_env_var",
        # web
        "web_fetch", "web_extract_text", "web_search",
        # email
        "email_list", "email_read", "email_send", "email_search",
        # task
        "task_list", "task_add", "task_done", "task_delete",
        # session
        "session_search", "session_read",
        # memory
        "memory_list", "memory_add", "memory_remove",
        # cronjob
        "cronjob_list", "cronjob_create", "cronjob_delete",
        # process
        "process_list", "process_start", "process_stop",
    }
    missing = expected - tools
    assert not missing, f"missing tools: {missing}"
    print(f"OK: {len(expected)} tools registered")


def test_schemas_valid():
    from void.tools.registry import get_schemas
    schemas = get_schemas()
    assert len(schemas) >= 26, f"expected >=26 schemas, got {len(schemas)}"
    for s in schemas:
        assert s["type"] == "function"
        assert "name" in s["function"]
        assert "parameters" in s["function"]
    print(f"OK: {len(schemas)} OpenAI-format schemas valid")


def test_task_roundtrip():
    from void.tools import task
    t = task.task_add("test task")
    assert t["status"] == "open"
    done = task.task_done(t["id"])
    assert done["status"] == "done"
    task.task_delete(t["id"])
    print("OK: task add/done/delete roundtrip")


def test_catalog():
    from void.skills_catalog import SKILLS, match_skills
    assert len(SKILLS) >= 100, f"expected >=100 skills, got {len(SKILLS)}"
    hits = match_skills("vercel")
    assert any("vercel" in s["name"] for s in hits), "vercel skill not matched"
    print(f"OK: {len(SKILLS)} skills in catalog")


def test_skill_injection():
    from void.agent import _inject_skills
    msgs = [{"role": "user", "content": "audit a smart contract for vulnerabilities"}]
    _inject_skills(msgs)
    sys_text = msgs[0]["content"]
    # Any contract-audit skill is a correct match here; the exact winner may
    # shift as triggers are tuned.
    assert any(s in sys_text for s in ("smart-contract-audit", "web3-audit", "code-sleuth")), \
        "no smart-contract skill injected"
    msgs2 = [{"role": "user", "content": "what time is it"}]
    _inject_skills(msgs2)
    injected = msgs2[0]["content"].split("Skill: ")[1:]
    catalog_hits = [l.split("\n")[0] for l in injected if not l.startswith("void")]
    assert not catalog_hits, f"false-positive skill injection: {catalog_hits}"
    print("OK: skill injection matches correctly, no false positives")


if __name__ == "__main__":
    test_tools_registered()
    test_schemas_valid()
    test_task_roundtrip()
    test_catalog()
    test_skill_injection()
    print("\nAll surface checks passed.")
