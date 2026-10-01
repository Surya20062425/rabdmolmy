"""Void theme — exact Hermes Agent terminal look.

Layout (per the screenshot):
- VOID logo: absolute top-left, outside/above the main box.
- Left column (~1/4 width): big S logo, then system info lines.
- Main content box (~3/4 width, to the right of left column):
    version header
    Available Tools (bright blue header)
    Available Skills (bright blue header)
    summary line
    warning line
    welcome line
    tip line
    status bar:  ❯ void-cli | ctxx — [████████] — 1s 🟢0s
    user input:  > Research this topic and write me a brief

Colors: neon green #00ff41 on black, bright blue #00bfff headers,
        white body, grey muted, red warning.
Background: faint Matrix-style 0/1 binary rain (optional, off by default).
"""


from __future__ import annotations

import os
import random
import time
from typing import List

from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.style import Style


# ═════════════════════════════════════════════════════════════════════
# PALETTE
# ═════════════════════════════════════════════════════════════════════

ANSI_GREEN = "\033[38;2;0;255;65m"     # #00ff41
ANSI_BLUE = "\033[38;2;0;191;255m"     # #00bfff
ANSI_WHITE = "\033[38;2;224;224;224m"  # #e0e0e0
ANSI_GREY = "\033[38;2;136;136;136m"   # #888888
ANSI_RED = "\033[38;2;255;51;51m"      # #ff3333
ANSI_RESET = "\033[0m"
ANSI_BOLD = "\033[1m"
ANSI_DIM = "\033[2m"


# ═════════════════════════════════════════════════════════════════════
# COLOR HELPERS
# ═════════════════════════════════════════════════════════════════════


def g(text: str) -> str:           # green
    return f"{ANSI_GREEN}{text}{ANSI_RESET}"


def gb(text: str) -> str:          # green bold
    return f"{ANSI_BOLD}{ANSI_GREEN}{text}{ANSI_RESET}"


def gd(text: str) -> str:          # green dim
    return f"{ANSI_DIM}{ANSI_GREEN}{text}{ANSI_RESET}"


def b(text: str) -> str:           # blue
    return f"{ANSI_BLUE}{text}{ANSI_RESET}"


def bb(text: str) -> str:          # blue bold
    return f"{ANSI_BOLD}{ANSI_BLUE}{text}{ANSI_RESET}"


def w(text: str) -> str:           # white
    return f"{ANSI_WHITE}{text}{ANSI_RESET}"


def gr(text: str) -> str:          # grey
    return f"{ANSI_GREY}{text}{ANSI_RESET}"


def grd(text: str) -> str:         # grey dim
    return f"{ANSI_DIM}{ANSI_GREY}{text}{ANSI_RESET}"


def r(text: str) -> str:           # red
    return f"{ANSI_RED}{text}{ANSI_RESET}"


# ═════════════════════════════════════════════════════════════════════
# SYMBOLS
# ═════════════════════════════════════════════════════════════════════

CHECK = "\u2713"
CROSS = "\u2717"
BLOCK = "\u2588"            # █
TRIANGLE = "\u26a0"         # ⚠
LIGHTBULB = "\U0001f4a1"    # 💡
BULLET = "\u2022"
DASH = "\u2014"
CIRCLE = "\u25cf"
ARROW_RIGHT = "\u276f"      # ❯  — the prompt char in the screenshot

# box-drawing
TL = "\u250c"   # ┌
TR = "\u2510"   # ┐
BL = "\u2514"   # └
BR = "\u2518"   # ┘
H = "\u2500"    # ─
V = "\u2502"    # │


# ═════════════════════════════════════════════════════════════════════
# PIXEL LOGOS — VOID and S
# ═════════════════════════════════════════════════════════════════════

# Each letter is a 5-wide x 7-tall cell grid.


def _pixel_v() -> List[str]:
    return [
        "V   V",
        "V   V",
        "V   V",
        " V V ",
        "  V  ",
        "  V  ",
        "  V  ",
    ]


