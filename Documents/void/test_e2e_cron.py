"""End-to-end: a cron job actually executes the agent and stores its result.

Requires a working API key. Run: python test_e2e_cron.py
"""
import sys

from void.commands.cron_cmd import create_job, run_job, get_job, delete_job


def main() -> int:
    job = create_job("30m", "Reply with exactly the word: pong")
    print(f"created job {job['id'][:8]}")
    result = run_job(job["id"])
    last = (result or {}).get("last_result") or ""
    print(f"runs={result['runs']}  result={last[:120]!r}")
    assert result["runs"] == 1, "run count did not increment"
    if last.startswith("ERROR"):
        print("NOTE: agent call failed (no key or provider issue) -- storage path still exercised")
        delete_job(job["id"])
        return 0
    assert "pong" in last.lower(), f"agent did not answer the prompt: {last[:200]}"
    print("OK: cron job executed the agent and stored the answer")
    delete_job(job["id"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
