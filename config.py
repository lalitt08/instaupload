"""Central configuration, loaded from the .env file."""
import os
from pathlib import Path

from dotenv import load_dotenv

# Project root (folder this file lives in)
BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

# --- Telegram ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Optional: comma-separated Telegram user IDs allowed to use the bot.
# Leave empty to allow anyone who finds the bot. Highly recommended to set this.
_allowed = os.getenv("ALLOWED_TELEGRAM_IDS", "").strip()
ALLOWED_TELEGRAM_IDS = {
    int(x) for x in _allowed.replace(" ", "").split(",") if x
}

# --- Instagram ---
IG_USERNAME = os.getenv("IG_USERNAME", "").strip()
IG_PASSWORD = os.getenv("IG_PASSWORD", "").strip()

# Where the cached IG login session is stored so we don't log in every run.
# Override with IG_SESSION_FILE env var (useful for Docker/cloud, where you
# create the session at home and mount/copy it in on a persistent volume).
IG_SESSION_FILE = Path(
    os.getenv("IG_SESSION_FILE", str(BASE_DIR / "ig_session.json"))
)

# For cloud hosts (Render, etc.) with no persistent disk: paste the base64 of a
# session created at home into this env var. On boot we write it to
# IG_SESSION_FILE so the bot reuses that trusted session instead of doing a
# fresh password login from a datacenter IP (which Instagram blocks).
# Create it at home with:  python make_session_b64.py
IG_SESSION_B64 = os.getenv("IG_SESSION_B64", "").strip()

# --- Caption ---
# Fixed caption: every post uses the text in this file, verbatim. Edit the file
# to change the caption for future posts. If the file is missing/empty, we fall
# back to AI captions (if a key is set) or the original reel caption.
CAPTION_FILE = BASE_DIR / "caption.txt"

# Optional AI caption fallback (only used when caption.txt is empty/missing).
# If set, captions are generated with Claude. If empty, we reuse the original
# reel's caption (or a simple default).
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()
CAPTION_MODEL = os.getenv("CAPTION_MODEL", "claude-opus-4-8").strip()

# --- Files ---
DOWNLOAD_DIR = BASE_DIR / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)


def validate() -> None:
    """Fail fast with a clear message if required settings are missing."""
    missing = []
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not IG_USERNAME:
        missing.append("IG_USERNAME")
    if not IG_PASSWORD:
        missing.append("IG_PASSWORD")
    if missing:
        raise SystemExit(
            "Missing required settings in .env: " + ", ".join(missing)
        )
