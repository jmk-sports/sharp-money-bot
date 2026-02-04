"""
bluesky_poster.py
─────────────────
Posts picks and updates profile description on Bluesky via the AT Protocol.

Bluesky authentication uses:
  - Handle (e.g., "sharpmoney.bsky.social")
  - App Password (generated in Settings → Privacy & Security → App Passwords)

No developer account needed — just create the account and generate an
app password. Done.
"""

import os, requests, time
from dotenv import load_dotenv

load_dotenv()

BLUESKY_HANDLE   = os.getenv("BLUESKY_HANDLE",   "your-handle.bsky.social")
BLUESKY_PASSWORD = os.getenv("BLUESKY_PASSWORD", "YOUR_APP_PASSWORD_HERE")

API_BASE = "https://bsky.social/xrpc"

MAX_RETRIES = 3
RETRY_DELAY = 5


# ── authentication ────────────────────────────────────────────────────────
_session_cache = None

def _get_session():
    """Create an authenticated session. Returns (did, access_jwt)."""
    global _session_cache
    if _session_cache:
        return _session_cache

    resp = requests.post(
        f"{API_BASE}/com.atproto.server.createSession",
        json={"identifier": BLUESKY_HANDLE, "password": BLUESKY_PASSWORD},
        timeout=15
    )
    resp.raise_for_status()
    data = resp.json()
    _session_cache = (data["did"], data["accessJwt"])
    return _session_cache


# ── public functions ──────────────────────────────────────────────────────
def post_skeet(text: str) -> bool:
    """
    Post a 'skeet' (Bluesky's term for a post).
    Returns True on success.
    """
    did, jwt = _get_session()

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(
                f"{API_BASE}/com.atproto.repo.createRecord",
                headers={"Authorization": f"Bearer {jwt}"},
                json={
                    "repo": did,
                    "collection": "app.bsky.feed.post",
                    "record": {
                        "$type": "app.bsky.feed.post",
                        "text": text,
                        "createdAt": requests.get("https://worldtimeapi.org/api/timezone/Etc/UTC", timeout=5).json()["datetime"]
                    }
                },
                timeout=15
            )
            resp.raise_for_status()
            print(f"[bluesky] Post created successfully — uri={resp.json().get('uri')}")
            return True

        except requests.exceptions.RequestException as exc:
            print(f"[bluesky] Post attempt {attempt}/{MAX_RETRIES} failed: {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    print("[bluesky] ERROR: post not created after all retries.")
    return False


def update_profile(description: str) -> bool:
    """
    Update the profile description (bio).
    Returns True on success.
    """
    did, jwt = _get_session()

    # Step 1: Get current profile
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(
                f"{API_BASE}/com.atproto.repo.getRecord",
                headers={"Authorization": f"Bearer {jwt}"},
                params={
                    "repo": did,
                    "collection": "app.bsky.actor.profile",
                    "rkey": "self"
                },
                timeout=15
            )
            resp.raise_for_status()
            current_profile = resp.json()["value"]

            # Step 2: Update description field
            current_profile["description"] = description

            # Step 3: Write it back
            resp = requests.post(
                f"{API_BASE}/com.atproto.repo.putRecord",
                headers={"Authorization": f"Bearer {jwt}"},
                json={
                    "repo": did,
                    "collection": "app.bsky.actor.profile",
                    "rkey": "self",
                    "record": current_profile
                },
                timeout=15
            )
            resp.raise_for_status()
            print("[bluesky] Profile description updated successfully.")
            return True

        except requests.exceptions.RequestException as exc:
            print(f"[bluesky] Profile update attempt {attempt}/{MAX_RETRIES} failed: {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

    print("[bluesky] ERROR: profile not updated after all retries.")
    return False
