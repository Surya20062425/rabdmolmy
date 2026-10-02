"""Void cron — scheduled jobs that run the agent.

Jobs stored in SQLite. Supports intervals (30m, every 2h) and cron expressions (0 9 * * *).
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import uuid
from datetime import datetime, timezone, timedelta

from void.config import ensure_home

DB_PATH = ensure_home() / "cron.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _ensure_schema() -> None:
    conn = _conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cron_jobs (
                id TEXT PRIMARY KEY,
                schedule_type TEXT NOT NULL,   -- 'interval' | 'cron' | 'once'
                schedule_value TEXT NOT NULL,
                prompt TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',  -- 'active' | 'paused' | 'completed'
                next_run TEXT,
                last_run TEXT,
                last_result TEXT,
                created_at TEXT NOT NULL,
                runs INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cron_next ON cron_jobs(next_run)")
        conn.commit()
    finally:
        conn.close()


_ensure_schema()


def create_job(schedule: str, prompt: str) -> dict:
    """Create a scheduled job. schedule is like '30m', 'every 2h', '0 9 * * *', or ISO timestamp."""
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Parse schedule
    schedule_type, schedule_value, next_run = _parse_schedule(schedule, now)

    conn = _conn()
    try:
        conn.execute(
            """INSERT INTO cron_jobs (id, schedule_type, schedule_value, prompt, status, next_run, created_at)
               VALUES (?, ?, ?, ?, 'active', ?, ?)""",
            (job_id, schedule_type, schedule_value, prompt, next_run, now),
        )
        conn.commit()
        return get_job(job_id)
    finally:
        conn.close()


def _parse_schedule(schedule: str, now: str) -> tuple[str, str, str | None]:
    """Parse a schedule string into (type, value, next_run_iso)."""
    now_dt = datetime.fromisoformat(now)

    if schedule.endswith("m") and schedule[:-1].isdigit():
        # Interval in minutes: 30m
        mins = int(schedule[:-1])
        return ("interval", schedule, (now_dt + timedelta(minutes=mins)).isoformat())
    elif schedule.startswith("every ") and schedule.endswith("h"):
        # Every N hours: every 2h
        hours = int(schedule[6:-1])
        return ("interval", schedule, (now_dt + timedelta(hours=hours)).isoformat())
    elif schedule.startswith("every ") and schedule.endswith("m"):
        mins = int(schedule[6:-1])
        return ("interval", schedule, (now_dt + timedelta(minutes=mins)).isoformat())
    elif " " in schedule and len(schedule.split()) == 5:
        # Cron expression: 0 9 * * *
        # Simple support: just parse the next occurrence
        return ("cron", schedule, _next_cron(schedule, now_dt))
    elif schedule.count("-") == 2 and schedule.count(":") == 2:
        # ISO timestamp: 2026-10-01T09:00:00
        try:
            dt = datetime.fromisoformat(schedule)
            return ("once", schedule, dt.isoformat())
        except ValueError:
            pass

    raise ValueError(f"Cannot parse schedule: {schedule}. Use '30m', 'every 2h', '0 9 * * *', or ISO timestamp.")


def _next_cron(cron_expr: str, from_dt: datetime) -> str | None:
    """Very simple cron parser — handles minute/hour/day/month/weekday basics."""
    # ponytail: naive single-occurrence cron, full cron 파싱은
    # APScheduler나python-crontab 사용 시 확장 가능
    parts = cron_expr.split()
    if len(parts) != 5:
        return None

    minute, hour, dom, month, dow = parts

    # Simple: if specific minute and hour given, return today or tomorrow at that time
    if minute != "*" and hour != "*":
        try:
            m, h = int(minute), int(hour)
            candidate = from_dt.replace(minute=m, hour=h, second=0, microsecond=0)
            if candidate <= from_dt:
                candidate += timedelta(days=1)
            return candidate.isoformat()
        except (ValueError, OverflowError):
            pass

    # Default: next hour
    return (from_dt + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0).isoformat()


def get_job(job_id: str) -> dict | None:
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM cron_jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            return None
        return dict(row)
    finally:
        conn.close()


def list_jobs(limit: int = 50) -> list[dict]:
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT * FROM cron_jobs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def edit_job(job_id: str, schedule: str | None = None, prompt: str | None = None) -> dict | None:
    conn = _conn()
    try:
        updates = []
        values = []
        if schedule is not None:
            st, sv, nr = _parse_schedule(schedule, datetime.now(timezone.utc).isoformat())
            updates.append("schedule_type = ?")
            updates.append("schedule_value = ?")
            updates.append("next_run = ?")
            values.extend([st, sv, nr])
        if prompt is not None:
            updates.append("prompt = ?")
            values.append(prompt)

        if not updates:
            return get_job(job_id)

        values.append(job_id)
        conn.execute(
            f"UPDATE cron_jobs SET {', '.join(updates)} WHERE id = ?",
            values,
        )
        conn.commit()
        return get_job(job_id)
    finally:
        conn.close()


def pause_job(job_id: str) -> dict | None:
    conn = _conn()
    try:
        conn.execute(
            "UPDATE cron_jobs SET status = 'paused' WHERE id = ?",
            (job_id,),
        )
        conn.commit()
        return get_job(job_id)
    finally:
        conn.close()


def resume_job(job_id: str) -> dict | None:
    conn = _conn()
    try:
        conn.execute(
            "UPDATE cron_jobs SET status = 'active' WHERE id = ?",
            (job_id,),
        )
        conn.commit()
        return get_job(job_id)
    finally:
        conn.close()


def run_job(job_id: str, prompt_override: str | None = None) -> dict | None:
    """Execute a job: run the prompt through the agent, store the result."""
    job = get_job(job_id)
    if not job:
        return None

    prompt = prompt_override or job["prompt"]
    result_text = ""
    try:
        from void.cli import build_model
        from void.agent import run as agent_run
        import argparse

        args = argparse.Namespace(api_key=None, base_url=None, model=None)
        model = build_model(args)
        result_text = agent_run(model, [{"role": "user", "content": prompt}])
    except Exception as e:
        result_text = f"ERROR: {e}"

    conn = _conn()
    try:
        now = datetime.now(timezone.utc).isoformat()
        next_run = _advance(job, now)
        conn.execute(
            """UPDATE cron_jobs SET last_run = ?, last_result = ?, runs = runs + 1, next_run = ?
               WHERE id = ?""",
            (now, result_text[:2000], next_run, job_id),
        )
        conn.commit()
        return get_job(job_id)
    finally:
        conn.close()


def _advance(job: dict, now_iso: str) -> str | None:
    """Compute the next run time for a job after it fires."""
    if job["schedule_type"] == "once":
        return None
    try:
        return _parse_schedule(job["schedule_value"], now_iso)[2]
    except ValueError:
        return None


def due_jobs() -> list[dict]:
    """Active jobs whose next_run has passed."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT * FROM cron_jobs WHERE status = 'active' AND next_run IS NOT NULL AND next_run <= ?",
            (now,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def tick() -> int:
    """Run every due job once. Returns how many fired."""
    fired = 0
    for job in due_jobs():
        run_job(job["id"])
        fired += 1
    return fired


def delete_job(job_id: str) -> bool:
    conn = _conn()
    try:
        cur = conn.execute("DELETE FROM cron_jobs WHERE id = ?", (job_id,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def job_stats() -> dict:
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*) as cnt, SUM(runs) as total_runs "
            "FROM cron_jobs WHERE status = 'active'",
        ).fetchone()
        return {
            "active_jobs": row["cnt"] or 0,
            "total_runs": row["total_runs"] or 0,
        }
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════════
# COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════════

def cmd_cron_list(args) -> None:
    from void.theme import header, table, green, green_bold, grey, dim, ok, DASH

    jobs = list_jobs()
    print(header("Scheduled Jobs", 1))
    if not jobs:
        print(grey("No scheduled jobs."))
        print(dim("  void cron create 30m 'check my inbox'"))
        return

    print(f"  {len(jobs)} job(s).\n")
    rows = []
    for j in jobs:
        job_id = j["id"][:8]
        stype = j["schedule_type"]
        sval = j["schedule_value"][:20]
        prompt = j["prompt"][:40]
        status = j["status"]
        next_run = j["next_run"][:16].replace("T", " ") if j["next_run"] else "---"
        rows.append([job_id, stype, sval, prompt, status, next_run])

    print(table(
        ["ID", "Type", "Schedule", "Prompt", "Status", "Next Run"],
        rows,
        [8, 10, 16, 40, 10, 18],
    ))
    print()
    print(dim(f"  {DASH} Type: interval = repeating, cron = cron expr, once = single run"))


def cmd_cron_create(args) -> None:
    from void.theme import ok, err, green_bold, dim

    if not args.schedule or not args.prompt:
        print(err("Usage: void cron create <schedule> <prompt>"))
        print(dim("  void cron create 30m 'what time is it'"))
        print(dim("  void cron create '0 9 * * *' 'daily standup'"))
        return

    try:
        job = create_job(args.schedule, args.prompt)
        print(ok(f"Created job {job['id'][:8]}"))
        print(f"  {dim('Schedule:')} {job['schedule_value']}")
        print(f"  {dim('Next run:')} {job['next_run'][:16].replace('T', ' ') if job['next_run'] else 'immediately'}")
        print(f"  {dim('Prompt:')} {job['prompt'][:60]}")
    except ValueError as e:
        print(err(str(e)))


def cmd_cron_edit(args) -> None:
    from void.theme import ok, err, dim

    if not args.id:
        print(err("Usage: void cron edit <id> [--schedule <sched>] [--prompt <prompt>]"))
        return

    try:
        job = edit_job(args.id, args.schedule, args.prompt)
        if job:
            print(ok(f"Edited job {job['id'][:8]}"))
            if args.schedule:
                print(f"  {dim('Schedule:')} {job['schedule_value']}")
            if args.prompt:
                print(f"  {dim('Prompt:')} {job['prompt'][:60]}")
        else:
            print(err(f"Job not found: {args.id[:8]}"))
    except ValueError as e:
        print(err(str(e)))


def cmd_cron_pause(args) -> None:
    from void.theme import ok, err

    if not args.id:
        print(err("Usage: void cron pause <id>"))
        return

    job = pause_job(args.id)
    if job:
        print(ok(f"Paused job {job['id'][:8]}"))
    else:
        print(err(f"Job not found: {args.id[:8]}"))


def cmd_cron_resume(args) -> None:
    from void.theme import ok, err

    if not args.id:
        print(err("Usage: void cron resume <id>"))
        return

    job = resume_job(args.id)
    if job:
        print(ok(f"Resumed job {job['id'][:8]}"))
    else:
        print(err(f"Job not found: {args.id[:8]}"))


def cmd_cron_run(args) -> None:
    from void.theme import ok, err, dim

    if not args.id:
        print(err("Usage: void cron run <id>"))
        return

    job = run_job(args.id)
    if job:
        print(ok(f"Triggered job {job['id'][:8]}"))
        print(f"  {dim('Prompt:')} {job['prompt'][:60]}")
    else:
        print(err(f"Job not found: {args.id[:8]}"))


def cmd_cron_remove(args) -> None:
    from void.theme import ok, err

    if not args.id:
        print(err("Usage: void cron remove <id>"))
        return

    if delete_job(args.id):
        print(ok(f"Removed job {args.id[:8]}"))
    else:
        print(err(f"Job not found: {args.id[:8]}"))


def cmd_cron_status(args) -> None:
    from void.theme import header, table, green, green_bold, grey, dim, DASH

    jobs = list_jobs()
    print(header("Job Statuses", 1))
    if not jobs:
        print(grey("No jobs."))
        return

    active = sum(1 for j in jobs if j["status"] == "active")
    paused = sum(1 for j in jobs if j["status"] == "paused")
    print(f"  {green_bold('Active:')} {active}  {dim('·')}  {grey('Paused:')} {paused}")
    stats = job_stats()
    active_jobs = stats["active_jobs"]
    print(f"  {dim(f'{DASH} {active_jobs} active jobs')}")
    print()

    rows = []
    for j in jobs:
        rows.append([
            j["id"][:8],
            j["prompt"][:40],
            j["status"],
            j["next_run"][:16].replace("T", " ") if j["next_run"] else "---",
            str(j["runs"]),
        ])
    print(table(
        ["ID", "Prompt", "Status", "Next Run", "Runs"],
        rows,
        [8, 40, 10, 18, 8],
    ))


def cmd_cron_tick(args) -> None:
    """Run all due jobs once (for external schedulers / Task Scheduler)."""
    from void.theme import ok, grey, dim

    fired = tick()
    if fired:
        print(ok(f"Fired {fired} job(s)"))
    else:
        print(grey("No jobs due."))


def cmd_cron_daemon(args) -> None:
    """Run due jobs forever on a fixed interval."""
    import time
    from void.theme import ok, dim, err

    interval = max(10, int(getattr(args, "interval", 60)))
    print(ok(f"cron daemon running every {interval}s — Ctrl-C to stop"))
    try:
        while True:
            n = tick()
            if n:
                print(dim(f"  fired {n} job(s)"))
            time.sleep(interval)
    except KeyboardInterrupt:
        print()
        print(dim("daemon stopped"))


def cmd_cron_logs(args) -> None:
    """Show last results for jobs that have run."""
    from void.theme import header, grey, dim, green_bold, table

    jobs = [j for j in list_jobs() if j.get("last_run")]
    print(header("Job Results", 1))
    if not jobs:
        print(grey("No jobs have run yet."))
        return
    for j in jobs:
        print(f"  {green_bold(j['id'][:8])}  {dim(j['last_run'][:16].replace('T', ' '))}")
        print(f"    {j['prompt'][:60]}")
        print(f"    {dim((j.get('last_result') or '')[:200])}")
        print()


# Dispatch
_CRON_DISPATCH = {
    "list":    cmd_cron_list,
    "create":  cmd_cron_create,
    "edit":    cmd_cron_edit,
    "pause":   cmd_cron_pause,
    "resume":  cmd_cron_resume,
    "run":     cmd_cron_run,
    "remove":  cmd_cron_remove,
    "status":  cmd_cron_status,
    "tick":    cmd_cron_tick,
    "daemon":  cmd_cron_daemon,
    "logs":    cmd_cron_logs,
}


def main(args: argparse.Namespace) -> None:
    if args.subcommand in _CRON_DISPATCH:
        _CRON_DISPATCH[args.subcommand](args)
    else:
        from void.theme import err
        print(err(f"Unknown cron subcommand: {args.subcommand}"))
        import sys
        sys.exit(1)
