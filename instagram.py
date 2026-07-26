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
from instagrapi.types import Track

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


def _find_original_track(cl: Client, info) -> Track | None:
    """Look up the exact licensed-music Track the source reel used, so the
    repost can be attributed to the same official audio (not just re-upload
    the same audio bytes). Returns None for reels using original/personal
    audio (no catalogued track exists to attribute to) or if lookup fails."""
    clips_metadata = getattr(info, "clips_metadata", None)
    if not clips_metadata:
        return None
    music_canonical_id = getattr(clips_metadata, "music_canonical_id", None)
    if not music_canonical_id:
        return None  # original/personal audio, or no music attached

    try:
        track = cl.track_info_by_canonical_id(music_canonical_id)
        log.info("Found original audio track: %s", track.title)
        return track
    except Exception as e:  # noqa: BLE001 - attribution is best-effort
        log.warning("Could not look up original audio track: %s", e)
        return None


def download_reel(url: str) -> tuple[Path, str, Track | None]:
    """Download a reel by its URL.

    Returns (path_to_mp4, original_caption, original_track_or_None).
    """
    cl = get_client()
    media_pk = cl.media_pk_from_url(url)
    info = cl.media_info(media_pk)
    original_caption = info.caption_text or ""
    track = _find_original_track(cl, info)

    log.info("Downloading reel %s ...", media_pk)
    path = cl.clip_download(media_pk, folder=config.DOWNLOAD_DIR)
    log.info("Downloaded to %s", path)
    return Path(path), original_caption, track


def upload_reel(path: Path, caption: str, track: Track | None = None) -> str:
    """Upload an mp4 as a reel/clip. Returns the new media's URL/code.

    If `track` is given, attributes the post to that same official audio
    track (metadata only — the audio itself is already in the video file).
    Falls back to a plain upload if that fails for any reason.
    """
    cl = get_client()
    log.info("Uploading reel from %s ...", path)

    # Provide a thumbnail so instagrapi doesn't need moviepy to make one.
    thumb = _make_thumbnail(path)
    kwargs = {"thumbnail": thumb} if thumb else {}
    try:
        if track is not None:
            try:
                media = cl.clip_upload_with_music(
                    path, caption=caption, track=track, **kwargs
                )
                log.info("Uploaded with original audio attribution.")
            except Exception as e:  # noqa: BLE001 - never let this block the post
                log.warning(
                    "Could not attribute original audio (%s); "
                    "uploading without it.",
                    e,
                )
                media = cl.clip_upload(path, caption=caption, **kwargs)
        else:
            media = cl.clip_upload(path, caption=caption, **kwargs)
    finally:
        if thumb:
            thumb.unlink(missing_ok=True)

    code = getattr(media, "code", None)
    url = f"https://www.instagram.com/reel/{code}/" if code else "(posted)"
    log.info("Uploaded. New reel: %s", url)
    return url
