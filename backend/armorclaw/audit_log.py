"""
ArmorClaw Audit Log — Immutable SQLite Audit Trail
════════════════════════════════════════════════════
Every quarantine action signed by ArmorClaw is permanently recorded
in the audit log. This log cannot be modified or deleted — enforced
by SQLite BEFORE UPDATE and BEFORE DELETE triggers.

Why immutability matters for elder safety:
  If a scammer ever gains access to the system, they cannot
  retroactively erase evidence of their attack from the audit trail.
  The log is a forensic record of every action ElderShield took.

Log entry fields:
  message_id       — UUID of the intercepted message
  action           — quarantine / hold_for_review / deliver
  confidence       — float [0,1] from L2 classifier
  reason           — reason code from classifier
  signature        — HMAC-SHA256 hex from L4 signer
  timestamp        — ISO 8601 UTC timestamp
  injection_detected — bool: was a prompt injection attempt caught?

Immutability triggers are set up by db.py during initialization.
This module only performs INSERT and SELECT operations.
"""

import logging
from datetime import datetime, timezone

import aiosqlite

from backend.models.schemas import AuditEntry

logger = logging.getLogger("eldershield.l4.audit_log")

DB_PATH = "eldershield.db"


async def record(
    message_id: str,
    action: str,
    confidence: float,
    reason: str,
    signature: str,
    timestamp: str,
    injection_detected: bool = False,
) -> None:
    """
    Write an immutable audit log entry to SQLite.

    Never raises — errors are logged but do not halt the pipeline.
    An audit failure should never prevent a quarantine action from
    being recorded elsewhere.
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                """
                INSERT INTO audit_log
                  (message_id, action, confidence, reason, signature, timestamp, injection_detected)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    action,
                    round(confidence, 4),
                    reason,
                    signature,
                    timestamp,
                    1 if injection_detected else 0,
                ),
            )
            await db.commit()

        logger.info(
            f"[L4/AuditLog] Recorded: msg={message_id[:8]}... | "
            f"action={action} | sig={signature[:16]}..."
        )

    except Exception as e:
        logger.error(f"[L4/AuditLog] Failed to write audit entry for {message_id}: {e}")


async def get_all(limit: int = 100) -> list[AuditEntry]:
    """
    Retrieve the most recent audit log entries.

    Args:
        limit: Maximum number of entries to return (default 100)

    Returns:
        List of AuditEntry objects, newest first.
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT message_id, action, confidence, reason, signature,
                       timestamp, injection_detected
                FROM audit_log
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()

        return [
            AuditEntry(
                message_id=row["message_id"],
                action=row["action"],
                confidence=row["confidence"],
                reason=row["reason"],
                signature=row["signature"],
                timestamp=row["timestamp"],
                injection_detected=bool(row["injection_detected"]),
            )
            for row in rows
        ]

    except Exception as e:
        logger.error(f"[L4/AuditLog] Failed to read audit log: {e}")
        return []


async def get_stats() -> dict:
    """
    Aggregate statistics over the entire audit log for the dashboard.

    Returns dict with keys:
      total_intercepted, total_blocked, total_suspicious,
      total_safe, injection_attempts, avg_confidence
    """
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT
                  COUNT(*) AS total,
                  SUM(CASE WHEN action = 'quarantine' THEN 1 ELSE 0 END) AS blocked,
                  SUM(CASE WHEN action = 'hold_for_review' THEN 1 ELSE 0 END) AS suspicious,
                  SUM(CASE WHEN action = 'deliver' THEN 1 ELSE 0 END) AS safe,
                  SUM(injection_detected) AS injections,
                  AVG(confidence) AS avg_conf
                FROM audit_log
                """
            ) as cursor:
                row = await cursor.fetchone()

        if not row or row["total"] == 0:
            return {
                "total_intercepted": 0,
                "total_blocked": 0,
                "total_suspicious": 0,
                "total_safe": 0,
                "injection_attempts": 0,
                "avg_confidence": 0.0,
            }

        return {
            "total_intercepted": row["total"] or 0,
            "total_blocked": row["blocked"] or 0,
            "total_suspicious": row["suspicious"] or 0,
            "total_safe": row["safe"] or 0,
            "injection_attempts": row["injections"] or 0,
            "avg_confidence": round(row["avg_conf"] or 0.0, 3),
        }

    except Exception as e:
        logger.error(f"[L4/AuditLog] Stats query failed: {e}")
        return {}
