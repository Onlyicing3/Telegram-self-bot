# LifeOS — Telegram Self-Bot & LifeOS System

Production-ready, headless Telegram userbot optimized for Render Free tier.

---

## Pre-Deploy: Generate SESSION_STRING

You must generate a Pyrogram/Telethon `StringSession` **once** on your local machine.
Run the helper script below — it handles the interactive 2FA prompt, then exits:

```bash
pip install telethon
python -c "
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
import os

api_id   = int(input('API_ID: '))
api_hash = input('API_HASH: ')

with TelegramClient(StringSession(), api_id, api_hash) as client:
    print('\\n--- SESSION_STRING ---')
    print(client.session.save())
    print('--- copy the line above ---')
"
```

Copy the output string and paste it as the `SESSION_STRING` environment variable on Render.

---

## Environment Variables (Render Dashboard)

| Variable | Required | Description |
|---|---|---|
| `API_ID` | Yes | Telegram API ID from my.telegram.org |
| `API_HASH` | Yes | Telegram API Hash from my.telegram.org |
| `SESSION_STRING` | Yes | Generated StringSession (see above) |
| `BOT_OWNER_ID` | Yes | Your Telegram numeric user ID |
| `SUPABASE_URL` | No | Supabase project URL (optional — in-memory fallback) |
| `SUPABASE_SERVICE_ROLE_KEY` | No | Supabase service role key (optional) |
| `DATABASE_URL` | No | PostgreSQL connection string (backup) |
| `TZ` | No | Timezone — defaults to `Asia/Tehran` |
| `PORT` | No | Web server port — defaults to `8000` (Render sets this) |
| `BIO_UPDATE_ENABLED` | No | Set to `true` to auto-start bio cron on boot |
| `LOG_LEVEL` | No | Logging level — defaults to `INFO` |

**Note:** Supabase is optional. If not configured, the bot uses in-memory storage and continues to function normally. Data will not persist across restarts without Supabase.

---

## Command Reference

### Utility
| Command | Description |
|---|---|
| `.ping` | Edit message to `PONG` |
| `.id` | Show Chat ID + Message ID |

### Save Engine (reply to a message)
| Command | Description |
|---|---|
| `.save f` | Forward save — metadata log, no download |
| `.save d` | Deep save — download, re-upload with rich caption |
| `.preview SV-000001` | Show stored metadata |
| `.send SV-000001` | Forward saved asset to current chat |

### Organizer
| Command | Description |
|---|---|
| `.organize list` | LifeOS data overview |
| `.organize clean` | Purge logs older than 7 days |
| `.del <n>` | Delete last n outgoing messages |
| `.del id <msgid>` | Delete all messages from msgid forward |

### Bio Engine
| Command | Description |
|---|---|
| `.bio help` | Token reference |
| `.bio template <tpl>` | Set bio template (`{time}`, `{mood}`, `{text}`) |
| `.bio text <text>` | Set {text} token |
| `.bio mood <mood>` | Set {mood} token |
| `.bio on` | Start timezone-synchronized cron |
| `.bio off` | Stop cron |
| `.bio show` | Inspect current state |

---

## Architecture

```
backend/
├── main.py          # asyncio entry point (telethon + uvicorn)
├── config.py        # env validation — only required vars hard-fail
├── bot/
│   ├── client.py    # StringSession, connect(), is_user_authorized()
│   ├── router.py    # registers all handlers
│   └── handlers/
│       ├── guard.py     # owner-only permission layer
│       ├── misc.py      # .ping, .id
│       ├── save.py      # .save f / .save d
│       ├── retrieve.py  # .preview, .send
│       ├── delete.py    # .del
│       ├── organize.py  # .organize
│       └── bio.py       # .bio
├── bio/
│   └── engine.py    # cron loop (exact minute sync, dedup)
├── db/
│   └── client.py    # Supabase singleton + in-memory fallback
└── web/
    └── app.py       # FastAPI + static serving

src/                 # React dashboard (dark Material 3)
├── App.tsx
├── components/
│   ├── SavedItems.tsx
│   ├── BioStatus.tsx
│   └── LogViewer.tsx
└── lib/
    └── api.ts       # typed fetch wrappers
```

## Security

- All credentials read exclusively from `os.getenv` — nothing hardcoded.
- Owner-only command gate: all other users are silently ignored.
- Session string never touches the filesystem on Render.
- No secrets are ever logged or printed.

## Reliability

- Supabase is optional — in-memory fallback ensures the bot never crashes.
- Bio cron: single task, idempotent start, deduplication, FloodWait handling.
- Clean shutdown: SIGTERM/SIGINT cancel all tasks and disconnect Telethon.
- Auto-reconnect enabled with 5 retries and 2s delay.
