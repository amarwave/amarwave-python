"""
AmarWave — HMAC-SHA256 signing utility.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import string


def hmac_sha256(secret: str, message: str) -> str:
    """Return HMAC-SHA256 of `message` signed with `secret` as lowercase hex."""
    return hmac.new(
        secret.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()


def generate_uid(length: int = 16) -> str:
    """Generate a random alphanumeric ID."""
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))
