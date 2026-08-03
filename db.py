"""
db.py — Key-value storage wrapper (Upstash Redis via Vercel Marketplace).

NOTE: Vercel KV (the original product) was sunset and replaced by Upstash
Redis, installed via the Vercel Marketplace. Depending on exactly how the
integration is installed, Vercel may inject the connection credentials
under one of two possible naming conventions:

    KV_REST_API_URL / KV_REST_API_TOKEN            (legacy Vercel KV naming,
                                                      kept for backward compatibility)
    UPSTASH_REDIS_REST_URL / UPSTASH_REDIS_REST_TOKEN (Upstash's native naming)

This module checks for both, so it works regardless of which naming your
specific integration uses. After connecting your database on Vercel, check
your project's Environment Variables page to see which pair actually
appears — no code changes should be needed either way.

For local testing without a real database connected, this module falls
back to an in-memory dictionary (data will NOT persist between runs, but
lets you test the full flow locally before deploying).
"""

import os
import json
import uuid
import datetime
import requests

KV_URL = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
KV_TOKEN = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")

# Local fallback store (used only when no database env vars are set — e.g. local dev)
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


def kv_list_keys(prefix: str = "session:"):
    """
    Lists all keys matching the given prefix, using Upstash's REST SCAN-based
    /keys endpoint. Used by the admin viewer page to enumerate all saved
    records.
    """
    if _kv_available():
        resp = requests.get(
            f"{KV_URL}/keys/{prefix}*",
            headers={"Authorization": f"Bearer {KV_TOKEN}"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("result", [])
    else:
        return [k for k in _local_store if k.startswith(prefix)]


def kv_delete(key: str):
    """Deletes the value stored under the given key."""
    if _kv_available():
        resp = requests.get(
            f"{KV_URL}/del/{key}",
            headers={"Authorization": f"Bearer {KV_TOKEN}"},
            timeout=10,
        )
        resp.raise_for_status()
    else:
        _local_store.pop(key, None)


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
    """Lets the app warn the user if no real database is connected (local dev mode)."""
    return not _kv_available()
