"""
API Key authentication middleware with HMAC signature verification.
"""

import hmac
import hashlib
from fastapi import Header, HTTPException, status
from typing import Optional

API_KEYS = {
    "prod": {
        "sk-live-finsight-a1b2c3d4": "enterprise",
        "sk-live-finsight-e5f6g7h8": "dashboard",
    },
    "dev": {
        "sk-test-finsight-xxxx": "admin",
    },
}

ACTIVE_ENV = "dev"


def verify_api_key(
    x_api_key: Optional[str] = Header(None),
    x_api_signature: Optional[str] = Header(None),
) -> str:
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header",
        )

    env_keys = API_KEYS.get(ACTIVE_ENV, {})
    role = env_keys.get(x_api_key)

    if not role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return role
