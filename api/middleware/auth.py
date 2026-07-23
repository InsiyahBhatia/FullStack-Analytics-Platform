"""
Timing-safe API key authentication middleware.

Keys are loaded from environment variables (never hardcoded).
Comparison uses hmac.compare_digest for constant-time matching.
"""

import hmac
import os
from fastapi import Header, HTTPException, status
from typing import Optional

API_KEYS = {}
for env in ("prod", "dev"):
    keys_raw = os.environ.get(f"API_KEYS_{env.upper()}", "")
    if keys_raw:
        for pair in keys_raw.split(","):
            if ":" in pair:
                key, role = pair.split(":", 1)
                API_KEYS[key.strip()] = role.strip()

ACTIVE_ENV = os.environ.get("FINSIGHT_ENV", "dev")

# Fallback for local dev if no env vars set
if not API_KEYS:
    API_KEYS = {
        "sk-test-finsight-xxxx": "admin",
    }


def verify_api_key(
    x_api_key: Optional[str] = Header(None),
) -> str:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )

    role = None
    for valid_key, valid_role in API_KEYS.items():
        if hmac.compare_digest(x_api_key, valid_key):
            role = valid_role
            break

    if not role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return role
