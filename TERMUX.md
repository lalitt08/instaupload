# Run the bot free & 24/7 on an Android phone (Termux)

Your personal phone has a normal mobile/Wi-Fi IP (not Zscaler), so Instagram
login works there. The phone becomes the always-on host — free, no Render.

---

## Part 1 — on the laptop: put the code on GitHub (one time)

Git push works fine on the office network (it's GitHub, not Instagram). I've
already run `git init` + the first commit for you. You just need to:

1. Create an **empty private repo** at https://github.com/new (e.g. `reel-bot`).
   Don't add a README/.gitignore — keep it empty.
2. In the project folder on the laptop, run the two commands GitHub shows you:
   ```bash
   git remote add origin https://github.com/<your-username>/reel-bot.git
   git push -u origin main
   ```

Your secrets are safe — `.env` and `ig_session.json` are gitignored, so they
are **not** uploaded.

---

## Part 2 — on the phone: Termux setup

### 1. Install Termux from **F-Droid** (NOT the Play Store)
The Play Store version is outdated and breaks installs.
- Install the **F-Droid** app: https://f-droid.org
- In F-Droid, search and install **Termux**.

### 2. Open Termux and install the system tools
```bash
pkg update -y && pkg upgrade -y
pkg install -y python git ffmpeg rust clang binutils libjpeg-turbo libpng zlib
```

### 3. Get the code
```bash
git clone https://github.com/<your-username>/reel-bot.git
cd reel-bot
```

### 4. Create the `.env` file (your secrets — type your real values)
```bash
cat > .env <<'EOF'
BOT_TOKEN=PASTE_YOUR_TELEGRAM_BOT_TOKEN
IG_USERNAME=speak_4_nation
IG_PASSWORD=PASTE_YOUR_INSTAGRAM_PASSWORD
ALLOWED_TELEGRAM_IDS=
EOF
```
(The values are in the `.env` on your laptop — copy them over.)

### 5. Install the Python packages
```bash
pip install -r requirements.txt
```
⏳ This takes **~15–30 min the first time** — it compiles a couple of packages
(that's normal on a phone). Let it finish. If it errors, send me the last few
lines and I'll fix it.

### 6. Run it
```bash
python bot.py
```
- Wait for **`Instagram login OK`**. (Instagram may email/text a "was this you?"
  code the first time — approve it, then run `python bot.py` again.)
- In Telegram, send your bot **`/whoami`**, note the number it replies.
- Press **Ctrl+C**, put that number after `ALLOWED_TELEGRAM_IDS=` in `.env`
  (`nano .env` to edit), then run `python bot.py` again.

✅ Now send the bot any Instagram reel link — it reposts it with your fixed
caption.

---

## Part 3 — keep it running 24/7

- In Termux run: `termux-wake-lock` (stops Android sleeping the app).
- Phone Settings → Apps → Termux → Battery → **Unrestricted** (no battery
  optimization).
- Keep the phone charged / plugged in. Don't swipe Termux away from recents.

**Auto-start after reboot (optional):** install **Termux:Boot** from F-Droid,
then:
```bash
mkdir -p ~/.termux/boot
cat > ~/.termux/boot/start-bot.sh <<'EOF'
#!/data/data/com.termux/files/usr/bin/sh
termux-wake-lock
cd ~/reel-bot && python bot.py
EOF
chmod +x ~/.termux/boot/start-bot.sh
```

---

## If the bot stops logging in later
Instagram sessions expire eventually. Just run `python bot.py` again in Termux;
it re-logs in from the phone's IP (approve any challenge). Since it's on the
phone's trusted IP, this keeps working.
