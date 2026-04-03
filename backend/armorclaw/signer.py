"""
ArmorClaw Signer — HMAC-SHA256 Cryptographic Layer
════════════════════════════════════════════════════
Every quarantine action is cryptographically signed before it is
stored in the audit log or sent to the family dashboard.

Why HMAC-SHA256?
  - No external library required (Python stdlib `hmac` + `hashlib`)
  - Tamper-evident: any modification to the action data invalidates the signature
  - Verifiable by any system with the shared secret
  - Production upgrade path → Ed25519 asymmetric signatures

Secret key:
  Set ARMORCLAW_SECRET in .env (min 32 characters).
  Falls back to a randomly generated session key if not set (demo-safe but
  signatures will not verify across restarts — fine for hackathon).

Canonical signing payload:
  "{message_id}|{action}|{confidence:.4f}|{reason}|{timestamp}"
  This covers all fields that change the meaning of a quarantine decision.
"""

import hmac
import hashlib
import os
import secrets
import logging
from datetime import datetime, timezone

logger = logging.getLogger("eldershield.l4.signer")

# Load or generate secret once at import time
_SECRET_RAW = os.getenv("ARMORCLAW_SECRET", "")
if _SECRET_RAW and len(_SECRET_RAW) >= 16:
    _SECRET_KEY: bytes = _SECRET_RAW.encode("utf-8")
    logger.info("[L4/Signer] Loaded ARMORCLAW_SECRET from environment")
else:
    _SESSION_KEY = secrets.token_hex(32)
    _SECRET_KEY = _SESSION_KEY.encode("utf-8")
    logger.warning(
        "[L4/Signer] ARMORCLAW_SECRET not set or too short — "
        "using ephemeral session key (signatures will not persist across restarts)"
    )


def _canonical_payload(
    message_id: str,
    action: str,
    confidence: float,
    reason: str,
    timestamp: str,
) -> str:
    """Build a deterministic string to sign."""
    return f"{message_id}|{action}|{confidence:.4f}|{reason}|{timestamp}"


def sign(
    message_id: str,
    action: str,
    confidence: float,
    reason: str,
    timestamp: str | None = None,
) -> tuple[str, str]:
    """
    Sign a quarantine action.

    Returns:
        (signature_hex, timestamp) — timestamp is either provided or generated now.

    Raises:
        ValueError: If message_id or action is empty.
    """
    if not message_id or not action:
        raise ValueError("message_id and action must be non-empty for signing")

    ts = timestamp or datetime.now(timezone.utc).isoformat()
    payload = _canonical_payload(message_id, action, confidence, reason, ts)

    mac = hmac.new(_SECRET_KEY, payload.encode("utf-8"), hashlib.sha256)
    sig = mac.hexdigest()

    logger.debug(
        f"[L4/Signer] Signed action | "
        f"msg={message_id[:8]}... | action={action} | sig={sig[:16]}..."
    )

    return sig, ts


def verify(
    message_id: str,
    action: str,
    confidence: float,
    reason: str,
    timestamp: str,
    signature: str,
) -> bool:
    """
    Verify a previously signed quarantine action.

    Uses `hmac.compare_digest` to prevent timing attacks.

    Returns:
        True if signature is valid, False otherwise.
    """
    payload = _canonical_payload(message_id, action, confidence, reason, timestamp)
    mac = hmac.new(_SECRET_KEY, payload.encode("utf-8"), hashlib.sha256)
    expected = mac.hexdigest()

    result = hmac.compare_digest(expected, signature)
    if not result:
        logger.warning(
            f"[L4/Signer] Signature MISMATCH for msg={message_id[:8]}... "
            f"— action may have been tampered with!"
        )
    return result
