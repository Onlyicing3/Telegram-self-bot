"""
Bio command handler.
All sub-commands edit the triggering message in-place (zero-spam policy).

  .bio help              — Token reference
  .bio template <tpl>    — Set template
  .bio text <text>       — Set {text} token
  .bio mood <mood>       — Set {mood} token
  .bio on                — Start timezone-synchronized cron
  .bio off               — Stop cron
  .bio show              — Inspect current state
"""
import logging
from datetime import datetime

import pytz
from telethon import events

from backend.bio import engine as bio_engine
from backend.bot.handlers.guard import is_owner
from backend.db import client as db_client

logger = logging.getLogger(__name__)

_HELP = (
    "**Bio Engine — Token Reference**\n\n"
    "`{time}` — Current time (HH:MM)\n"
    "`{mood}` — Current mood value\n"
    "`{text}` — Custom freeform text\n\n"
    "**Commands**\n"
    "`.bio text <text>` — Set {text}\n"
    "`.bio mood <mood>` — Set {mood}\n"
    "`.bio on` — Start cron sync\n"
    "`.bio off` — Stop cron sync\n"
    "`.bio show` — Inspect state\n"
    "`.bio template <tpl>` — Set template\n\n"
    "**Example template**\n"
    "`🕒 {time} | 💭 {mood} | 📝 {text}`"
)


def register(client, owner_id: int, tz_str: str):

    @client.on(events.NewMessage(outgoing=True, pattern=r"^\.bio(?:\s+(.+))?$"))
    async def bio_cmd(event):
        if not is_owner(event, owner_id):
            return

        arg = (event.pattern_match.group(1) or "").strip()

        try:
            state = db_client.get_or_create_bio_state(owner_id)
        except Exception as exc:
            logger.error("bio db init failed: %s", exc)
            await event.edit(f"❌ DB error: {exc}")
            return

        if (not arg) or (arg in ("help", "template") and " " not in arg):
            if arg == "template":
                await event.edit(
                    f"**Current template:**\n`{state.get('template')}`\n\n"
                    "To change: `.bio template <new template>`"
                )
            else:
                await event.edit(_HELP)
            return

        if arg.startswith("template "):
            new_tpl = arg[9:].strip()
            if not new_tpl:
                await event.edit("⚠️ Template cannot be empty.")
                return
            db_client.update_bio_state(owner_id, {"template": new_tpl})
            await event.edit(f"✅ Template updated:\n`{new_tpl}`")

        elif arg.startswith("text "):
            val = arg[5:].strip()
            db_client.update_bio_state(owner_id, {"custom_text": val})
            await event.edit(f"✅ Text set to: `{val}`")

        elif arg.startswith("mood "):
            val = arg[5:].strip()
            db_client.update_bio_state(owner_id, {"mood": val})
            await event.edit(f"✅ Mood set to: `{val}`")

        elif arg == "on":
            db_client.update_bio_state(owner_id, {"is_active": True})
            bio_engine.start_cron(client, owner_id, tz_str)
            preview = bio_engine.render_bio(
                state.get("template", "🕒 {time} | 💭 {mood}"),
                state.get("mood", "😊"),
                state.get("custom_text", ""),
                tz_str,
            )
            await event.edit(f"✅ Bio cron **ON**\nPreview: `{preview}`")

        elif arg == "off":
            db_client.update_bio_state(owner_id, {"is_active": False})
            bio_engine.stop_cron()
            await event.edit("⏹ Bio cron **OFF**")

        elif arg == "show":
            tz = pytz.timezone(tz_str)
            now = datetime.now(tz)
            preview = bio_engine.render_bio(
                state.get("template", "🕒 {time} | 💭 {mood}"),
                state.get("mood", "😊"),
                state.get("custom_text", ""),
                tz_str,
            )
            status = "ON" if bio_engine.is_running() else "OFF"
            await event.edit(
                f"**Bio State**\n\n"
                f"Status: `{status}`\n"
                f"Template: `{state.get('template')}`\n"
                f"Mood: `{state.get('mood')}`\n"
                f"Text: `{state.get('custom_text') or '—'}`\n"
                f"Last Bio: `{state.get('last_bio') or '—'}`\n"
                f"Preview: `{preview}`\n"
                f"Server Time ({tz_str}): `{now.strftime('%H:%M:%S')}`"
            )

        else:
            await event.edit("⚠️ Unknown bio command. Try `.bio help`")
