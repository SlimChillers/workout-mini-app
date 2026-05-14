#!/usr/bin/env python3
"""
Workout Mini App Handler for Hermes Telegram bot.

Listens for /workout commands and web_app_data from the workout Mini App.
Runs as a standalone process alongside Hermes, using a SEPARATE polling
connection with allowed_updates to avoid conflicts.

Requires: pip install python-telegram-bot google-api-python-client
"""

import asyncio
import json
import logging
import os
import subprocess
import sys

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, ContextTypes
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [workout] %(message)s")
logger = logging.getLogger("workout-bot")

# ── Configuration ──────────────────────────────────────────────
SPREADSHEET_ID = "1REsqKFnvUgejcXHU1EVCGJVr8WLm89qgp4423PhwTLo"
MINI_APP_URL = "https://transcripts-hrs-skills-creator.trycloudflare.com"
GAPI = "/opt/data/google-venv/bin/python /opt/data/profiles/coding-premium/skills/productivity/google-workspace/scripts/google_api.py"
TOKEN_PATH = "/opt/data/profiles/coding-premium/config.yaml"

# ── Token Helper ───────────────────────────────────────────────

def get_bot_token() -> str:
    """Extract bot token from Hermes config.yaml."""
    import yaml
    with open(TOKEN_PATH) as f:
        config = yaml.safe_load(f)
    # Try common token paths in Hermes config
    telegram = config.get("platforms", {}).get("telegram", {})
    if isinstance(telegram, dict):
        for key in ("bot_token", "token", "api_token"):
            if telegram.get(key):
                return telegram[key]
    raise RuntimeError("Bot token not found in config.yaml. Check platforms.telegram.bot_token")


# ── Handlers ───────────────────────────────────────────────────

async def cmd_workout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the Mini App button."""
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "🏋️ Log Workout",
            web_app=WebAppInfo(url=MINI_APP_URL)
        )
    ]])
    await update.message.reply_text(
        "Tap below to open the workout logger:",
        reply_markup=keyboard
    )


async def handle_web_app_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle data sent from the workout Mini App."""
    raw = update.message.web_app_data.data
    logger.info("Received web_app_data: %s", raw[:200])

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        await update.message.reply_text("⚠️ Invalid data from Mini App.")
        return

    if data.get("type") != "workout_log":
        return

    await log_workout(update.message.chat_id, data)


async def log_workout(chat_id: int, data: dict):
    """Write workout data to Google Sheets."""
    date = data.get("date", "")
    workout = data.get("workout", "")
    exercises = data.get("exercises", [])
    cardio_type = data.get("cardio_type", "")
    cardio_min = data.get("cardio_min", 0)
    notes = data.get("notes", "")

    # Build rows (one per non-skipped exercise)
    rows = []
    for ex in exercises:
        if ex.get("skipped"):
            continue
        rows.append([
            date,
            workout,
            ex["name"],
            str(ex["weight"]) if ex.get("weight", 0) > 0 else "",
            str(ex["reps"]) if ex.get("reps", 0) > 0 else "",
            str(ex["sets"]) if ex.get("sets", 0) > 0 else "",
            cardio_type,
            str(cardio_min) if cardio_min > 0 else "",
            notes
        ])

    # Cardio-only
    if not rows and (cardio_type or cardio_min):
        rows.append([date, workout, "Cardio only", "", "", "",
                     cardio_type, str(cardio_min), notes])
    elif rows and (cardio_type or cardio_min):
        rows[-1][6] = cardio_type
        rows[-1][7] = str(cardio_min)

    if not rows:
        logger.info("No rows to log")
        return

    # Write to Google Sheets
    try:
        values_json = json.dumps(rows)
        cmd = f'{GAPI} sheets append {SPREADSHEET_ID} "Log!A:I" --values \'{values_json}\''

        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=15,
            env={**os.environ, "HOME": os.path.expanduser("~")}
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout or "Unknown error")

        exercise_names = [r[2] for r in rows]
        summary = ", ".join(exercise_names)
        msg = f"✅ Workout logged!\n📅 {date} — {workout}\n💪 {summary}"
        if cardio_type and cardio_min:
            msg += f"\n🏃 {cardio_type} {cardio_min}min"
        if notes:
            msg += f"\n📝 {notes}"

        # Respond via HTTP API so we don't conflict with Hermes' polling
        await _send_confirmation(chat_id, msg)
        logger.info("Workout logged: %d rows for %s", len(rows), date)

    except Exception as e:
        logger.error("Failed to log workout: %s", e)
        await _send_confirmation(chat_id, f"❌ Failed to log workout: {e}")


async def _send_confirmation(chat_id: int, text: str):
    """Send confirmation via Telegram Bot API directly (HTTP, not PTB)."""
    import httpx
    token = BOT_TOKEN
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(url, json={"chat_id": chat_id, "text": text})


# ── Main ───────────────────────────────────────────────────────

BOT_TOKEN = ""

async def main():
    global BOT_TOKEN
    BOT_TOKEN = get_bot_token()
    logger.info("Starting workout handler bot...")

    app = Application.builder().token(BOT_TOKEN).build()

    # Register handlers
    app.add_handler(CommandHandler("workout", cmd_workout))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, handle_web_app_data))

    # Polling — only for specified update types, Hermes handles the rest
    logger.info("Bot started. Waiting for /workout commands and Mini App data...")
    await app.run_polling(
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True
    )


if __name__ == "__main__":
    asyncio.run(main())
