"""
db.py — Vercel KV storage wrapper.

Vercel KV is accessed via a simple REST API, so it works from any language
(including this Python/Flask backend), not just Node.js. When you connect
a KV database to your Vercel project, Vercel automatically provides these
two environment variables — you do not need to create them manually:

    KV_REST_API_URL
    KV_REST_API_TOKEN

For local testing without a real Vercel KV instance, this module falls
back to an in-memory dictionary (data will NOT persist between runs, but
lets you test the full flow locally before deploying).
"""

import os
import json
import uuid
import datetime
import requests

KV_URL = os.environ.get("KV_REST_API_URL")
KV_TOKEN = os.environ.get("KV_REST_API_TOKEN")

# Local fallback store (used only when KV env vars are not set — e.g. local dev)
_local_store = {}


def _kv_available() -> bool:
    return bool(KV_URL and KV_TOKEN)


def kv_set(key: str, value: dict):
    """Stores a JSON-serialisable dict under the given key."""
    payload = json.dumps(value, default=str)
    if _kv_available():
        resp = requests.post(
            f"{KV_URL}/set/{key}",
            headers={"Authorization": f"Bearer {KV_TOKEN}"},
            data=payload,
            timeout=10,
        )
        resp.raise_for_status()
    else:
        _local_store[key] = payload


def kv_get(key: str):
    """Retrieves and JSON-decodes the value stored under the given key, or None."""
    if _kv_available():
        resp = requests.get(
            f"{KV_URL}/get/{key}",
            headers={"Authorization": f"Bearer {KV_TOKEN}"},
            timeout=10,
        )
        resp.raise_for_status()
        result = resp.json().get("result")
        return json.loads(result) if result else None
    else:
        raw = _local_store.get(key)
        return json.loads(raw) if raw else None


def save_session_record(record: dict) -> str:
    """
    Saves a full session record under a unique key: session:<uuid>.
    Returns the session_id used as the key suffix.
    """
    session_id = str(uuid.uuid4())
    record["session_id"] = session_id
    record["saved_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    kv_set(f"session:{session_id}", record)
    return session_id


def is_using_local_fallback() -> bool:
    """Lets the app warn the user if KV isn't configured (local dev mode)."""
    return not _kv_available()
