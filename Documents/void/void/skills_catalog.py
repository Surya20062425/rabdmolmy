"""Void skill catalog -- the skills Void knows about.
Each skill has: name, description, tools it uses, when to trigger it.
"""

import os
from pathlib import Path

SKILLS = {
    # void-core
    "void-agent": {
        "name": "void-agent",
        "description": "Use, configure, theme, and extend Void",
        "tools": ["web_search", "system_shell", "system_read_file"],
        "trigger": "void configuration, setup, theme",
    },
    "void-providers": {
        "name": "void-providers",
        "description": "Add LLM providers to Void: keys, config, verify",
        "tools": ["system_read_file", "system_write_file", "system_shell"],
        "trigger": "add provider, api key, llm provider",
    },

    # devops
    "vercel-deploy-fullstack": {
        "name": "vercel-deploy-fullstack",
        "description": "Deploy full-stack Vite+Express projects to Vercel free tier",
        "tools": ["system_shell", "system_read_file", "system_write_file"],
        "trigger": "deploy vercel, push to vercel, fullstack deploy",
    },

    # creative
    "architecture-diagram": {
        "name": "architecture-diagram",
        "description": "Dark-themed SVG architecture/cloud/infra diagrams",
        "tools": ["system_write_file"],
        "trigger": "architecture diagram, svg infra, cloud diagram",
    },
    "ascii-video": {
        "name": "ascii-video",
        "description": "Convert video/audio to colored ASCII MP4/GIF",
        "tools": ["system_shell"],
        "trigger": "ascii video, ascii art video",
    },
    "baoyu-infographic": {
        "name": "baoyu-infographic",
        "description": "Infographics: 21 layouts x 21 styles",
        "tools": ["system_shell", "system_write_file"],
        "trigger": "infographic, chart, data viz",
    },
    "claude-design": {
        "name": "claude-design",
        "description": "Design one-off HTML artifacts (landing, deck, prototype)",
        "tools": ["system_write_file"],
        "trigger": "html landing page, design prototype, deck",
    },
    "design-md": {
        "name": "design-md",
        "description": "Author/validate/export Google's DESIGN.md token spec files",
        "tools": ["system_read_file", "system_write_file"],
        "trigger": "design md, design tokens, token spec",
    },
    "humanizer": {
        "name": "humanizer",
        "description": "Humanize text: strip AI-isms and add real voice",
        "tools": ["web_search"],
        "trigger": "humanize text, make it sound human, strip AI",
    },
    "manim-video": {
        "name": "manim-video",
        "description": "Manim CE animations: 3Blue1Brown math/algo videos",
        "tools": ["system_shell"],
        "trigger": "manim animation, math video, 3blue1brown",
    },
    "p5js": {
        "name": "p5js",
        "description": "p5.js sketches: gen art, shaders, interactive, 3D",
        "tools": ["system_shell"],
        "trigger": "p5js creative coding, sketch, shader",
    },
    "popular-web-designs": {
        "name": "popular-web-designs",
        "description": "54 real design systems (Stripe, Linear, Vercel) as HTML/CSS",
        "tools": ["system_write_file"],
        "trigger": "design system, stripe clone, linear ui",
    },
    "songsee": {
        "name": "songsee",
        "description": "Audio spectrograms/features (mel, chroma, MFCC) via CLI",
        "tools": ["system_shell"],
        "trigger": "audio spectrogram, mel spectrogram, mfcc",
    },
    "songwriting-and-ai-music": {
        "name": "songwriting-and-ai-music",
        "description": "Songwriting craft and Suno AI music prompts",
        "tools": ["web_search"],
        "trigger": "songwriting, suno, music prompt, lyrics",
    },

    # UI/UX
    "banner-design": {
        "name": "banner-design",
        "description": "Design banners for social media, ads, website heroes",
        "tools": ["system_write_file"],
        "trigger": "banner design, social media banner, ad banner",
    },
    "brand": {
        "name": "brand",
        "description": "Brand voice, visual identity, messaging frameworks, assets",
        "tools": ["system_read_file", "system_write_file", "web_search"],
        "trigger": "brand identity, brand voice, visual identity",
    },
    "design": {
        "name": "design",
        "description": "Comprehensive design skill: brand identity, design tokens, UI patterns",
        "tools": ["system_write_file"],
        "trigger": "comprehensive design, design system, UI design",
    },
    "design-system": {
        "name": "design-system",
        "description": "Token architecture, component specifications, slide decks",
        "tools": ["system_write_file"],
        "trigger": "design system, tokens, component spec",
    },
    "slides": {
        "name": "slides",
        "description": "Strategic HTML presentations with Chart.js, design tokens",
        "tools": ["system_write_file"],
        "trigger": "presentation, html slides, deck",
    },
    "ui-styling": {
        "name": "ui-styling",
        "description": "Beautiful, accessible user interfaces with shadcn/ui",
        "tools": ["system_write_file"],
        "trigger": "ui styling, shadcn, accessible design",
    },
    "ui-ux-pro-max": {
        "name": "ui-ux-pro-max",
        "description": "UI/UX design intelligence for web, mobile, and desktop",
        "tools": ["system_write_file", "web_search"],
        "trigger": "ui ux, wireframe, mockup, user experience",
    },

    # software-development
    "cli-agent-python": {
        "name": "cli-agent-python",
        "description": "Build a CLI agent in Python with model tools and theming",
        "tools": ["system_shell", "system_read_file", "system_write_file"],
        "trigger": "cli agent, python agent, terminal ai",
    },
    "codebase-inspection": {
        "name": "codebase-inspection",
        "description": "Inspect codebases: LOC, languages, ratios with pygount",
        "tools": ["system_shell"],
        "trigger": "inspect codebase, lines of code, stats",
    },
    "dogfood": {
        "name": "dogfood",
        "description": "Exploratory QA of web apps: find bugs, evidence, reports",
        "tools": ["web_fetch", "web_extract_text", "system_write_file"],
        "trigger": "qa, dogfood, test web app, find bugs",
    },
    "github": {
        "name": "github",
        "description": "GitHub via gh CLI: PRs, issues, reviews, repos, auth",
        "tools": ["system_shell"],
        "trigger": "github pr, issue, review, repo, auth",
    },
    "void-skill-authoring": {
        "name": "void-skill-authoring",
        "description": "Author in-repo SKILL.md files: frontmatter and structure",
        "tools": ["system_write_file", "system_read_file"],
        "trigger": "skill authoring, write skill, SKILL.md",
    },
    "void-theme-authoring": {
        "name": "void-theme-authoring",
        "description": "Void CLI branding and theming reference",
        "tools": ["system_read_file", "system_write_file"],
        "trigger": "branding, theme, cli colors",
    },
    "inspecting-desktop-dom": {
        "name": "inspecting-desktop-dom",
        "description": "Read a live desktop app DOM/CSS over CDP",
        "tools": ["system_shell"],
        "trigger": "desktop dom, cd inspect, electron devtools",
    },
    "node-inspect-debugger": {
        "name": "node-inspect-debugger",
        "description": "Debug Node.js via --inspect + Chrome DevTools Protocol CLI",
        "tools": ["system_shell"],
        "trigger": "debug node, inspect, chrome devtools protocol",
    },
    "requesting-code-review": {
        "name": "requesting-code-review",
        "description": "Pre-commit review: security scan, quality gates, auto-fix",
        "tools": ["system_shell", "system_read_file"],
        "trigger": "code review, pre-commit, lint, security scan",
    },
    "simplify-code": {
        "name": "simplify-code",
        "description": "Parallel 4-agent cleanup of recent code changes",
        "tools": ["system_shell", "system_read_file", "system_write_file"],
        "trigger": "simplify, refactor, cleanup code",
    },
    "spike": {
        "name": "spike",
        "description": "Throwaway experiments to validate an idea before build",
        "tools": ["system_shell"],
        "trigger": "spike, proof of concept, experiment",
    },
    "systematic-debugging": {
        "name": "systematic-debugging",
        "description": "4-phase root cause debugging: understand bugs before fixing",
        "tools": ["system_read_file", "system_shell"],
        "trigger": "debug, root cause, bug fix",
    },
    "test-driven-development": {
        "name": "test-driven-development",
        "description": "TDD: enforce RED-GREEN-REFACTOR, tests before code",
        "tools": ["system_shell", "system_write_file"],
        "trigger": "tdd, test driven, red green refactor",
    },
    "vite-react-ts-scaffold": {
        "name": "vite-react-ts-scaffold",
        "description": "Scaffold a Vite React TypeScript Tailwind web app",
        "tools": ["system_shell"],
        "trigger": "scaffold vite react tailwind",
    },

    # bountyforge
    "bb-methodology": {
        "name": "bb-methodology",
        "description": "The 3rd eye for pentesting: understand deeper attack surface",
        "tools": ["web_search", "web_fetch", "system_write_file"],
        "trigger": "bug bounty methodology, pentest, attack surface",
    },
    "bug-bounty": {
        "name": "bug-bounty",
        "description": "Complete bug bounty workflow: recon, triage, report writing",
        "tools": ["web_search", "web_fetch", "system_shell", "system_write_file"],
        "trigger": "bug bounty, bounty, security research",
    },
    "code-sleuth": {
        "name": "code-sleuth",
        "description": "Analyze EVM smart contracts for storage-safety vulnerabilities",
        "tools": ["system_shell", "system_read_file"],
        "trigger": "evm contract, solidity audit, storage safety",
    },
    "fizz": {
        "name": "fizz",
        "description": "Generate Echidna/Medusa-compatible Solidity fuzz suites",
        "tools": ["system_shell", "system_write_file"],
        "trigger": "fuzz testing, echidna, medusa, solidity",
    },
    "hackenproof-triage-marketplace": {
        "name": "hackenproof-triage-marketplace",
        "description": "HackenProof bug bounty triage workflow for Claude Code",
        "tools": ["web_search", "system_write_file"],
        "trigger": "hackenproof, triage, marketplace",
    },
    "meme-coin-audit": {
        "name": "meme-coin-audit",
        "description": "Meme coin and token security audit: rug pull detection",
        "tools": ["system_shell", "system_read_file", "web_fetch"],
        "trigger": "meme coin audit, token security, rug pull",
    },
    "report-writing": {
        "name": "report-writing",
        "description": "Bug bounty report writing for H1/Bugcrowd/Intigriti/Immunefi",
        "tools": ["system_write_file", "web_search"],
        "trigger": "bug bounty report, security report, write report",
    },
    "security-arsenal": {
        "name": "security-arsenal",
        "description": "Security payloads, bypass tables, wordlists, gf patterns",
        "tools": ["system_read_file", "system_write_file"],
        "trigger": "payloads, bypass, wordlist, gf patterns",
    },
    "smart-contract-audit": {
        "name": "smart-contract-audit",
        "description": "Comprehensive smart contract security audit framework",
        "tools": ["system_shell", "system_read_file"],
        "trigger": "smart contract audit, solidity audit, security audit",
    },
    "triage-validation": {
        "name": "triage-validation",
        "description": "Finding validation before writing any report: 7-question filter",
        "tools": ["web_fetch", "system_write_file"],
        "trigger": "triage, validate finding, 7 questions",
    },
    "web2-recon": {
        "name": "web2-recon",
        "description": "Web2 recon pipeline: subdomain enum, URL crawling, JS analysis",
        "tools": ["web_search", "web_fetch", "system_shell", "system_write_file"],
        "trigger": "web2 recon, subdomain, url crawl, js analysis",
    },
    "web2-vuln-classes": {
        "name": "web2-vuln-classes",
        "description": "Complete reference for 28 web2 bug classes with root causes",
        "tools": ["web_search", "web_fetch"],
        "trigger": "web2 vulnerability, vuln class, xss csrf",
    },
    "web3-audit": {
        "name": "web3-audit",
        "description": "Smart contract security audit: 10 DeFi bug classes",
        "tools": ["system_shell", "system_read_file"],
        "trigger": "web3 audit, defi audit, smart contract",
    },

    # web3
    "web3-ai-tools": {
        "name": "web3-ai-tools",
        "description": "AI-powered tools for Web3 bug bounty automation",
        "tools": ["web_search", "web_fetch"],
        "trigger": "web3 ai, automation, blockchain",
    },
    "web3-bug-classes": {
        "name": "web3-bug-classes",
        "description": "Complete reference for all 10 DeFi smart contract bug classes",
        "tools": ["web_search"],
        "trigger": "defi bug class, reentrancy, oracle manip",
    },
    "web3-case-study-role-misconfig": {
        "name": "web3-case-study-role-misconfig",
        "description": "Case study: role misconfiguration bug class applied to a contract",
        "tools": ["system_read_file"],
        "trigger": "role misconfig, access control, case study",
    },
    "web3-grep-arsenal": {
        "name": "web3-grep-arsenal",
        "description": "Master grep command arsenal for Web3 smart contract audit",
        "tools": ["system_shell"],
        "trigger": "grep solidity, contract analysis, search code",
    },
    "web3-hunt-foundation": {
        "name": "web3-hunt-foundation",
        "description": "Hunter mindset, recon setup, target scoring for Web3 hunts",
        "tools": ["web_search"],
        "trigger": "web3 hunt, recon, target scoring",
    },
    "web3-hunt-zksync-era": {
        "name": "web3-hunt-zksync-era",
        "description": "ZKsync Era Immunefi completed hunt -- 0 findings after exhaustive search",
        "tools": ["system_read_file", "web_fetch"],
        "trigger": "zksync era, immunefi, hunt report",
    },
    "web3-methodology-research": {
        "name": "web3-methodology-research",
        "description": "External research synthesis: Trail of Bits, SlowMist, etc",
        "tools": ["web_search", "web_fetch"],
        "trigger": "research synthesis, trail of bits, slowmist",
    },
    "web3-poc-foundry": {
        "name": "web3-poc-foundry",
        "description": "Complete Foundry PoC writing guide + all cheatcodes + DeFi patterns",
        "tools": ["system_shell", "system_read_file", "web_search"],
        "trigger": "foundry poc, cheatcode, proof of concept",
    },
    "web3-solidity-audit-mcp": {
        "name": "web3-solidity-audit-mcp",
        "description": "MCP server integrating Slither + Aderyn + SWC patterns",
        "tools": ["system_shell"],
        "trigger": "mcp server, slither, aderyn, swc",
    },
    "web3-start-here": {
        "name": "web3-start-here",
        "description": "Master index for Web3 smart contract security knowledge",
        "tools": ["web_search", "web_fetch"],
        "trigger": "web3 start here, index, knowledge base",
    },
    "web3-triage-report": {
        "name": "web3-triage-report",
        "description": "Bug triage validation system, Immunefi report format",
        "tools": ["system_write_file", "web_search"],
        "trigger": "triage report, immunefi format, bug report",
    },

    # web2
    "blocked-page-recovery": {
        "name": "blocked-page-recovery",
        "description": "Use when a fetch fails: 403/429, paywall, WAF, bot wall",
        "tools": ["web_fetch", "system_shell"],
        "trigger": "403 blocked, paywall, WAF, bot wall",
    },
    "web-spa-scraping": {
        "name": "web-spa-scraping",
        "description": "Use when scraping SPAs. Extract data via internal APIs",
        "tools": ["web_fetch", "system_shell"],
        "trigger": "spa scraping, api extraction, javascript site",
    },

    # research
    "arxiv": {
        "name": "arxiv",
        "description": "Search arXiv papers by keyword, author, category, or ID",
        "tools": ["web_search"],
        "trigger": "arxiv paper search, academic paper",
    },
    "competitor-news-monitor": {
        "name": "competitor-news-monitor",
        "description": "Watch named companies for material news; cited digests",
        "tools": ["web_search", "system_write_file"],
        "trigger": "competitor news, company watch, monitor",
    },
    "grounded-citations": {
        "name": "grounded-citations",
        "description": "Ground answers and documents in cited, verifiable sources",
        "tools": ["web_search", "web_fetch", "system_write_file"],
        "trigger": "citations, grounded answers, references",
    },
    "llm-wiki": {
        "name": "llm-wiki",
        "description": "Karpathy's LLM Wiki: build/query interlinked markdown KB",
        "tools": ["system_shell", "system_read_file", "system_write_file"],
        "trigger": "llm wiki, knowledge base, markdown kb",
    },

    # productivity
    "airtable": {
        "name": "airtable",
        "description": "Airtable REST API via curl. Records CRUD, filters, upserts",
        "tools": ["system_shell"],
        "trigger": "airtable crud, airtable api",
    },
    "box": {
        "name": "box",
        "description": "Box manages cloud files, sharing, search, and metadata",
        "tools": ["web_fetch", "system_shell"],
        "trigger": "box file management, box cloud",
    },
    "career-artifacts": {
        "name": "career-artifacts",
        "description": "Create resumes or portfolios. Optimizes for ATS",
        "tools": ["system_write_file"],
        "trigger": "resume, portfolio, career, ats",
    },
    "document-to-action-items": {
        "name": "document-to-action-items",
        "description": "Extract cited obligations, deadlines, tasks from documents",
        "tools": ["system_read_file", "system_write_file"],
        "trigger": "action items, extract tasks, obligations",
    },
    "meeting-action-items": {
        "name": "meeting-action-items",
        "description": "Turn meeting notes into cited decisions, owners, tickets",
        "tools": ["system_read_file", "system_write_file"],
        "trigger": "meeting notes, action items, decisions",
    },
    "modular-content-delivery": {
        "name": "modular-content-delivery",
        "description": "Use when generating content suites. Incremental delivery",
        "tools": ["system_write_file"],
        "trigger": "content suite, modular, incremental delivery",
    },
    "notion": {
        "name": "notion",
        "description": "Notion API + ntn CLI: pages, databases, markdown, Workers",
        "tools": ["system_shell"],
        "trigger": "notion api, notion page, ntn",
    },
    "math-md-to-pdf": {
        "name": "math-md-to-pdf",
        "description": "Math Markdown to print-ready PDF offline via Brave + MathML",
        "tools": ["system_shell"],
        "trigger": "math pdf, markdown to pdf, latex",
    },
    "maps": {
        "name": "maps",
        "description": "Geocode, POIs, routes, timezones via OpenStreetMap/OSRM",
        "tools": ["web_search"],
        "trigger": "geocode, map, route, poi, timezone",
    },
    "product-price-monitor": {
        "name": "product-price-monitor",
        "description": "Watch product, flight, or listing prices; alert on target",
        "tools": ["web_search", "system_write_file"],
        "trigger": "price monitor, track price, alert",
    },
    "teams-meeting-pipeline": {
        "name": "teams-meeting-pipeline",
        "description": "Teams meeting summaries, job replay, Graph subscriptions",
        "tools": ["web_search", "system_shell"],
        "trigger": "teams meeting, graph api, teams summary",
    },
    "weekly-review-planning": {
        "name": "weekly-review-planning",
        "description": "Weekly reset: commitments, stalled work, next-week plan",
        "tools": ["system_write_file"],
        "trigger": "weekly review, weekly plan, reset",
    },

    # publish
    "publish-artifacts": {
        "name": "publish-artifacts",
        "description": "Push local files to GitHub when user says push to github",
        "tools": ["system_shell"],
        "trigger": "push to github, publish github, repo",
    },
    "ship-project": {
        "name": "ship-project",
        "description": "Ship a complete project to GitHub: README, deps, source",
        "tools": ["system_shell", "system_read_file", "system_write_file"],
        "trigger": "ship project, github publish, complete project",
    },

    # media
    "gif-search": {
        "name": "gif-search",
        "description": "Search/download GIFs from Tenor via curl + jq",
        "tools": ["system_shell"],
        "trigger": "gif search, tenor, download gif",
    },
    "youtube-content": {
        "name": "youtube-content",
        "description": "YouTube transcripts to summaries, threads, blogs",
        "tools": ["web_fetch", "system_write_file"],
        "trigger": "youtube transcript, summarize video, youtube content",
    },

    # email
    "email-inbox-triage": {
        "name": "email-inbox-triage",
        "description": "Triage an inbox: prioritize threads, draft replies safely",
        "tools": ["email_list", "email_read", "email_search"],
        "trigger": "inbox triage, email priority, draft reply",
    },
    "himalaya": {
        "name": "himalaya",
        "description": "Himalaya CLI: IMAP/SMTP email from terminal",
        "tools": ["email_list", "email_send", "email_read", "email_search"],
        "trigger": "himalaya email, imap smtp, terminal email",
    },

    # hyperframes
    "hyperframes": {
        "name": "hyperframes",
        "description": "Mandatory entry point for HyperFrames requests",
        "tools": ["system_shell"],
        "trigger": "hyperframes, video composition, animation",
    },
    "hyperframes-animation": {
        "name": "hyperframes-animation",
        "description": "All animation knowledge for HyperFrames: atomic motion rules",
        "tools": ["system_shell", "system_write_file"],
        "trigger": "animation, motion design, hyperframes animation",
    },
    "hyperframes-audio": {
        "name": "hyperframes-audio",
        "description": "Use when audio already placed in a HyperFrames composition",
        "tools": ["system_shell"],
        "trigger": "hyperframes audio, audio placement",
    },
    "hyperframes-cli": {
        "name": "hyperframes-cli",
        "description": "HyperFrames CLI development loop: init, add, catalog",
        "tools": ["system_shell"],
        "trigger": "hyperframes cli, init project",
    },
    "hyperframes-core": {
        "name": "hyperframes-core",
        "description": "The HyperFrames composition contract: build renderable video",
        "tools": ["system_write_file"],
        "trigger": "hyperframes core, composition contract",
    },
    "hyperframes-creative": {
        "name": "hyperframes-creative",
        "description": "Non-animation creative direction for HyperFrames videos",
        "tools": ["system_write_file"],
        "trigger": "hyperframes creative, video direction",
    },
    "hyperframes-keyframes": {
        "name": "hyperframes-keyframes",
        "description": "HyperFrames composition needs punch-in, punch-out keyframes",
        "tools": ["system_write_file"],
        "trigger": "keyframes, punch-in, punch-out",
    },
    "hyperframes-registry": {
        "name": "hyperframes-registry",
        "description": "Search, install, wire registry blocks and components",
        "tools": ["system_shell", "web_fetch"],
        "trigger": "registry, install block, hyperframes component",
    },
    "hyperframes-studio": {
        "name": "hyperframes-studio",
        "description": "Use when building or editing a HyperFrames project",
        "tools": ["system_shell", "system_write_file"],
        "trigger": "hyperframes studio, edit project",
    },

    # higgsfield
    "higgsfield-brandkit": {
        "name": "higgsfield-brandkit",
        "description": "Create and extend complete visual brand systems through the tool",
        "tools": ["system_shell"],
        "trigger": "brandkit, brand system, visual identity",
    },
    "higgsfield-generate": {
        "name": "higgsfield-generate",
        "description": "Generate images/videos/3D assets/audio via Higgsfield AI",
        "tools": ["system_shell"],
        "trigger": "higgsfield generate, image video 3d audio",
    },
    "higgsfield-marketplace-cards": {
        "name": "higgsfield-marketplace-cards",
        "description": "Generate marketplace product image cards through Higgsfield",
        "tools": ["system_shell"],
        "trigger": "marketplace card, product image card",
    },
    "higgsfield-product-photoshoot": {
        "name": "higgsfield-product-photoshoot",
        "description": "Generate brand-quality product images through Higgsfield",
        "tools": ["system_shell"],
        "trigger": "product photoshoot, product image",
    },
    "higgsfield-soul-id": {
        "name": "higgsfield-soul-id",
        "description": "Train a Soul Character: personalized model on a person",
        "tools": ["system_shell"],
        "trigger": "soul id, train a character, soul character",
    },
    "higgsfield-video-explainer": {
        "name": "higgsfield-video-explainer",
        "description": "Build a complete non-photoreal narrated explainer or story",
        "tools": ["system_shell", "system_write_file"],
        "trigger": "video explainer, narrated video, explainer",
    },
    "higgsfield-websites": {
        "name": "higgsfield-websites",
        "description": "Build, edit, and deploy full-stack websites, apps and games",
        "tools": ["system_shell", "system_write_file"],
        "trigger": "higgsfield website, full-stack site, deploy",
    },
    "higgsfield-youtube-thumbnail": {
        "name": "higgsfield-youtube-thumbnail",
        "description": "Create high-click-through YouTube thumbnails and vertical",
        "tools": ["system_shell"],
        "trigger": "youtube thumbnail, thumbnail design",
    },
}


