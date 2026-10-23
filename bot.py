#!/usr/bin/env python3
"""
LinkHide Bot - a Telegram link-hiding bot (python-telegram-bot v21+).

Features
  * Hide a link behind custom text   (/hide)
  * Send a message with inline URL buttons (/button, /buttons)
  * Paste a bare link and pick a mode with inline buttons
  * /start, /help, /cancel

Setup: put your BotFather token in BOT_TOKEN (env var or .env file), then
run:  python bot.py
"""

import html
import logging
import os
import re
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO
)
log = logging.getLogger("linkhide")

URL_FIND = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
URL_FULL = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)

HELP_TEXT = (
    "<b>🔗 LinkHide Bot</b>\n"
    "Hide links behind text or buttons.\n\n"
    "<b>Commands</b>\n"
    "/hide <code>url text</code> – hide a link behind text\n"
    "   e.g. <code>/hide https://example.com Click here</code>\n\n"
    "/button <code>url | label | message</code> – message with one inline button\n"
    "   e.g. <code>/button https://example.com | Open | Check this out</code>\n\n"
    "/buttons – several buttons, one per line:\n"
    "<code>/buttons\nhttps://a.com | Site A\nhttps://b.com | Site B</code>\n\n"
    "/cancel – cancel the current action\n"
    "/help – show this message\n\n"
    "<b>Quick mode:</b> just send me a link and choose what to do with it."
)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def load_env_file(path: str = ".env") -> None:
    """Tiny .env loader so no extra dependency is needed."""
    p = Path(path)
    if not p.is_file():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def is_valid_url(url: str) -> bool:
    return bool(URL_FULL.fullmatch(url))


def hidden_link(url: str, text: str) -> str:
    return f'<a href="{html.escape(url, quote=True)}">{html.escape(text)}</a>'


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📖 Help", callback_data="help")],
        ]
    )


def mode_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔗 Hidden text link", callback_data="mode:link"),
                InlineKeyboardButton("🔘 Inline button", callback_data="mode:button"),
            ],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
        ]
    )


async def send_hidden(update: Update, url: str, text: str) -> None:
    await update.effective_message.reply_text(
        hidden_link(url, text),
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    name = html.escape(update.effective_user.first_name or "there")
    await update.message.reply_text(
        f"👋 Hi <b>{name}</b>!\n\n"
        "I can hide your links behind text or inline buttons.\n"
        "Send me a link to begin, or use /help.",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu(),
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        HELP_TEXT, parse_mode=ParseMode.HTML, disable_web_page_preview=True
    )


async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    await update.message.reply_text("✅ Cancelled.")


async def hide_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args
    if len(args) < 2 or not is_valid_url(args[0]):
        await update.message.reply_text(
            "Usage: /hide <url> <text>\n"
            "Example: /hide https://example.com Click here"
        )
        return
    await send_hidden(update, args[0], " ".join(args[1:]))


async def button_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    raw = update.message.text.partition(" ")[2]
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) < 2 or not is_valid_url(parts[0]) or not parts[1]:
        await update.message.reply_text(
            "Usage: /button <url> | <label> | <message (optional)>\n"
            "Example: /button https://example.com | Open | Check this out"
        )
        return
    url, label = parts[0], parts[1][:64]
    message = parts[2] if len(parts) > 2 and parts[2] else "👇"
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(label, url=url)]]),
    )


async def buttons_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    raw = update.message.text.partition("\n")[2]
    rows = []
    for line in raw.splitlines():
        if "|" not in line:
            continue
        url, _, label = line.partition("|")
        url, label = url.strip(), label.strip()[:64]
        if is_valid_url(url) and label:
            rows.append([InlineKeyboardButton(label, url=url)])
    if not rows:
        await update.message.reply_text(
            "Usage (one button per line):\n"
            "/buttons\n"
            "https://a.com | Site A\n"
            "https://b.com | Site B"
        )
        return
    await update.message.reply_text("👇", reply_markup=InlineKeyboardMarkup(rows[:20]))


# --------------------------------------------------------------------------
# quick mode: bare link -> choose mode -> send text/label
# --------------------------------------------------------------------------
async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (update.message.text or "").strip()
    ud = context.user_data

    # Waiting for the label / text after choosing a mode
    if ud.get("awaiting") and ud.get("url"):
        url, mode = ud["url"], ud["awaiting"]
        ud.clear()
        if mode == "link":
            await send_hidden(update, url, text)
        else:
            await update.message.reply_text(
                "👇",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton(text[:64], url=url)]]
                ),
            )
        return

    match = URL_FIND.search(text)
    if not match:
        await update.message.reply_text(
            "Send me a link starting with http:// or https://\nSee /help."
        )
        return

    ud.clear()
    ud["url"] = match.group(0)
    await update.message.reply_text(
        "What should I do with this link?", reply_markup=mode_menu()
    )


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    ud = context.user_data

    if data == "help":
        await query.message.reply_text(
            HELP_TEXT, parse_mode=ParseMode.HTML, disable_web_page_preview=True
        )
    elif data == "cancel":
        ud.clear()
        await query.edit_message_text("✅ Cancelled.")
    elif data.startswith("mode:"):
        if not ud.get("url"):
            await query.edit_message_text("Session expired. Send the link again.")
            return
        mode = data.split(":", 1)[1]
        ud["awaiting"] = mode
        prompt = (
            "✏️ Send the text to show instead of the link."
            if mode == "link"
            else "✏️ Send the label for the button."
        )
        await query.edit_message_text(prompt)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    log.error("Unhandled error", exc_info=context.error)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main() -> None:
    load_env_file()
    token = os.environ.get("BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "BOT_TOKEN is missing. Put it in a .env file:  BOT_TOKEN=123456:ABC..."
        )

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("cancel", cancel_cmd))
    app.add_handler(CommandHandler("hide", hide_cmd))
    app.add_handler(CommandHandler("button", button_cmd))
    app.add_handler(CommandHandler("buttons", buttons_cmd))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(on_error)

    log.info("Bot started. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
