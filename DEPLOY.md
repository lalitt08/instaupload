# Hosting the bot 24/7

Read this first — it decides everything below.

## ⚠️ The one constraint that rules out most "free" hosts

This bot logs into Instagram's **private mobile API** (via `instagrapi`) to
download and upload reels. Instagram **blocks datacenter / cloud IP ranges** at
login — you get `403 Forbidden` at `launcher/sync` before your password is even
checked. We already hit exactly this on the corporate (Zscaler) network.

**Almost every "free host" runs on datacenter IPs**, so they hit the same 403:

| Platform | Runs 24/7? | Works with Instagram? | Verdict |
|---|---|---|---|
| **Vercel** | ❌ serverless, ephemeral | ❌ datacenter IP, no ffmpeg, no persistent session, function timeouts | **No** — wrong tool for a long-running bot |
| **GitHub Actions** | ❌ CI, not always-on | ❌ Azure datacenter IP, no real-time polling | **No** |
| **Render (paid Worker)** | ✅ | ⚠️ datacenter IP — needs the session trick; may still be challenged | Possible (~$7/mo) — see below |
| **Render (free Web Service)** | ⚠️ spins down after 15 min idle | ❌ ephemeral disk wipes session → re-login → 403 | Not viable |
| **Oracle Cloud "Always Free" VM** | ✅ truly free forever | ⚠️ datacenter IP — *may* work with the session trick below | Best free **cloud** option |
| **Your own always-on device (home)** | ✅ | ✅ residential IP = trusted | ✅ **Recommended** |

**Bottom line:** the problem was never the code or the platform — it's the IP.
A residential IP works; datacenter IPs usually don't.

---

## ✅ Recommended: run it on an always-on device at home (free + reliable)

Any device on your **home internet** works, because it has a residential IP:
your home PC/laptop (left on), a Raspberry Pi, an old laptop, or even an old
Android phone (via Termux). It polls Telegram (works from anywhere) and talks to
Instagram from the trusted home IP.

### Option A — plain Python (simplest)

```bash
# one time
python -m venv venv
venv/Scripts/python -m pip install -r requirements.txt

# run it (keep this running)
venv/Scripts/python bot.py
```

To keep it running after you close the terminal / after reboots:
- **Windows:** Task Scheduler → "At log on" → run `venv\Scripts\python.exe bot.py`.
- **Linux/Pi:** a `systemd` service, or `pm2 start "python bot.py"`.

### Option B — Docker (auto-restart, survives reboots)

If the device has Docker:

```bash
docker compose up -d --build     # starts and keeps it running
docker compose logs -f           # watch logs (approve any IG login challenge)
```

`docker-compose.yml` persists the Instagram session in a volume, so it only
logs in once. `restart: unless-stopped` brings it back after reboots/crashes.

Either way: on first login Instagram may send a "was this you?" prompt/email —
approve it once, and the saved session is reused after that.

---

## ☁️ If you really want it in the cloud (free): the session-transfer trick

Cloud VMs have datacenter IPs, so a **fresh** login there will likely 403. The
workaround is to log in once from home and carry the session to the cloud:

1. Run the bot **once at home** so it creates `ig_session.json` (a valid,
   Instagram-trusted session).
2. Spin up a free always-on VM — **Oracle Cloud "Always Free"** is the best
   (free forever; Google Cloud `e2-micro` free tier also works).
3. Copy the code + your `.env` + `ig_session.json` to the VM.
4. Run with Docker (`docker compose up -d --build`). The compose file mounts the
   session at `/data/ig_session.json` (via the `IG_SESSION_FILE` env var).

This works because Instagram trusts the existing session. It is **not
guaranteed** — a big IP jump (home → datacenter) can still trigger a
re-verification, and heavy use raises flagging risk. If it keeps challenging,
you need a **residential/mobile proxy** (paid) via `Client.set_proxy(...)`, or
just run on the home device.

---

## Deploy to Render (paid Background Worker + home session)

Render deploys our `Dockerfile` easily, but two facts shape the setup:
- The bot long-polls (no web port) → it must be a **Background Worker**, which
  is **paid** (~$7/mo). The free Web Service tier spins down when idle and has an
  ephemeral disk that wipes the login session — not viable.
- Render's IP is a datacenter IP, so a **fresh** login there will likely `403`.
  We get around it by seeding the session created at home via `IG_SESSION_B64`.

### Steps

1. **Create the session at home** (residential IP):
   ```bash
   venv/Scripts/python bot.py          # log in once; creates ig_session.json
   # Ctrl+C after you see "Instagram login OK"
   venv/Scripts/python make_session_b64.py   # prints a long base64 string — copy it
   ```
2. Push this project to a GitHub repo (Render deploys from Git). `.env`,
   `venv/`, and `ig_session.json` are gitignored — good, keep secrets out of Git.
3. In Render: **New → Blueprint**, point it at the repo. It reads
   [render.yaml](render.yaml) and creates the worker.
4. In the service's **Environment** tab, set the secrets (all `sync:false`):
   `BOT_TOKEN`, `IG_USERNAME`, `IG_PASSWORD`, `ALLOWED_TELEGRAM_IDS`, and
   `IG_SESSION_B64` (paste the base64 from step 1).
5. Deploy and watch the logs. If you see `Instagram login OK`, you're live —
   send the bot a reel link. If you see a `403` at `launcher/sync`, Render's IP
   is blocked even with the session → fall back to the home device, or add a
   residential proxy.

**Maintenance:** the seeded session eventually expires. When it does, the bot
will try a password login (which `403`s on Render's IP). Just re-run
`make_session_b64.py` at home and update the `IG_SESSION_B64` value on Render.

> No persistent disk is needed — the session is re-seeded from `IG_SESSION_B64`
> on every boot. That keeps it to the single worker charge.

## Which should you pick?

- **Want it free and just working?** → Home device (Option A or B). This is the
  honest best answer.
- **Home device can't stay on?** → Oracle Always-Free VM with the session trick.
- **Must run from a locked-down network and it keeps getting blocked?** → add a
  residential proxy (small monthly cost) — tell me and I'll wire in `PROXY`
  support.

---

## Deploy checklist (any host)

- [ ] `.env` present with `BOT_TOKEN`, `IG_USERNAME`, `IG_PASSWORD`
- [ ] `ALLOWED_TELEGRAM_IDS` set to your Telegram ID (so only you can post)
- [ ] `caption.txt` has the caption you want on every post
- [ ] First login done from a residential IP (creates `ig_session.json`)
- [ ] Process set to auto-restart (Docker `restart:` / systemd / Task Scheduler)
