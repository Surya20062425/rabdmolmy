"""Void skills — skill management.

Skills are SKILL.md files injected into the system prompt.
Stored in ~/.void/skills/ as individual .md files.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

from void.config import ensure_home

SKILLS_DIR = ensure_home() / "skills"
SKILLS_REGISTRY = ensure_home() / "skills_registry.json"

# Unicode symbols
DASH = "\u2014"


def _ensure_skills_dir() -> None:
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)


def _load_registry() -> dict:
    if not SKILLS_REGISTRY.exists():
        return {}
    try:
        return json.loads(SKILLS_REGISTRY.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_registry(reg: dict) -> None:
    SKILLS_REGISTRY.write_text(json.dumps(reg, indent=2, default=str) + "\n", encoding="utf-8")


def discover_skills() -> list[dict]:
    """Discover installed skills from the skills directory.

    Supports both layouts: registry-tracked flat .md files and vendored
    <name>/SKILL.md directories.
    """
    _ensure_skills_dir()
    reg = _load_registry()
    result = []
    seen = set()

    for name, info in reg.items():
        md_path = SKILLS_DIR / f"{name}.md"
        if not md_path.exists():
            md_path = SKILLS_DIR / name / "SKILL.md"
        seen.add(name)
        result.append({
            "id": name,
            "name": info.get("name", name),
            "version": info.get("version", "0.1.0"),
            "installed_at": info.get("installed_at", ""),
            "source": info.get("source", ""),
            "description": info.get("description", ""),
            "tools": info.get("tools", []),
            "path": str(md_path) if md_path.exists() else None,
        })

    # Vendored skills not in the registry
    if SKILLS_DIR.exists():
        for d in sorted(SKILLS_DIR.iterdir()):
            if not d.is_dir() or d.name in seen:
                continue
            md = d / "SKILL.md"
            if not md.exists():
                continue
            desc = ""
            try:
                head = md.read_text(encoding="utf-8")[:800]
                for line in head.splitlines():
                    if line.lower().startswith("description:"):
                        desc = line.split(":", 1)[1].strip().strip('"')
                        break
            except OSError:
                pass
            result.append({
                "id": d.name,
                "name": d.name,
                "version": "0.1.0",
                "installed_at": "",
                "source": "vendored",
                "description": desc,
                "tools": [],
                "path": str(md),
            })

    return sorted(result, key=lambda s: s["name"])


def install_skill(skill_id: str, url: str | None = None, repo: str | None = None) -> dict:
    """Install a skill from URL or GitHub repo."""
    _ensure_skills_dir()
    reg = _load_registry()

    if skill_id in reg:
        raise ValueError(f"Skill already installed: {skill_id}")

    content = None
    source = ""

    if url:
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                content = resp.read().decode("utf-8")
            source = url
        except Exception as e:
            raise ValueError(f"Failed to fetch skill from URL: {e}")
    elif repo:
        raw_url = f"https://raw.githubusercontent.com/{repo}/main/SKILL.md"
        try:
            with urllib.request.urlopen(raw_url, timeout=30) as resp:
                content = resp.read().decode("utf-8")
            source = f"github:{repo}"
        except Exception:
            raw_url = f"https://raw.githubusercontent.com/{repo}/master/SKILL.md"
            with urllib.request.urlopen(raw_url, timeout=30) as resp:
                content = resp.read().decode("utf-8")
            source = f"github:{repo}"

    if not content:
        raise ValueError("No content source provided. Use --url or --repo.")

    name = skill_id
    description = ""
    version = "0.1.0"
    tools = []

    if content.startswith("---\n"):
        parts = content.split("---\n", 2)
        if len(parts) >= 3:
            try:
                fm = json.loads(parts[1]) if parts[1].strip().startswith("{") else {}
                if not isinstance(fm, dict):
                    fm = {}
            except json.JSONDecodeError:
                fm = {}
                for line in parts[1].split("\n"):
                    if ":" in line:
                        k, v = line.split(":", 1)
                        fm[k.strip()] = v.strip().strip('"')
            name = fm.get("name", skill_id)
            description = fm.get("description", "")
            version = fm.get("version", "0.1.0")
            raw_tools = fm.get("tools", [])
            tools = raw_tools if isinstance(raw_tools, list) else [raw_tools] if raw_tools else []

    md_path = SKILLS_DIR / f"{skill_id}.md"
    md_path.write_text(content, encoding="utf-8")

    reg[skill_id] = {
        "name": name,
        "description": description,
        "version": version,
        "tools": tools,
        "source": source,
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "path": str(md_path),
    }
    _save_registry(reg)

    return {
        "id": skill_id,
        "name": name,
        "version": version,
        "description": description,
        "tools": tools,
        "installed_at": reg[skill_id]["installed_at"],
    }


def uninstall_skill(skill_id: str) -> bool:
    """Remove a skill."""
    reg = _load_registry()
    if skill_id not in reg:
        return False

    md_path = SKILLS_DIR / f"{skill_id}.md"
    if md_path.exists():
        md_path.unlink()

    del reg[skill_id]
    _save_registry(reg)
    return True


def get_skill(skill_id: str) -> dict | None:
    """Get a skill by ID."""
    reg = _load_registry()
    if skill_id in reg:
        info = reg[skill_id]
        return {
            "id": skill_id,
            "name": info.get("name", skill_id),
            "version": info.get("version", "0.1.0"),
            "description": info.get("description", ""),
            "tools": info.get("tools", []),
            "source": info.get("source", ""),
            "installed_at": info.get("installed_at", ""),
            "path": info.get("path", ""),
        }
    # Fall back to a vendored skill (<name>/SKILL.md) not tracked in the registry
    for s in discover_skills():
        if s["id"] == skill_id:
            return {
                "id": skill_id,
                "name": s["name"],
                "version": s["version"],
                "description": s["description"],
                "tools": s["tools"],
                "source": s["source"],
                "installed_at": s["installed_at"],
                "path": s["path"] or "",
            }
    return None


def update_skill(skill_id: str, repo: str | None = None) -> dict | None:
    """Update an installed skill from its source."""
    if repo:
        source = f"github:{repo}"
    else:
        reg = _load_registry()
        if skill_id not in reg:
            return None
        source = reg[skill_id].get("source", "")

    if source.startswith("github:"):
        repo_name = source[7:]
        return install_skill(skill_id, repo=repo_name)
    return None


def search_skills(query: str) -> list[dict]:
    """Search installed + catalog skills by keyword."""
    q = query.lower()
    installed = discover_skills()
    hits = [s for s in installed if q in s["name"].lower() or q in s.get("description", "").lower()]
    seen = {s["id"] for s in hits}
    from void.skills_catalog import SKILLS
    for name, info in SKILLS.items():
        if name in seen:
            continue
        if q in name.lower() or q in info["description"].lower() or q in info["trigger"].lower():
            hits.append({"id": name, "name": name, "description": info["description"], "tools": info["tools"]})
    return hits


# ═══════════════════════════════════════════════════════════════════
# COMMAND HANDLERS
# ═══════════════════════════════════════════════════════════════════

def cmd_skills_list(args) -> None:
    from void.theme import header, green, green_bold, grey, dim, ok

    skills = discover_skills()
    print(header("Skills", 1))
    if not skills:
        print(grey("No skills installed."))
        print(dim("  Install one:  void skills install <url>"))
        print(dim("  Or:           void skills tap add <repo>"))
        return

    print(f"  {len(skills)} skill(s) installed.\n")
    for s in skills:
        name = green_bold(s["name"])
        desc = dim(s.get("description", "")[:60])
        tools = grey(f"[{len(s.get('tools', []))} tool(s)]")
        print(f"  {name}  {desc}")
        print(f"       {grey(s['id'])}  {tools}  {dim(s['version'])}")
        print()


def cmd_skills_browse(args) -> None:
    from void.theme import header, dim, green, green_bold, grey, DASH
    from void.skills_catalog import SKILLS

    print(header("Skill Catalog", 1))
    print(f"  {len(SKILLS)} skills available.\n")
    cats = {}
    for name, info in SKILLS.items():
        tools = info.get("tools", [])
        key = tools[0] if tools else "other"
        cats.setdefault(key, []).append(name)
    for key, names in sorted(cats.items()):
        print(f"  {green_bold(key)}  {grey(f'({len(names)})')}")
        print(f"    {dim(', '.join(names))}")
        print()


def cmd_skills_search(args) -> None:
    from void.theme import header, green, green_bold, grey, dim

    skills = search_skills(args.query)
    print(header(f"Search: {args.query}", 1))
    if not skills:
        print(grey("No matching skills."))
        return

    for s in skills:
        print(f"  {green_bold(s['name'])}  {dim(s.get('description', '')[:60])}")
        print(f"       {grey(s['id'])}")
    print(f"\n  {len(skills)} result(s).")


def cmd_skills_inspect(args) -> None:
    from void.theme import header, green, green_bold, grey, white, dim, err
    from pathlib import Path

    if not args.id:
        print(err("Usage: void skills inspect <id>"))
        return

    skill = get_skill(args.id)
    if not skill:
        print(err(f"Skill not found: {args.id}"))
        return

    print(header(f"Skill: {skill['name']}", 1))
    print(f"  {green_bold('ID:')} {grey(skill['id'])}")
    print(f"  {green_bold('Version:')} {grey(skill['version'])}")
    print(f"  {green_bold('Description:')} {white(skill['description'])}")
    print(f"  {green_bold('Tools:')} {grey(', '.join(skill['tools']) or '(none)')}")
    print(f"  {green_bold('Source:')} {grey(skill['source'])}")
    print(f"  {green_bold('Installed:')} {grey(skill['installed_at'])}")
    print()
    print(dim("--- SKILL.md content ---"))
    print()
    content = Path(skill["path"]).read_text(encoding="utf-8") if skill["path"] else "(not found)"
    print(content[:2000])


def cmd_skills_install(args) -> None:
    from void.theme import ok, err
    from void.commands.skills_cmd import install_skill
    from void.config import ensure_home
    from pathlib import Path

    if args.path and args.url:
        print(err("Usage: void skills install <url>   or   void skills install --path <file>"))
        return
    if not args.path and not args.url:
        print(err("Usage: void skills install <url>   or   void skills install --path <file>"))
        return

    try:
        if args.path:
            path = Path(args.path)
            if not path.exists():
                print(err(f"File not found: {args.path}"))
                return
            content = path.read_text(encoding="utf-8")
            skill_id = path.stem
            ensure_home() / "skills"
            dest = ensure_home() / "skills" / f"{skill_id}.md"
            dest.write_text(content, encoding="utf-8")
            from void.commands.skills_cmd import _load_registry, _save_registry
            from datetime import datetime, timezone
            reg = _load_registry()
            reg[skill_id] = {
                "name": skill_id,
                "description": "",
                "version": "0.1.0",
                "tools": [],
                "source": str(path),
                "installed_at": datetime.now(timezone.utc).isoformat(),
                "path": str(dest),
            }
            _save_registry(reg)
            print(ok(f"Installed skill: {skill_id}"))
        else:
            skill_id = args.url.rstrip("/").split("/")[-1]
            if skill_id.endswith(".md"):
                skill_id = skill_id[:-3]
            result = install_skill(skill_id, url=args.url)
            print(ok(f"Installed skill: {result['name']} (v{result['version']})"))
    except ValueError as e:
        print(err(str(e)))


def cmd_skills_uninstall(args) -> None:
    from void.theme import ok, err

    if not args.name:
        print(err("Usage: void skills uninstall <name>"))
        return

    if uninstall_skill(args.name):
        print(ok(f"Uninstalled: {args.name}"))
    else:
        print(err(f"Skill not found: {args.name}"))


def cmd_skills_update(args) -> None:
    from void.theme import ok, grey

    reg = _load_registry()
    updated = []
    for skill_id, info in reg.items():
        source = info.get("source", "")
        if source.startswith("github:"):
            try:
                result = update_skill(skill_id, repo=source[7:])
                if result:
                    updated.append(result["name"])
            except Exception:
                pass

    if updated:
        print(ok(f"Updated {len(updated)} skill(s): {', '.join(updated)}"))
    else:
        print(grey("No updatable skills (only GitHub-sourced skills can be updated)."))


def cmd_skills_config(args) -> None:
    from void.theme import header, dim

    print(header("Skill Config", 1))
    print(dim("Skill enable/disable per platform coming in a future update."))
    print()
    print(dim("Current: all installed skills are enabled for CLI."))


def cmd_skills_check(args) -> None:
    from void.theme import dim, grey, ok

    reg = _load_registry()
    outdated = []
    for skill_id, info in reg.items():
        source = info.get("source", "")
        if source.startswith("github:"):
            outdated.append(info.get("name", skill_id))

    if outdated:
        print(dim(f"{len(outdated)} skill(s) could have updates: {', '.join(outdated)}"))
        print()
        print(dim("  void skills update  to update all GitHub-sourced skills"))
    else:
        print(grey("No GitHub-sourced skills to check."))


def cmd_skills_publish(args) -> None:
    from void.theme import ok, dim, err
    from pathlib import Path

    if not args.path:
        print(err("Usage: void skills publish <path>"))
        return

    path = Path(args.path)
    if not path.exists():
        print(err(f"File not found: {args.path}"))
        return

    print(ok(f"Skill ready to publish: {path.name}"))
    print()
    print(dim("Publishing requires a skill hub account."))
    print(dim("  Coming in a future update."))


def cmd_skills_tap(args) -> None:
    from void.theme import ok, dim, err
    import urllib.request

    if not args.repo:
        print(err("Usage: void skills tap add <owner/repo>"))
        return

    repo = args.repo.strip()
    if "/" not in repo:
        print(err("Format: void skills tap add <owner/repo>"))
        return

    raw_url = f"https://raw.githubusercontent.com/{repo}/main/SKILL.md"
    try:
        urllib.request.urlopen(raw_url, timeout=10)
        print(ok(f"Added skill source: {repo}"))
        print(dim(f"  Install with: void skills install --repo {repo}"))
    except Exception:
        raw_url = f"https://raw.githubusercontent.com/{repo}/master/SKILL.md"
        try:
            urllib.request.urlopen(raw_url, timeout=10)
            print(ok(f"Added skill source: {repo}"))
            print(dim(f"  Install with: void skills install --repo {repo}"))
        except Exception:
            print(err(f"No SKILL.md found in {repo} (tried main and master branches)."))


# Dispatch table
_SKILLS_DISPATCH = {
    "list":       cmd_skills_list,
    "browse":     cmd_skills_browse,
    "search":     cmd_skills_search,
    "inspect":    cmd_skills_inspect,
    "install":    cmd_skills_install,
    "uninstall":  cmd_skills_uninstall,
    "update":     cmd_skills_update,
    "config":     cmd_skills_config,
    "check":      cmd_skills_check,
    "publish":    cmd_skills_publish,
    "tap":        cmd_skills_tap,
}


def main(args: argparse.Namespace) -> None:
    if args.subcommand == "tap":
        subcommand = getattr(args, "tap_subcommand", "add")
        tap_args = argparse.Namespace(subcommand=subcommand, repo=getattr(args, "repo", None))
        if tap_args.subcommand in _SKILLS_DISPATCH:
            _SKILLS_DISPATCH[tap_args.subcommand](tap_args)
        else:
            from void.theme import err
            print(err(f"Unknown skills tap subcommand: {subcommand}"))
    elif args.subcommand in _SKILLS_DISPATCH:
        _SKILLS_DISPATCH[args.subcommand](args)
    else:
        from void.theme import err
        print(err(f"Unknown skills subcommand: {args.subcommand}"))
    import sys
    sys.exit(0)
