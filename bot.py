"""Telegram bot entry point.

Flow:
    You send an Instagram Reel link to the bot
        -> bot extracts the URL
        -> downloads the reel (via instagrapi)
        -> generates a caption (original, or AI if configured)
        -> uploads it to your Instagram account
        -> replies with the new reel link
"""
import asyncio
import logging
import re
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import caption
import config
import instagram

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
# instagrapi is chatty at INFO; keep it to warnings.
logging.getLogger("instagrapi").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("bot")

# Matches instagram.com/reel/<code>, /reels/<code>, and /p/<code> links.
REEL_URL_RE = re.compile(
    r"https?://(?:www\.)?instagram\.com/(?:reel|reels|p)/[\w-]+/?",
    re.IGNORECASE,
)


def _is_authorized(update: Update) -> bool:
    """True if the sender is allowed to use the bot."""
    if not config.ALLOWED_TELEGRAM_IDS:
        return True  # no allowlist configured -> open to anyone
    user = update.effective_user
    return bool(user and user.id in config.ALLOWED_TELEGRAM_IDS)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Send me an Instagram Reel link and I'll repost it to your "
        "Instagram account.\n\nExample:\n"
        "https://www.instagram.com/reel/ABC123/"
    )


async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply with the sender's Telegram user ID (useful for the allowlist)."""
    user = update.effective_user
    await update.message.reply_text(f"Your Telegram user ID is: {user.id}")


def _process_reel(url: str) -> str:
    """Blocking pipeline: download -> caption -> upload -> cleanup.

    Runs off the event loop (instagrapi is synchronous). Returns the new
    reel URL.
    """
    video_path, original_caption = instagram.download_reel(url)
    try:
        new_caption = caption.generate_caption(original_caption)
        new_url = instagram.upload_reel(video_path, new_caption)
        return new_url
    finally:
        # Always clean up the downloaded file.
        try:
            Path(video_path).unlink(missing_ok=True)
        except OSError as e:
            log.warning("Could not delete %s: %s", video_path, e)


async def handle_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not _is_authorized(update):
        await update.message.reply_text("⛔ You're not authorized to use this bot.")
        return

    text = update.message.text or ""
    match = REEL_URL_RE.search(text)
    if not match:
        await update.message.reply_text(
            "❓ I couldn't find an Instagram Reel link in that message.\n"
            "Send something like: https://www.instagram.com/reel/ABC123/"
        )
        return

    url = match.group(0)
    status = await update.message.reply_text("⏳ Downloading and reposting…")

    try:
        # Run the blocking IG work in a thread so we don't block the bot.
        new_url = await asyncio.to_thread(_process_reel, url)
        await status.edit_text(f"✅ Reel posted successfully!\n{new_url}")
    except Exception as e:  # noqa: BLE001 - report any failure to the user
        log.exception("Failed to repost %s", url)
        await status.edit_text(f"❌ Failed to repost the reel:\n{e}")


def main() -> None:
    config.validate()

    # Log in to Instagram up front so credential/challenge problems surface
    # at startup rather than on the first reel.
    log.info("Logging in to Instagram…")
    instagram.get_client()
    log.info("Instagram login OK.")

    # Python 3.14 removed implicit event-loop creation on the main thread, but
    # python-telegram-bot 21.6's run_polling() still calls
    # asyncio.get_event_loop() internally expecting one to exist. Create and
    # set one ourselves; PTB manages and closes it normally from here.
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    app = Application.builder().token(config.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("whoami", whoami))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    log.info("Bot is running. Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
