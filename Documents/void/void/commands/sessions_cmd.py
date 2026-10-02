"""Void sessions — session management.

Sessions stored in SQLite (~/.void/sessions.db).
Surface: list, browse, rename, delete, export, prune, stats.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from void.sessions import (
    create_session,
    get_session,
    list_sessions,
    rename_session,
    delete_session,
    add_message,
    list_messages,
    export_session,
    prune_sessions,
    session_stats,
)
from void.theme import (
    green, green_bold, white, grey, dim, red as orange,
    ok, warn, err, table, header, cmd_entry, bullet,
    BOX_DIV, section_divider,
)


def cmd_sessions_list(args) -> None:
    """List all sessions."""
    sessions = list_sessions(limit=getattr(args, 'limit', None) or 50, offset=getattr(args, 'offset', 0))
    if not sessions:
        print(grey("No sessions found."))
        print(dim("  Start a chat with void chat to create one."))
        return

    print(header("Sessions", 1))
    rows = []
    for s in sessions:
        title = s["title"][:30]
        updated = s["updated_at"][:16].replace("T", " ")
        msgs = str(s["message_count"])
        rows.append([s["id"][:8], title, updated, msgs])

    print(table(
        ["ID", "Title", "Last Active", "Messages"],
        rows,
        [8, 30, 18, 10],
    ))
    print()
    print(dim(f"  {len(sessions)} session(s) shown.  void sessions list --offset 50 for more."))


def cmd_sessions_browse(args) -> None:
    """Browse sessions interactively."""
    sessions = list_sessions(limit=100)
    if not sessions:
        print(grey("No sessions to browse."))
        return

    print(header("Browse Sessions", 1))
    for i, s in enumerate(sessions[:30], 1):
        updated = s["updated_at"][:16].replace("T", " ")
        print(f"  {green(str(i).rjust(2) + '.')}  {green_bold(s['title'][:35])}")
        print(f"       {grey(updated)}  [{s['message_count']} messages]")

    if len(sessions) > 30:
        print(f"  {dim(f'...and {len(sessions) - 30} more. Use void sessions list for full list.')}")

    print()
    print(dim("  void sessions export <id>  to save a session to JSON"))


def cmd_sessions_rename(args) -> None:
    """Rename a session."""
    if not args.id or not args.title:
        print(err("Usage: void sessions rename <id> <title>"))
        return

    result = rename_session(args.id, args.title)
    if result:
        print(ok(f"Renamed to: {args.title}"))
    else:
        print(err(f"Session not found: {args.id[:8]}"))


def cmd_sessions_delete(args) -> None:
    """Delete a session."""
    if not args.id:
        print(err("Usage: void sessions delete <id>"))
        return

    if delete_session(args.id):
        print(ok(f"Deleted session {args.id[:8]}"))
    else:
        print(err(f"Session not found: {args.id[:8]}"))


def cmd_sessions_export(args) -> None:
    """Export a session to JSON."""
    if not args.id:
        print(err("Usage: void sessions export <id> [output_path]"))
        return

    try:
        path = export_session(args.id, args.output)
        print(ok(f"Exported to: {path}"))
    except ValueError as e:
        print(err(str(e)))


def cmd_sessions_prune(args) -> None:
    """Prune old sessions."""
    count = prune_sessions(age_days=args.days)
    if count:
        print(ok(f"Pruned {count} session(s) older than {args.days} days"))
    else:
        print(grey("No sessions to prune."))


def cmd_sessions_stats(args) -> None:
    """Show session statistics."""
    stats = session_stats()
    print(header("Session Stats", 1))
    print(f"  {green_bold('Sessions:')} {stats['session_count']}")
    print(f"  {green_bold('Messages:')} {stats['total_messages']}")
    print(f"  {green_bold('Duration:')} {stats['total_duration_seconds']}s")
    print()


# Subcommand dispatch table
_SESSIONS_DISPATCH = {
    "list":    cmd_sessions_list,
    "browse":  cmd_sessions_browse,
    "rename":  cmd_sessions_rename,
    "delete":  cmd_sessions_delete,
    "export":  cmd_sessions_export,
    "prune":   cmd_sessions_prune,
    "stats":   cmd_sessions_stats,
}


def main(args: argparse.Namespace) -> None:
    if args.subcommand in _SESSIONS_DISPATCH:
        _SESSIONS_DISPATCH[args.subcommand](args)
    else:
        print(err(f"Unknown sessions subcommand: {args.subcommand}"))
        print(dim("  void sessions --help for usage."))
        sys.exit(1)