def _pixel_o() -> List[str]:
    return [
        " OOO ",
        "O   O",
        "O   O",
        "O   O",
        "O   O",
        "O   O",
        " OOO ",
    ]


def _pixel_i() -> List[str]:
    return [
        " III ",
        "  I  ",
        "  I  ",
        "  I  ",
        "  I  ",
        "  I  ",
        " III ",
    ]


def _pixel_d() -> List[str]:
    return [
        " DD  ",
        "D  D ",
        "D  D ",
        "D  D ",
        "D  D ",
        "D  D ",
        " DD  ",
    ]


def _pixel_s() -> List[str]:
    """Big S logo — same pixel font as VOID letters."""
    return [
        " SSSS ",
        "S    S",
        "S     ",
        " SSSS ",
        "     S",
        "S    S",
        " SSSS ",
    ]


def _pad(cell: str, width: int) -> str:
    return cell.ljust(width)


def _glitch(cell: str) -> str:
    """One-column-right offset for the shadow layer behind each logo."""
    return " " + cell[:-1]


def logo_void() -> str:
    """Pixelated VOID — 5x7 cells per letter, dim shadow behind each row."""
    cols = (_pixel_v(), _pixel_o(), _pixel_i(), _pixel_d())
    w = max(len(c[0]) for c in cols)
    lines: List[str] = []
    for row in range(7):
        shadow: List[str] = []
        main: List[str] = []
        for col in cols:
            cell = col[row]
            shadow.append(_pad(_glitch(cell), w) + " ")
            main.append(_pad(cell, w) + " ")
        lines.append(gd("".join(shadow).rstrip()))
        lines.append(gb("".join(main).rstrip()))
    return "\n".join(lines)


def logo_big_s() -> str:
    """Big standalone S logo — same pixel style as VOID letters."""
    w = len(_pixel_s()[0])
    lines: List[str] = []
    for row in range(7):
        cell = _pixel_s()[row]
        lines.append(gd(_pad(_glitch(cell), w)))
        lines.append(gb(_pad(cell, w)))
    return "\n".join(lines)


# ═════════════════════════════════════════════════════════════════════
# MATRIX RAIN — subtle 0/1 binary, green, off by default
# ═════════════════════════════════════════════════════════════════════


class MatrixRain:
    """Falls faint 0/1 raindrops down the screen.

    Off by default. Use `rain.animate()` only for a full-screen splash;
    normal terminal use should print the rain behind the UI without
    clearing every frame.
    """

    CHARS = "01"

    def __init__(self, width: int = 80, height: int = 25):
        self.width = width
        self.height = height
        self.columns = [random.randint(-20, -1) for _ in range(width)]
        self.chars = [random.choice(self.CHARS) for _ in range(width)]

    def frame(self) -> str:
        lines: List[str] = []
        for row in range(self.height):
            cells: List[str] = []
            for col in range(self.width):
                if row >= self.columns[col]:
                    if row == self.columns[col]:
                        cells.append(g(self.chars[col]))
                    else:
                        cells.append(gd(self.chars[col]))
                else:
                    cells.append(" ")
            lines.append("".join(cells))
        for col in range(self.width):
            self.columns[col] += 1
            if self.columns[col] > self.height:
                self.columns[col] = random.randint(-20, -1)
                self.chars[col] = random.choice(self.CHARS)
        return "\n".join(lines)

    def animate(self, frames: int = 100, interval: float = 0.05):
        """Full-screen rain animation; clears screen each frame."""
        import sys
        for _ in range(frames):
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.write(self.frame())
            sys.stdout.flush()
            time.sleep(interval)


# ═════════════════════════════════════════════════════════════════════
# CLIPBOARD DATA — exact strings from the screenshot
# ═════════════════════════════════════════════════════════════════════

