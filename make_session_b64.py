"""Print the base64 of your Instagram session file.

Run this AT HOME (residential IP) after the bot has logged in once and created
ig_session.json. Copy the output into the IG_SESSION_B64 env var on your cloud
host (Render, etc.) so it reuses this trusted session instead of logging in
fresh from a datacenter IP.

    python make_session_b64.py
"""
import base64
import sys

import config

if not config.IG_SESSION_FILE.exists():
    sys.exit(
        f"No session file at {config.IG_SESSION_FILE}.\n"
        "Run the bot once at home first so it logs in and creates it."
    )

data = config.IG_SESSION_FILE.read_bytes()
print(base64.b64encode(data).decode("ascii"))
