# void — CLI agent

`/s` — the CLI agent. Neon-green branding, full tool + skill + session + cron system.

## Structure

```
void/
├── agent.py           # Agent loop — model call → tool dispatch → round-trip
├── cli.py             # CLI entry point (argparse, all subcommands)
├── config.py          # Config (~/.void/config.json) — key/base_url/model
├── model.py           # OpenAI-format model client
├── sessions.py        # SQLite session store
├── providers.py       # Provider config + fallback chain
├── skills_catalog.py  # 101-skill catalog
├── theme.py           # Terminal theme (neon green #9df133, DM Mono)
├── commands/
│   ├── model_cmd.py   # model list/set/show
│   ├── auth_cmd.py    # auth add/list/remove/status
│   ├── fallback_cmd.py# fallback chain commands
│   ├── sessions_cmd.py# session CRUD + export
│   ├── skills_cmd.py  # skill install/discover/search/browse
│   └── cron_cmd.py    # scheduled jobs
└── tools/
    ├── registry.py    # Tool register + dispatch (auto-discovers tools/*.py)
    ├── system.py      # read/write/shell/ls/pwd/env
    ├── web.py         # fetch/extract/search (DuckDuckGo)
    ├── email.py       # list/read/send/search (IMAP/SMTP)
    ├── task.py        # task list/add/done/delete
    ├── session_tool.py# session search/read
    ├── memory_tool.py # memory list/add/remove
    ├── cronjob_tool.py# cronjob list/create/delete
    ├── process_tool.py# process list/start/stop
    └── example.py     # get_time demo
```

## Tools — 28 across 9 categories

| Category  | Tools |
|-----------|-------|
| system    | `system_read_file` `system_write_file` `system_shell` `system_ls` `system_pwd` `system_env_var` |
| web       | `web_fetch` `web_extract_text` `web_search` |
| email     | `email_list` `email_read` `email_send` `email_search` |
| task      | `task_list` `task_add` `task_done` `task_delete` |
| session   | `session_search` `session_read` |
| memory    | `memory_list` `memory_add` `memory_remove` |
| cronjob   | `cronjob_list` `cronjob_create` `cronjob_delete` |
| process   | `process_list` `process_start` `process_stop` |
| misc      | `get_time` |

## Skills — 101 in catalog

`void/skills_catalog.py` holds the Void skill catalog: void-core, devops, creative, UI/UX,
software-development, bountyforge, web3, web2, research, productivity, publish, media, email,
hyperframes, higgsfield. Skills are injected into the system prompt when the user's message
matches a skill trigger.

```
void skills browse             # list all 101 skills by category
void skills search vercel      # search installed + catalog
void skills list               # installed skills only
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

## Tests

```
python test_surface.py     # tools registered, schemas valid, catalog, skill injection
python test_imports.py     # theme + import sanity
python -m void.agent       # agent-loop self-check (mocked model)
```