TOOLS_LINES = [
    "browser: browser_back, browser_click, ...",
    "browseruse: browser_exec",
    "clarify: clarify",
    "code_execution: execute_code",
    "delegation: delegate_task",
    "file: patch, read_file, search_files, write_file",
    "image_gen: image_generate",
    "kanban: kanban_attach, kanban_attach_url, ...",
    "(and 6 more toolsets...)",
]

SKILLS_LINES = [
    "Void CLI:          claude-code, codex, computer-use, hermes-agent, +12 more",
    "bountyforge:       bb-methodology, bug-bounty, code-sleuth, fizz, fizz-convert, +24 more",
    "creative:          architecture-diagram, ascii-video, banner-design, +14 more",
    "devops:            sdlc-review, velcel-deploy-fullstack",
    "email:             smail-inbox-triage, himalaya",
    "general:           bountyforge, brag, hermes-plugins, higgsfield-brandkit, +23 more",
    "media:             gif-search, songsee, youtube-content",
    "note-taking:       obsidian",
    "productivity:      airtable, tex, career-artifacts, document-to-action-items, +14 more",
    "research:          arxiv, competitor-news-monitor, grounded-citations, llm-wiki",
    "sih:               sih-architecture-generator, sih-debug-and-patch, +3 more",
    "software-development: cli-agent-python, codebase-inspection, dogfood, +11 more",
    "web:               blocked-page-recovery, web-spa-scraping",
]

VERSION_HEADER = (
    "Void CLI v0.0.21.0 (2026.8.31) - Upstream lad2eble - local 79445a49 (+1 carried commit)"
)

SUMMARY_LINE = "18 tools · 130 skills · ./help for commands"

WARNING_LINE = "14525 commits behind - run hermes update to update"

WELCOME_LINE = "Welcome to Hermes Agent! Type your message or /help for commands."

TIP_LINE = (
    "Tip: Hermes curator rollback restores shrills from a pre-run snapshot"
    " - backups live under shrills/.curator_backups/."
)

SYSTEM_MODEL = "solar-pro4:free ~ Nous Research"
SYSTEM_CWD = r"C:\Users\b7993"
SYSTEM_SESSION = "Session: 20261001_020526_1ee39d"


# ═════════════════════════════════════════════════════════════════════
# SECTION BUILDERS
# ═════════════════════════════════════════════════════════════════════


def section(title: str) -> str:
    """Bright blue bold section header, exactly like the screenshot."""
    return bb(f"  {title}")


def tools_block() -> List[str]:
    out: List[str] = [section("Available Tools")]
    out.extend(f"  {ln}" for ln in TOOLS_LINES)
    return out


def skills_block() -> List[str]:
    out: List[str] = [section("Available Skills")]
    out.extend(f"  {ln}" for ln in SKILLS_LINES)
    return out


def center_lines() -> List[str]:
    """All body lines that go inside the main bordered box."""
    out: List[str] = []
    out.append(w(VERSION_HEADER))
    out.append("")
    out.extend(tools_block())
    out.append("")
    out.extend(skills_block())
    out.append("")
    out.append(w(SUMMARY_LINE))
    out.append("")
    out.append(r(TRIANGLE + "  " + WARNING_LINE))
    out.append("")
    out.append(w(WELCOME_LINE))
    out.append("")
    out.append(w(LIGHTBULB + " " + TIP_LINE))
    out.append("")
    out.append(status_bar())
    out.append("")
    out.append(input_line())
    return out


def left_column() -> List[str]:
    """The left column: big S logo then system info, all green."""
    out: List[str] = []
    out.append(logo_big_s())
    out.append("")
    out.append(g(SYSTEM_MODEL))
    out.append(g(gr(SYSTEM_CWD)))
    out.append(g(gr(SYSTEM_SESSION)))
    return out


# ═════════════════════════════════════════════════════════════════════
# BOX WRAPPING — thin green border around a list of pre-colored lines
# ═════════════════════════════════════════════════════════════════════


def _visible_len(s: str) -> int:
    """Length of s after stripping ANSI escape codes."""
    out = []
    in_code = False
    for ch in s:
        if ch == "\033" and not in_code:
            in_code = True
        elif ch == "m" and in_code:
            in_code = False
        elif not in_code:
            out.append(ch)
    return len("".join(out))


