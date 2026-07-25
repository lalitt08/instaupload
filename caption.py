"""Optional AI caption generation with Claude.

If ANTHROPIC_API_KEY is set in .env, we ask Claude to write a fresh caption
based on the original reel's caption. If not, we just reuse the original
caption (or a simple default).
"""
import logging

import config

log = logging.getLogger(__name__)

DEFAULT_CAPTION = "🔥"

PROMPT = """You are writing an Instagram caption for a reel that is being reposted.

Here is the original reel's caption (it may be empty or in another language):
---
{original}
---

Write a fresh, engaging Instagram caption for this reel. Rules:
- Keep it short (1-2 lines).
- Add a few relevant emojis.
- End with 3-6 relevant hashtags.
- Return ONLY the caption text, nothing else. No preamble, no quotes."""


def generate_caption(original_caption: str) -> str:
    """Return a caption for the repost.

    Priority:
      1. Fixed caption from caption.txt (used verbatim on every post).
      2. AI-generated caption (if ANTHROPIC_API_KEY is set).
      3. The original reel's caption (or a default).
    """
    original_caption = (original_caption or "").strip()

    # 1. Fixed caption file wins.
    try:
        if config.CAPTION_FILE.exists():
            fixed = config.CAPTION_FILE.read_text(encoding="utf-8").strip()
            if fixed:
                return fixed
    except OSError as e:
        log.warning("Could not read %s: %s", config.CAPTION_FILE, e)

    if not config.ANTHROPIC_API_KEY:
        # No AI configured — reuse the original, or a default if it's empty.
        return original_caption or DEFAULT_CAPTION

    try:
        import anthropic  # lazy import: only needed when a key is set

        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model=config.CAPTION_MODEL,
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": PROMPT.format(original=original_caption or "(none)"),
                }
            ],
        )
        text = next(
            (b.text for b in response.content if b.type == "text"), ""
        ).strip()
        return text or original_caption or DEFAULT_CAPTION
    except Exception as e:  # noqa: BLE001 - never let caption gen break a post
        log.warning("Caption generation failed (%s); using original.", e)
        return original_caption or DEFAULT_CAPTION
