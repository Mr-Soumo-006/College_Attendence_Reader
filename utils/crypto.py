"""
HMAC signing utilities for QR code integrity.
"""

import hmac
import hashlib
from config.settings import QR_SECRET_KEY


def sign(payload: str) -> str:
    """Return a 16-character hex HMAC-SHA256 digest of *payload*."""
    key = QR_SECRET_KEY.encode("utf-8")
    mac = hmac.new(key, payload.encode("utf-8"), hashlib.sha256)
    return mac.hexdigest()[:16]


def verify(payload: str, signature: str) -> bool:
    """Return True if *signature* matches the expected HMAC for *payload*."""
    expected = sign(payload)
    return hmac.compare_digest(expected, signature)