def box(lines: List[str], pad: int = 1) -> str:
    """Draw a thin green box around `lines`.

    Each line in `lines` is already a complete ANSI-colored string.
    Width = max visible length + 2*pad.
    """
    vis = [_visible_len(l) for l in lines]
    inner = max(vis) + pad * 2
    top = g(TL + H * (inner - 2) + TR)
    bot = g(BL + H * (inner - 2) + BR)
    vert = g(V)
    body: List[str] = []
    for line, vl in zip(lines, vis):
        right_pad = max(0, inner - 2 - vl)
        body.append(f"{vert} {line}{' ' * right_pad} {vert}")
    return f"\n{top}\n" + "\n".join(body) + f"\n{bot}\n"


# ═════════════════════════════════════════════════════════════════════
# STATUS BAR — exact string from the screenshot
# ═════════════════════════════════════════════════════════════════════
#
#   ❯ void-cli | ctxx — [████████] — 1s 🟢0s
#
# Breakout:
#   ❯ space void-cli space | space ctxx space — space [████] space — space 1s space 🟢0s
#


GREEN_CIRCLE = "\U0001f7e2"
BAR_EMPTY = "\u2591"


def status_bar(
    ctx: str = "ctxx",
    progress: float = 1.0,
    latency_s: float = 1.0,
) -> str:
    """Exact status bar matching the screenshot:
    ❯ void-cli | ctxx — [████████] — 1s 🟢0s"""
    width = 8
    filled = int(progress * width)
    bar = g("[" + BLOCK * filled + BAR_EMPTY * (width - filled) + "]")
    return (
        f"{gb(ARROW_RIGHT)} {gb('void-cli')}"
        f"{gr(' | ' + ctx + ' — ')}"
        f"{bar}"
        f"{gr(' — ' + str(int(round(latency_s))) + 's ')}"
        f"{g(GREEN_CIRCLE)}{gr('0s')}"
    )


# ═════════════════════════════════════════════════════════════════════
# INPUT LINE — user's typed query
# ═════════════════════════════════════════════════════════════════════


def input_line(text: str = "Research this topic and write me a brief") -> str:
    """User input line: green > prompt, white text, block cursor at end."""
    return f"{g('>')} {w(text + ' ')}{g(BLOCK)}"


# ═════════════════════════════════════════════════════════════════════
# START SCREEN — full composite
# ═════════════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════════
# RICH-BASED START SCREEN — exact void interface layout
# ═══════════════════════════════════════════════════════════════════

M_GREEN = "#00FF66"
M_BG = "#030A05"
M_BORDER = "#00DD55"
M_CYAN = "#00E5FF"
M_WHITE = "#E0E0E0"
M_MUTED = "#005522"
M_RED = "#FF3344"


def _rich_base() -> Style:
    return Style(color=M_GREEN, bgcolor=M_BG)


def _rich_title() -> str:
    return (
        f"[{M_GREEN} bold]Void CLI v0.0.21.0 (2026.8.31)[/{M_GREEN} bold]"
        f"- [{M_WHITE}]Upstream lad2eble - local 79445a49 ([/{M_WHITE}]"
        f"[{M_GREEN}]→1 carried commit[/{M_GREEN}])"
    )


