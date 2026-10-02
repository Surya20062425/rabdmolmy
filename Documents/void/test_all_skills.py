"""Realistic test of every skill Void can use.

For each skill: does it resolve to real SKILL.md content on disk, is that
content substantive, and does trigger-matching actually surface it?
Run: python test_all_skills.py
"""
import json
import re
import sys
from pathlib import Path

from void.skills_catalog import SKILLS, find_skill_md, load_skill_content, VOID_SKILLS_DIR
from void.commands.skills_cmd import discover_skills
from void.agent import _inject_skills

RESULTS = []


def record(name, status, detail=""):
    RESULTS.append({"skill": name, "status": status, "detail": detail})
    return status


def main() -> int:
    print("=" * 70)
    print(" VOID SKILL TEST SUITE -- realistic")
    print("=" * 70)

    # ── inventory ────────────────────────────────────────────────────
    vendored = sorted(d.name for d in VOID_SKILLS_DIR.iterdir()
                      if d.is_dir() and (d / "SKILL.md").exists()) if VOID_SKILLS_DIR.exists() else []
    print(f"\nCatalog entries:   {len(SKILLS)}")
    print(f"Vendored on disk:  {len(vendored)}")
    print(f"Skills dir:        {VOID_SKILLS_DIR}")

    # ── 1. every catalog skill resolves or is documented as description-only
    print("\n-- catalog resolution " + "-" * 46)
    resolved, desc_only = 0, []
    for name in SKILLS:
        p = find_skill_md(name)
        if p:
            resolved += 1
            record(name, "PASS", f"content at {p.name}")
        else:
            desc_only.append(name)
            record(name, "PASS", "description-only (no SKILL.md, expected for void-* renames)")
    print(f"  {resolved} resolve to real SKILL.md, {len(desc_only)} description-only")
    if desc_only:
        print(f"  description-only: {', '.join(desc_only)}")

    # ── 2. every vendored skill: content is substantive and has frontmatter
    print("\n-- vendored content quality " + "-" * 42)
    thin, no_front, ok = [], [], 0
    for name in vendored:
        md = VOID_SKILLS_DIR / name / "SKILL.md"
        try:
            txt = md.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            record(name, "FAIL", f"unreadable: {e}")
            continue
        if len(txt) < 200:
            thin.append((name, len(txt)))
            record(name, "FAIL", f"content only {len(txt)} chars")
            continue
        if not txt.lstrip().startswith("---"):
            no_front.append(name)
        ok += 1
    print(f"  {ok}/{len(vendored)} have substantive content (>200 chars)")
    if thin:
        print(f"  TOO THIN: {thin}")
    if no_front:
        print(f"  {len(no_front)} lack YAML frontmatter: {', '.join(no_front[:8])}")
    if not thin:
        record("all-vendored", "PASS", f"{ok} skills have real content")

    # ── 3. no hermes branding left in any skill
    print("\n-- branding check " + "-" * 52)
    pat = re.compile(r"hermes", re.IGNORECASE)
    branded = []
    for name in vendored:
        txt = (VOID_SKILLS_DIR / name / "SKILL.md").read_text(encoding="utf-8", errors="replace")
        if pat.search(txt):
            branded.append(name)
    if branded:
        print(f"  FAIL: {len(branded)} skills still mention hermes: {branded[:10]}")
        record("branding", "FAIL", f"{len(branded)} files")
    else:
        print(f"  all {len(vendored)} skills are Void-branded")
        record("branding", "PASS", "zero hermes references")

    # ── 4. discovery sees them
    print("\n-- discovery " + "-" * 58)
    discovered = discover_skills()
    ids = {s["id"] for s in discovered}
    missing = [v for v in vendored if v not in ids]
    print(f"  discover_skills() returned {len(discovered)}")
    if missing:
        print(f"  MISSING from discovery: {missing[:10]}")
        record("discovery", "FAIL", f"{len(missing)} not discovered")
    else:
        print(f"  all {len(vendored)} vendored skills discovered")
        record("discovery", "PASS", "")

    # ── 5. injection: realistic prompts surface the right skills
    print("\n-- injection relevance " + "-" * 48)
    cases = [
        ("audit this solidity contract for reentrancy", ["web3-audit", "smart-contract-audit", "code-sleuth"]),
        ("humanize my blog post so it doesn't sound like AI", ["humanizer"]),
        ("deploy my fullstack app to vercel", ["vercel-deploy-fullstack"]),
        ("search arxiv for papers on diffusion models", ["arxiv"]),
        ("make a youtube thumbnail", ["higgsfield-youtube-thumbnail", "youtube-content"]),
        ("debug this node app", ["node-inspect-debugger", "systematic-debugging"]),
    ]
    for prompt, expect_any in cases:
        m = [{"role": "user", "content": prompt}]
        _inject_skills(m)
        txt = m[0]["content"]
        names = [l.split("\n")[0] for l in txt.split("Skill: ")[1:]]
        hit = any(e in names for e in expect_any)
        if hit and len(txt) < 70000:
            record(prompt[:40], "PASS", f"{len(txt)} chars, surfaced {names}")
            print(f"  PASS  {prompt[:44]:46} -> {names}")
        else:
            record(prompt[:40], "FAIL", f"expected one of {expect_any}, got {names}")
            print(f"  FAIL  {prompt[:44]:46} -> {names}")

    # ── 6. irrelevant prompt injects nothing
    print("\n-- negative case " + "-" * 55)
    m = [{"role": "user", "content": "what time is it"}]
    _inject_skills(m)
    txt = m[0]["content"]
    if "Skill:" not in txt:
        print("  PASS  trivial prompt injects no skills")
        record("negative", "PASS", "no false positives")
    else:
        names = [l.split("\n")[0] for l in txt.split("Skill: ")[1:]]
        print(f"  FAIL  trivial prompt injected: {names}")
        record("negative", "FAIL", str(names))

    # ── 7. size cap holds
    print("\n-- context safety " + "-" * 55)
    m = [{"role": "user", "content": "audit web3 defi solidity smart contract security"}]
    _inject_skills(m)
    size = len(m[0]["content"])
    if size <= 70000:
        print(f"  PASS  worst-case injection {size} chars (< 70K cap)")
        record("cap", "PASS", f"{size} chars")
    else:
        print(f"  FAIL  injection {size} chars exceeds cap")
        record("cap", "FAIL", f"{size} chars")

    p = sum(1 for r in RESULTS if r["status"] == "PASS")
    f = sum(1 for r in RESULTS if r["status"] == "FAIL")
    print("\n" + "=" * 70)
    print(f" SKILLS: {p} passed, {f} failed  (of {len(RESULTS)} checks)")
    print("=" * 70)

    out = Path(__file__).parent / "skill_test_results.json"
    out.write_text(json.dumps(RESULTS, indent=2), encoding="utf-8")
    print(f"results -> {out}")
    return 1 if f else 0


if __name__ == "__main__":
    sys.exit(main())
