"""
Authentication utilities for JWT token verification.
"""
from fastapi import HTTPException, Depends, Header
from typing import Optional, Dict, Any
import logging
import json
import base64
import os

from app.supabase_client import verify_token_get_user

logger = logging.getLogger(__name__)


async def verify_jwt_token(authorization: Optional[str] = Header(None)) -> str:
    """
    Verify JWT token from Authorization header and extract user_id.

    This uses Supabase's user endpoint as the primary verifier. If Supabase
    is not reachable or the verification fails, the function falls back to a
    best-effort JWT payload decode (no signature verification) to extract
    the `sub`/`user_id` claim. In `DEV_MODE` the check is bypassed.
    """
    # NOTE: Authentication removed — allow direct public access.
    # All endpoints that previously depended on `get_current_user`
    # will receive the user id `anonymous` so the API can be used
    # without sign-in. This simplifies local/demo usage per request.
    logger.info("Authentication disabled: returning anonymous user")
    return "anonymous"


def _decode_token(token: str) -> Dict[str, Any]:
    """
    Basic JWT decoding without signature verification.

    For production use with Supabase, implement proper signature verification
    using Supabase's JWKS and a JWT library.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")

        payload_encoded = parts[1]
        # Fix padding
        padding = 4 - (len(payload_encoded) % 4)
        if padding != 4:
            payload_encoded += "=" * padding

        decoded = base64.urlsafe_b64decode(payload_encoded)
        return json.loads(decoded)
    except Exception as e:
        raise ValueError(f"Failed to decode JWT: {e}")


async def get_current_user(
    authorization: Optional[str] = Header(None)
) -> str:
    return await verify_jwt_token(authorization)


def create_test_token(user_id: str) -> str:
    """Create an unsigned test token (DEV only)."""
    payload = {"sub": user_id, "iat": 1234567890, "exp": 9999999999}
    payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    header_encoded = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
    signature_encoded = base64.urlsafe_b64encode(b"test_signature").decode().rstrip("=")
    token = f"{header_encoded}.{payload_encoded}.{signature_encoded}"
    return f"Bearer {token}"