def _left_column() -> Text:
    t = Text(style=_rich_base())
    t.append(
        "  ██╗   ██╗ ██████╗ ██╗██████╗ \n"
        "  ██║   ██║██╔═══██╗██║██╔══██╗\n"
        "  ██║   ██║██║   ██║██║██║  ██║\n"
        "  ╚██╗ ██╔╝██║   ██║██║██║  ██║\n"
        "   ╚████╔╝ ╚██████╔╝██║██████╔╝\n"
        "    ╚═══╝   ╚═════╝ ╚═╝╚═════╝\n\n",
        style=Style(color=M_GREEN, bold=True),
    )
    t.append(
        "      .-----------------.\n"
        "     /  .--------------. \\\n"
        "    |  /   .--------.   \\ |\n"
        "    | |   /  .----.  \\   '|\n"
        "    | |  |  /      '--'   |\n"
        "    |  \\  \\  `-----.      |\n"
        "     \\  `--`-----.  \\     |\n"
        "      `--------.  |  |    |\n"
        "     .--------. | |  |    |\n"
        "    |  .----.  \\| |  |    |\n"
        "    | |      \\   /  /     |\n"
        "    |  `------'  .-'     /\n"
        "     `----------'-------'\n\n",
        style=Style(color=M_GREEN, bold=True),
    )
    t.append("C:\\Users\\b7993\n", style=Style(color=M_GREEN))
    t.append("Session: 20261001_020526_lee39d\n", style=Style(color=M_GREEN))
    return t


# ═════════════════════════════════════════════════════════════════════
# STANDALONE HELPERS — for use outside start_screen()
# ═════════════════════════════════════════════════════════════════════


def prompt(text: str = "") -> str:
    """Standalone prompt: > text"""
    return f"{g('>')} {w(text)}"


def panel(title: str, lines: List[str]) -> str:
    """A single titled box (for Available Tools / Available Skills alone)."""
    return box([section(title)] + lines)


# ═════════════════════════════════════════════════════════════════════
# CLI COMPAT — keep the old void subcommand surface working
# ═════════════════════════════════════════════════════════════════════


def ok(text: str) -> str:
    return f"{gb(CHECK)} {w(text)}"


def warn(text: str) -> str:
    return f"{r(TRIANGLE + ' ')}{r(text)}"


def err(text: str) -> str:
    return f"{r(CROSS + ' ')}{r(text)}"


def banner(title: str = "VOID", subtitle: str = "/s — the CLI agent") -> str:
    width = 70
    top = g(TL + H * width + TR)
    mid = (
        f"{g(V)}  {gb(title)}  {gd(subtitle)}"
        f"{' ' * max(0, width - len(title) - len(subtitle) - 6)}{g(V)}"
    )
    bot = g(BL + H * width + BR)
    return f"{top}\n{mid}\n{bot}"


def logo_ascii() -> str:
    return logo_void()


# ═══════════════════════════════════════════════════════════════════
# RICH-BASED START SCREEN — exact void interface layout
# ═══════════════════════════════════════════════════════════════════

M_GREEN = "#00FF66"
M_BG = "#030A05"
M_BORDER = "#00DD55"
M_CYAN = "#00E5FF"
M_WHITE = "#E0E0E0"
M_MUTED = "#005522"
M_RED = "#FF3344"


def _rich_base() -> Style:
    return Style(color=M_GREEN, bgcolor=M_BG)


def _rich_title() -> str:
    return (
        f"[{M_GREEN} bold]Void CLI v0.0.21.0 (2026.8.31)[/{M_GREEN} bold]"
        f"- [{M_WHITE}]Upstream lad2eble - local 79445a49 ([/{M_WHITE}]"
        f"[{M_GREEN}]→1 carried commit[/{M_GREEN}])"
    )


def _left_column() -> Text:
    t = Text(style=_rich_base())
    t.append(
        "  ██╗   ██╗ ██████╗ ██╗██████╗ \n"
        "  ██║   ██║██╔═══██╗██║██╔══██╗\n"
        "  ██║   ██║██║   ██║██║██║  ██║\n"
        "  ╚██╗ ██╔╝██║   ██║██║██║  ██║\n"
        "   ╚████╔╝ ╚██████╔╝██║██████╔╝\n"
        "    ╚═══╝   ╚═════╝ ╚═╝╚═════╝\n\n",
        style=Style(color=M_GREEN, bold=True),
    )
    t.append(
        "      .-----------------.\n"
        "     /  .--------------. \\\n"
        "    |  /   .--------.   \\ |\n"
        "    | |   /  .----.  \\   '|\n"
        "    | |  |  /      '--'   |\n"
        "    |  \\  \\  `-----.      |\n"
        "     \\  `--`-----.  \\     |\n"
        "      `--------.  |  |    |\n"
        "     .--------. | |  |    |\n"
        "    |  .----.  \\| |  |    |\n"
        "    | |      \\   /  /     |\n"
        "    |  `------'  .-'     /\n"
        "     `----------'-------'\n\n",
        style=Style(color=M_GREEN, bold=True),
    )
    t.append("C:\\Users\\b7993\n", style=Style(color=M_GREEN))
    t.append("Session: 20261001_020526_lee39d\n", style=Style(color=M_GREEN))
    return t


