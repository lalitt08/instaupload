# Reel Reposter Bot (Telegram → Instagram)

Send an Instagram Reel link to your Telegram bot, and it downloads the reel and
reposts it to your Instagram account.

```
You  ──send reel link──▶  Telegram Bot  ──▶  download reel  ──▶  (optional AI caption)  ──▶  upload to Instagram  ──▶  ✅ reply with new link
```

## How it works

- **Download + upload** both use [`instagrapi`](https://github.com/subzeroid/instagrapi)
  on a single authenticated Instagram session (no `yt-dlp`/cookies needed).
- The Instagram login session is cached in `ig_session.json` so the bot doesn't
  log in fresh every run (fewer security prompts from Instagram).
- Captions: by default the original reel's caption is reused. If you set an
  `ANTHROPIC_API_KEY`, captions are rewritten by Claude instead.

## Files

| File            | Purpose                                              |
| --------------- | ---------------------------------------------------- |
| `bot.py`        | Telegram bot — receives links, runs the pipeline     |
| `instagram.py`  | Instagram login (cached), download reel, upload reel |
| `caption.py`    | Optional AI caption generation                       |
| `config.py`     | Loads settings from `.env`                           |
| `.env`          | Your secrets (bot token, IG credentials)             |
| `requirements.txt` | Python dependencies                               |

## Setup

Dependencies are already installed in `venv/`. If you ever need to reinstall:

```bash
venv/Scripts/python -m pip install -r requirements.txt
```

## Configure `.env`

```ini
BOT_TOKEN=your_telegram_bot_token
IG_USERNAME=your_instagram_username
IG_PASSWORD=your_instagram_password

# Optional — restrict who can use the bot (comma-separated Telegram user IDs).
# Get your ID by sending /whoami to the bot. Leave empty to allow anyone.
ALLOWED_TELEGRAM_IDS=

# Optional — enable AI captions with Claude. If unset, the original caption is reused.
ANTHROPIC_API_KEY=
CAPTION_MODEL=claude-opus-4-8
```

> **Tip:** Set `ALLOWED_TELEGRAM_IDS` so only you can trigger posts to your account.

## Run

```bash
venv/Scripts/python bot.py
```

On startup the bot logs in to Instagram, then waits for messages. Send it a reel
link in Telegram:

```
https://www.instagram.com/reel/ABC123/
```

It replies `✅ Reel posted successfully!` with the new reel's link.

Bot commands: `/start` (help), `/whoami` (show your Telegram ID for the allowlist).

## First-login note

The **first** login from a new machine may trigger an Instagram security
challenge (a code sent to your email/SMS, or a "Was this you?" prompt).
If that happens, `instagrapi` raises a challenge error at startup. Approve the
login in the Instagram app / email, then run the bot again. Once a session is
saved to `ig_session.json`, subsequent runs reuse it silently.

## Troubleshooting: `403 Forbidden` at `launcher/sync` on login

If login fails immediately with a `403` on `.../api/v1/launcher/sync/` (before
your password is even checked), Instagram is **blocking the IP**, not rejecting
your credentials. This happens on corporate networks, VPNs, and proxies —
notably **Zscaler** and other cloud proxies, whose IP ranges Instagram's private
API refuses.

**Fix:** run the bot from a **residential or mobile connection** (home Wi-Fi, or
tether to your phone's hotspot). Mobile/residential IPs are trusted and this
almost always works. If you must stay on a corporate network, route instagrapi
through a residential proxy (`Client.set_proxy("http://user:pass@host:port")`).

## Running 24/7

To have the bot always available, run it on an always-on machine:
a small VPS (DigitalOcean, Hetzner, AWS EC2), a Raspberry Pi, or a PC that
stays on. Keep `ig_session.json` alongside the code so it doesn't re-login.

## ⚠️ Notes & caveats

- `instagrapi` automates Instagram's private mobile API — not the official Graph
  API. It can break if Instagram changes things, and heavy automation may risk
  account restrictions. Use in moderation.
- Only repost content you have the rights/permission to use, and follow
  Instagram's Terms and copyright rules.
