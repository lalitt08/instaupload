"""Instagram logic: login (with session caching), download a reel, upload a reel.

Uses instagrapi for BOTH download and upload so everything runs on a single
authenticated session — no yt-dlp / cookie juggling required.
"""
import logging
import shutil
import subprocess
from pathlib import Path

from instagrapi import Client
from instagrapi.exceptions import LoginRequired

import config

log = logging.getLogger(__name__)


def _find_ffmpeg() -> str | None:
    """Locate an ffmpeg binary: system PATH first (Termux/Linux), then the one
    bundled with imageio-ffmpeg (desktop)."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001
        return None


def _make_thumbnail(video_path: Path) -> Path | None:
    """Grab the first frame as a JPG so instagrapi doesn't need moviepy to
    generate one. Returns None if ffmpeg isn't available (instagrapi then falls
    back to its own thumbnail path)."""
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        return None
    thumb = video_path.with_suffix(".jpg")
    try:
        subprocess.run(
            [ffmpeg, "-y", "-i", str(video_path), "-vframes", "1", "-q:v", "2",
             str(thumb)],
            check=True,
            capture_output=True,
        )
        return thumb if thumb.exists() else None
    except Exception as e:  # noqa: BLE001
        log.warning("ffmpeg thumbnail generation failed: %s", e)
        return None

# One shared client for the whole process.
_client: Client | None = None


def _build_client() -> Client:
    """Create a Client, restoring a cached session if one exists.

    Strategy:
      1. If a session file exists, load it and try to reuse it.
      2. Verify the session is still valid; if not, log in fresh with the
         password and re-save the session.
      3. If no session file, log in fresh and save the session.
    """
    cl = Client()
    cl.delay_range = [1, 3]  # small random delays -> looks less bot-like

    session_file = config.IG_SESSION_FILE

    # On cloud hosts with no persistent disk, seed the session from an env var
    # (a session created at home) so we don't do a fresh datacenter-IP login.
    if config.IG_SESSION_B64 and not session_file.exists():
        import base64

        try:
            session_file.parent.mkdir(parents=True, exist_ok=True)
            session_file.write_bytes(base64.b64decode(config.IG_SESSION_B64))
            log.info("Seeded Instagram session from IG_SESSION_B64.")
        except Exception as e:  # noqa: BLE001
            log.warning("Could not seed session from IG_SESSION_B64: %s", e)

    if session_file.exists():
        log.info("Loading cached Instagram session from %s", session_file)
        cl.load_settings(session_file)
        cl.login(config.IG_USERNAME, config.IG_PASSWORD)
        try:
            cl.get_timeline_feed()  # cheap call to confirm session is alive
            log.info("Cached session is valid.")
            return cl
        except LoginRequired:
            log.warning("Cached session expired. Logging in fresh.")
            # Keep the device/uuids from the old settings, drop stale auth.
            old_settings = cl.get_settings()
            cl.set_settings({})
            cl.set_uuids(old_settings.get("uuids", {}))

    log.info("Logging in to Instagram as %s", config.IG_USERNAME)
    cl.login(config.IG_USERNAME, config.IG_PASSWORD)
    cl.dump_settings(session_file)
    log.info("Login OK. Session saved to %s", session_file)
    return cl


def get_client() -> Client:
    """Return the shared, logged-in client (creating it on first use)."""
    global _client
    if _client is None:
        _client = _build_client()
    return _client


def download_reel(url: str) -> tuple[Path, str]:
    """Download a reel by its URL.

    Returns (path_to_mp4, original_caption).
    """
    cl = get_client()
    media_pk = cl.media_pk_from_url(url)
    info = cl.media_info(media_pk)
    original_caption = info.caption_text or ""

    log.info("Downloading reel %s ...", media_pk)
    path = cl.clip_download(media_pk, folder=config.DOWNLOAD_DIR)
    log.info("Downloaded to %s", path)
    return Path(path), original_caption


def upload_reel(path: Path, caption: str) -> str:
    """Upload an mp4 as a reel/clip. Returns the new media's URL/code."""
    cl = get_client()
    log.info("Uploading reel from %s ...", path)

    # Provide a thumbnail so instagrapi doesn't need moviepy to make one.
    thumb = _make_thumbnail(path)
    kwargs = {"thumbnail": thumb} if thumb else {}
    try:
        media = cl.clip_upload(path, caption=caption, **kwargs)
    finally:
        if thumb:
            thumb.unlink(missing_ok=True)

    code = getattr(media, "code", None)
    url = f"https://www.instagram.com/reel/{code}/" if code else "(posted)"
    log.info("Uploaded. New reel: %s", url)
    return url
