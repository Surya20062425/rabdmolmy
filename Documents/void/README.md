# void — CLI agent

`/s` — the CLI agent. Hermes-equivalent surface, neon-green branding, full tool + skill + session + cron system.

## Structure

```
void/
├── agent.py           # Agent loop — model call → tool dispatch → round-trip
├── cli.py             # CLI entry point (argparse, all subcommands)
├── config.py          # Config (~/.void/config.json) — key/base_url/model
├── model.py           # OpenAI-format model client
├── sessions.py        # SQLite session store
├── providers.py       # Provider config + fallback chain
├── theme.py           # Terminal theme (neon green #9df133, DM Mono)
├── commands/
│   ├── model_cmd.py   # model list/set/show
│   ├── auth_cmd.py    # auth add/list/remove/status
│   ├── fallback_cmd.py# fallback chain commands
│   ├── sessions_cmd.py# session CRUD + export
│   ├── skills_cmd.py  # skill install/discover/search
│   └── cron_cmd.py    # scheduled jobs
└── tools/
    ├── registry.py    # Tool register + dispatch
    ├── system.py      # read/write/shell/ls/pwd/env
    ├── web.py         # fetch/extract/search (DuckDuckGo)
    └── example.py     # get_time demo
```

## Usage

```
void setup                          # walkthrough: key → base_url → model
void chat -q "what time is it?"     # chat with tool-calling loop
void config set api_key <key>       # set API key
void model list                     # show providers + models
void sessions list                  # browse sessions
void cron create 30m "what time is it"
```

## Requirements

Python >= 3.10, openai >= 1.0. No external tools.