def _right_column() -> Text:
    t = Text(style=_rich_base())
    t.append("Available Tools\n", style=Style(color=M_CYAN, bold=True))
    for line in [
        "browser: browser_back, browser_click, ...",
        "browser-use: browser_exec",
        "clarify: clarify",
        "code_execution: execute_code",
        "delegation: delegate_task",
        "file: patch, read_file, search_files, write_file",
        "image_gen: image_generate",
        "kanban: kanban_attach, kanban_attach_url, ...",
        "(and 6 more toolsets...)",
    ]:
        t.append(line + "\n", style=Style(color=M_GREEN))
    t.append("\nAvailable Skills\n", style=Style(color=M_CYAN, bold=True))
    for line in [
        "Void CLI: claude-code, codex, computer-use, hermes-agent, +2 more",
        "bountyforge: bb-methodology, bug-bounty, code-sleuth, fizz, fizz-convert, +24 more",
        "creative: architecture-diagram, ascii-video, banner-design, +14 more",
        "devops: sdlc-review, vercel-deploy-fullstack",
        "email: smail-inbox-triage, himalaya",
        "general: bountyforge, brag, hermes-plugins, higgsfield-brandkit, +23 more",
        "media: gif-search, songsee, youtube-content",
        "note-taking: obsidian",
        "productivity: airtable, tex, career-artifacts, document-to-action-items, +14 more",
        "research: arxiv, competitor-news-monitor, grounded-citations, llm-wiki",
        "sih: sih-architecture-generator, sih-debug-and-patch, +3 more",
        "software-development: cli-agent-python, codebase-inspection, dogfood, +11 more",
        "web: blocked-page-recovery, web-spa-scraping",
    ]:
        t.append(line + "\n", style=Style(color=M_GREEN))
    t.append("\n", style=Style(color=M_GREEN))
    t.append("18 tools · 130 skills · /help for commands\n", style=Style(color=M_WHITE))
    return t