def get_skill(name: str) -> dict | None:
    return SKILLS.get(name)


VOID_SKILLS_DIR = Path(
    os.environ.get("VOID_SKILLS_DIR", Path.home() / ".void" / "skills")
)


def find_skill_md(name: str) -> Path | None:
    """Locate a skill's real SKILL.md on disk.

    Checks both layouts Void supports: <dir>/<name>/SKILL.md (vendored) and
    <dir>/<name>.md (flat installs).
    """
    if not VOID_SKILLS_DIR.exists():
        return None
    nested = VOID_SKILLS_DIR / name / "SKILL.md"
    if nested.exists():
        return nested
    flat = VOID_SKILLS_DIR / f"{name}.md"
    if flat.exists():
        return flat
    for p in VOID_SKILLS_DIR.rglob("SKILL.md"):
        if p.parent.name == name:
            return p
    return None


def load_skill_content(name: str) -> str | None:
    """Full SKILL.md body for a catalog skill, or None if not on disk."""
    p = find_skill_md(name)
    if not p:
        return None
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return None


def match_skills(query: str) -> list[dict]:
    """Find skills matching a query by name, description, or trigger."""
    q = query.lower()
    results = []
    for skill in SKILLS.values():
        if (q in skill["name"].lower()
            or q in skill["description"].lower()
            or q in skill["trigger"].lower()):
            results.append(skill)
    return results