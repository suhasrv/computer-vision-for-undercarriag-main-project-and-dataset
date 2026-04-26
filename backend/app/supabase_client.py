"""
Supabase client helpers for storage, auth, and database operations.

This module provides lightweight async helpers that call Supabase's REST
and Storage APIs using the configured service role key. It is intentionally
simple and uses `httpx` for HTTP calls so it works without relying on the
JS client runtime.
"""
import os
import logging
import json
import uuid
import datetime
from typing import Optional, List, Dict, Any

import httpx
from supabase import create_client, Client

from app.config import (
    SUPABASE_URL,
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_ANON_KEY,
    DETECTIONS_TABLE,
    STORAGE_BUCKET,
    JOBS_TABLE,
)

logger = logging.getLogger(__name__)

# Global Supabase client (high-level Python client) — optional usage.
supabase: Optional[Client] = None


def init_supabase() -> Optional[Client]:
    """Initialise the Supabase Python client using the service role key.
    Returns the client instance or None on failure.
    """
    global supabase
    if supabase is not None:
        return supabase

    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        logger.warning("Supabase credentials not configured")
        return None

    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        logger.info("Supabase client created")
        return supabase
    except Exception as e:
        logger.error(f"Failed to create Supabase client: {e}")
        return None


def is_supabase_available() -> bool:
    # Ensure a boolean is returned (avoid returning the raw key string)
    return bool(supabase is not None or (bool(SUPABASE_URL) and bool(SUPABASE_SERVICE_ROLE_KEY)))


async def verify_token_get_user(token: str) -> Optional[Dict[str, Any]]:
    """Verify an access token by calling Supabase Auth user endpoint.
    Returns user dict when valid, otherwise None.
    """
    if not token:
        return None
    url = f"{SUPABASE_URL}/auth/v1/user"
    headers = {
        "Authorization": f"Bearer {token}",
        "apikey": SUPABASE_ANON_KEY,
    }
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, headers=headers, timeout=30.0)
            if r.status_code == 200:
                return r.json()
            logger.debug(f"verify_token_get_user failed: {r.status_code} {r.text}")
            return None
        except Exception as e:
            logger.error(f"verify_token_get_user error: {e}")
            return None


async def sign_up_user(email: str, password: str) -> Dict[str, Any]:
    """Sign up a user via Supabase Auth (returns the raw response JSON)."""
    url = f"{SUPABASE_URL}/auth/v1/signup"
    headers = {"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"}
    payload = {"email": email, "password": password}
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload, headers=headers, timeout=30.0)
        r.raise_for_status()
        return r.json()


async def sign_in_user(email: str, password: str) -> Dict[str, Any]:
    """Sign in a user and return token payload (access_token, etc.)."""
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    headers = {"apikey": SUPABASE_ANON_KEY, "Content-Type": "application/json"}
    payload = {"email": email, "password": password}
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload, headers=headers, timeout=30.0)
        r.raise_for_status()
        return r.json()


async def upload_image_to_storage(user_id: str, file_content: bytes, original_filename: str, content_type: str) -> (Optional[str], Optional[str]):
    """Upload raw bytes to Supabase Storage and return (path, public_url).

    Uses the service role key so uploads succeed regardless of RLS settings.
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("Supabase not configured")

    timestamp = int(datetime.datetime.utcnow().timestamp())
    safe_name = original_filename.replace(" ", "_")
    object_path = f"{user_id}/{timestamp}_{uuid.uuid4().hex}_{safe_name}"

    url = f"{SUPABASE_URL}/storage/v1/object/{STORAGE_BUCKET}/{object_path}"
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": content_type,
        # allow overwrite when re-uploading same path
        "x-upsert": "true",
    }

    async with httpx.AsyncClient() as client:
        r = await client.put(url, content=file_content, headers=headers, timeout=120.0)
        if r.status_code in (200, 201, 204):
            public_url = f"{SUPABASE_URL}/storage/v1/object/public/{STORAGE_BUCKET}/{object_path}"
            return object_path, public_url
        logger.error(f"Storage upload failed: {r.status_code} {r.text}")
        raise RuntimeError(f"Storage upload failed: {r.status_code}")


async def save_detection_to_database(
    user_id: str,
    image_path: str,
    image_url: str,
    detections: List[Dict[str, Any]],
    image_size: tuple,
    confidence_threshold: float,
    processing_time_ms: float,
) -> Optional[str]:
    """Insert a detection record into the configured table and return the record id."""
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("Supabase not configured")

    url = f"{SUPABASE_URL}/rest/v1/{DETECTIONS_TABLE}"
    payload = {
        "user_id": user_id,
        "image_path": image_path,
        "image_url": image_url,
        "detections": detections,
        "image_width": int(image_size[0]),
        "image_height": int(image_size[1]),
        "confidence_threshold": float(confidence_threshold),
        "processing_time_ms": float(processing_time_ms),
        "created_at": datetime.datetime.utcnow().isoformat(),
    }

    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=[payload], headers=headers, timeout=30.0)
        if r.status_code in (200, 201):
            try:
                data = r.json()
                if isinstance(data, list) and data:
                    return str(data[0].get("id"))
            except Exception:
                logger.exception("Failed to parse DB insert response")
        logger.error(f"DB insert failed: {r.status_code} {r.text}")
        return None


async def create_job(job_id: str, user_id: str, status: str = "pending", meta: Optional[dict] = None):
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("Supabase not configured")
    payload = {"id": job_id, "user_id": user_id, "status": status, "meta": meta or {}, "created_at": datetime.datetime.utcnow().isoformat()}
    url = f"{SUPABASE_URL}/rest/v1/{JOBS_TABLE}"
    headers = {"apikey": SUPABASE_SERVICE_ROLE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}", "Content-Type": "application/json", "Prefer": "return=representation"}
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=[payload], headers=headers, timeout=30.0)
        if r.status_code in (200,201):
            return True
        logger.error(f"create_job failed: {r.status_code} {r.text}")
        return False


async def update_job(job_id: str, **fields):
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("Supabase not configured")
    url = f"{SUPABASE_URL}/rest/v1/{JOBS_TABLE}?id=eq.{job_id}"
    headers = {"apikey": SUPABASE_SERVICE_ROLE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}", "Content-Type": "application/json", "Prefer": "return=representation"}
    async with httpx.AsyncClient() as client:
        r = await client.patch(url, json=fields, headers=headers, timeout=30.0)
        if r.status_code in (200,201):
            try:
                data = r.json()
                return data[0] if isinstance(data, list) and data else data
            except Exception:
                return None
        logger.error(f"update_job failed: {r.status_code} {r.text}")
        return None


async def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("Supabase not configured")
    url = f"{SUPABASE_URL}/rest/v1/{JOBS_TABLE}?id=eq.{job_id}"
    headers = {"apikey": SUPABASE_SERVICE_ROLE_KEY, "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}"}
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers=headers, timeout=30.0)
        if r.status_code == 200:
            data = r.json()
            return data[0] if isinstance(data, list) and data else None
        logger.error(f"get_job failed: {r.status_code} {r.text}")
        return None