def start_screen() -> str:
    """Rich-based start screen — exact void interface layout."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.columns import Columns

    console = Console(color_system="truecolor")
    with console.capture() as cap:
        console.print(
            Panel(
                Columns([_left_column(), _right_column()], expand=True),
                title=_rich_title(),
                title_align="left",
                border_style=Style(color=M_BORDER),
                style=Style(bgcolor=M_BG),
            )
        )
    return cap.get()


def cmd_entry(cmd: str, desc: str | None = None, indent: int = 2) -> str:
    sp = " " * indent
    line = f"{sp}{g(ARROW_RIGHT)} {gb(cmd)}"
    if desc:
        line += f"  {gd(desc)}"
    return line


def bullet(text: str) -> str:
    return f"  {g(BULLET)} {w(text)}"


def section_divider() -> str:
    return gd(H * 70)


def divider(width: int = 70) -> str:
    return gd(H * width)


def header(text: str, level: int = 1) -> str:
    if level == 1:
        line = gb(H * 50)
        return f"\n{line}\n  {gb(text)}\n{line}\n"
    return f"\n{gb(text)}\n{gd(H * 40)}\n"


def tagged(label: str, value: str,
           label_color=None, value_color=None) -> str:
    l = label_color or g
    v = value_color or w
    return f"  {l('[' + label + ']')} {v(value)}"


def masked_api_key(key: str) -> str:
    if not key:
        return gr("(not set)")
    if len(key) > 8:
        return g(key[:4]) + gr("...") + g(key[-4:])
    return gr("***")


def symbol(text: str = "") -> str:
    return f"{gb('s')}{w(':')} {g(text)}"


def prompt_text(text: str) -> str:
    return f"{gb('s')}{w('>')}{w(' ' + text)}{ANSI_RESET}"


def table(headers: List[str],
          rows: List[List[str]],
          widths: List[int] | None = None) -> str:
    if widths is None:
        widths = [
            max(len(h), max((len(str(r[i])) for r in rows), default=0))
            for i, h in enumerate(headers)
        ]
    out: List[str] = []
    hdr_cells = [f"{h:^{w}}" for h, w in zip(headers, widths)]
    hdr_line = f"{g(V)} {'  '.join(hdr_cells)} {g(V)}"
    out.append(hdr_line)
    hlen = sum(widths) + 2 * len(widths) - 1
    out.append(g("\u251c" + H * hlen + "\u2524"))
    for row in rows:
        cells = [f"{str(c):<{w}}" for c, w in zip(row, widths)]
        out.append(f"{g(V)} {'  '.join(cells)} {g(V)}")
    out.append(g("\u2514" + H * hlen + "\u2518"))
    return "\n".join(out)


# backward-compat aliases
dim = grd
green = g
green_bold = gb
green_dim = gd
cyan = b
cyan_bold = bb
orange = r
orange_bold = lambda t: f"{ANSI_BOLD}{ANSI_RED}{t}{ANSI_RESET}"
BULLET_OLD = BULLET
ARROW_OLD = ARROW_RIGHT
CIRCLE_OLD = CIRCLE
BOX_DIV = H
BOX_VERT = V
BOX_TL = TL
BOX_TR = TR
BOX_BL = BL
BOX_BR = BR
BOX_L = V
BOX_T = H
DASH_ALT = DASH
GREEN_CIRCLE = "\U0001f7e2"
RED_CIRCLE = "\U0001f534"
GREEN_LINE = gd
CRIMSON = "\U0001f534"      # 🔴 — alias for red circle, keeps compat surface complete
VIOLET = "\U0001f534"       # 🔴 — placeholder: swap to #8b5cf6 when a true violet is needed

SYMBOL = "s"
CHECK_MARK = CHECK
CROSS_MARK = CROSS


def green_line(text: str) -> str:
    return gd(text)


def progress_bar(fraction: float, width: int = 20) -> str:
    filled = int(fraction * width)
    return g(BLOCK * filled + " " * (width - filled))


# Color preset registry — the five required swatches, plus any added later.
# Consumers can read this dict directly; the canonical hex source of truth is
# the ANSI_* constants above, which these hex strings must match.
COLOR_PRESETS: dict[str, dict[str, str]] = {
    "crimson": {
        "name": "Crimson",
        "hex": "#DC143C",
    },
    "violet": {
        "name": "Violet",
        "hex": "#8B5CF6",
    },
    "void_green": {
        "name": "Void Neon Green",
        "hex": "#00ff41",
    },
    "matrix_blue": {
        "name": "Matrix Bright Blue",
        "hex": "#00bfff",
    },
    "void_red": {
        "name": "Void Warning Red",
        "hex": "#ff3333",
    },
}


# ═════════════════════════════════════════════════════════════════════
# BACKWARD-COMPAT — old long names that cli.py and command modules import.
# The theme now uses short names (g, gb, w, gr, gd, r) internally; these
# aliases keep every existing import working without touching callers.
# ═════════════════════════════════════════════════════════════════════

green = g
green_bold = gb
white = w
grey = gr
green_dim = gd
dim = gd
red = r
orange = r
orange_bold = r
ARROW = ARROW_RIGHT
GREEN_CIRCLE = "\U0001F7E2"
RED_CIRCLE = "\U0001F534"
