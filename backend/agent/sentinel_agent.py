"""
SentinelAgent — L0 Temporal Pattern Monitor
=============================================
Runs as a background task independently of the main message pipeline.

The Hallucination Problem it Solves:
  Individual-message classifiers process each message in isolation.
  A patient scammer who sends 4 "innocent-looking" messages (each BENIGN)
  before a final SCAM message defeats per-message classifiers entirely.
  The Sentinel has MEMORY — it watches patterns ACROSS messages over time.

What it does (runs every 60 seconds):
  1. Queries database for senders with ≥3 messages in the last 5 minutes
     → Burst/volumetric attack detection
  2. Queries database for senders with ≥3 SUSPICIOUS messages in 24h
     → Slow-burn social engineering detection
  3. For flagged senders:
     - Marks them as SCAMMER in phone_reputation DB
     - Broadcasts a SENTINEL_ALERT to the family dashboard WebSocket
     - Logs a HIGH severity alert to the audit trail

This is DETERMINISTIC analysis — purely database queries + counting logic.
No LLM is involved, so zero hallucination is possible.

Retroactive protection:
  If SentinelAgent flags a sender, future messages from that number
  get a 0.90 prior from PhoneReputationAgent — meaning the LLM pipeline
  will treat them with maximum suspicion automatically.
"""

import asyncio
import logging
import json
from datetime import datetime, timezone
from typing import Callable, Awaitable

from backend.database.db import Database

logger = logging.getLogger("eldershield.l0.sentinel")

# Tunable thresholds
BURST_WINDOW_MINUTES = 5       # Time window for burst detection
BURST_MIN_MESSAGES = 3        # Min messages in window to flag as volumetric
SLOW_BURN_WINDOW_HOURS = 24   # Time window for slow-burn detection
SLOW_BURN_MIN_SUSPICIOUS = 3  # Min suspicious messages in 24h to flag
SCAN_INTERVAL_SECONDS = 60    # How often SentinelAgent scans


class SentinelAgent:
    """
    L0 — Background temporal pattern monitor.

    Detects multi-message attack campaigns that per-message classifiers miss.

    Usage (in main.py lifespan):
        sentinel = SentinelAgent(db, broadcast_fn=ws_manager.broadcast)
        sentinel_task = asyncio.create_task(sentinel.run())
        # On shutdown:
        sentinel_task.cancel()
    """

    def __init__(
        self,
        db: Database,
        broadcast_fn: Callable[[str], Awaitable[None]] | None = None,
    ):
        self.db = db
        self.broadcast = broadcast_fn  # WebSocket broadcast function
        self._running = False
        self._alerts_sent: set[str] = set()  # Prevent duplicate alerts per sender

    async def run(self):
        """Main background loop. Runs every SCAN_INTERVAL_SECONDS."""
        self._running = True
        logger.info(
            f"[L0/Sentinel] 🛡️ Started — scanning every {SCAN_INTERVAL_SECONDS}s | "
            f"Burst: ≥{BURST_MIN_MESSAGES} msgs in {BURST_WINDOW_MINUTES}min | "
            f"Slow-burn: ≥{SLOW_BURN_MIN_SUSPICIOUS} suspicious in {SLOW_BURN_WINDOW_HOURS}h"
        )

        while self._running:
            try:
                await self._scan()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[L0/Sentinel] Error during scan: {e}")

            try:
                await asyncio.sleep(SCAN_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break

        logger.info("[L0/Sentinel] Stopped.")

    async def stop(self):
        """Gracefully stop the sentinel."""
        self._running = False

    async def _scan(self):
        """Run one complete scan cycle."""
        now = datetime.now(timezone.utc)
        logger.debug(f"[L0/Sentinel] Scanning at {now.strftime('%H:%M:%S')}...")

        burst_flags = await self._detect_burst_attacks()
        slow_burn_flags = await self._detect_slow_burn_attacks()

        all_flags = burst_flags + slow_burn_flags

        if all_flags:
            logger.warning(
                f"[L0/Sentinel] 🚨 {len(all_flags)} sender(s) flagged this cycle"
            )
            for flag in all_flags:
                await self._handle_flag(flag)
        else:
            logger.debug("[L0/Sentinel] ✅ No suspicious patterns detected.")

    async def _detect_burst_attacks(self) -> list[dict]:
        """
        Detect volumetric / burst attacks:
        Senders who sent ≥BURST_MIN_MESSAGES messages in the last BURST_WINDOW_MINUTES.
        """
        try:
            senders = await self.db.get_recent_senders(
                minutes=BURST_WINDOW_MINUTES,
                min_messages=BURST_MIN_MESSAGES,
            )
        except Exception as e:
            logger.warning(f"[L0/Sentinel] Burst detection query failed: {e}")
            return []

        flags = []
        for row in senders:
            sender = row["sender"]
            count = row["message_count"]
            flags.append({
                "sender": sender,
                "type": "BURST_ATTACK",
                "message_count": count,
                "description": f"Burst: {count} messages in {BURST_WINDOW_MINUTES} minutes",
                "severity": "HIGH",
            })
            logger.warning(
                f"[L0/Sentinel] 🚨 BURST ATTACK: {sender} sent {count} messages "
                f"in {BURST_WINDOW_MINUTES} minutes"
            )
        return flags

    async def _detect_slow_burn_attacks(self) -> list[dict]:
        """
        Detect slow-burn social engineering:
        Senders with ≥SLOW_BURN_MIN_SUSPICIOUS suspicious messages in last 24h.
        
        Queries audit_log for HOLD_FOR_REVIEW decisions (which map to SUSPICIOUS/low-conf SCAM)
        grouped by their message sender via join with intercept_events.
        """
        try:
            async_db = self.db
            import aiosqlite
            async with aiosqlite.connect(self.db.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    """
                    SELECT ie.sender, COUNT(al.id) as suspicious_count
                    FROM audit_log al
                    JOIN intercept_events ie ON al.message_id = ie.message_id
                    WHERE (al.action = 'hold_for_review' OR al.action = 'quarantine')
                      AND datetime(al.timestamp) >= datetime('now', '-24 hours')
                    GROUP BY ie.sender
                    HAVING COUNT(al.id) >= ?
                    ORDER BY suspicious_count DESC
                    """,
                    (SLOW_BURN_MIN_SUSPICIOUS,),
                ) as cursor:
                    rows = await cursor.fetchall()
        except Exception as e:
            logger.warning(f"[L0/Sentinel] Slow-burn detection query failed: {e}")
            return []

        flags = []
        for row in rows:
            sender = row["sender"]
            count = row["suspicious_count"]
            flags.append({
                "sender": sender,
                "type": "SLOW_BURN_CAMPAIGN",
                "message_count": count,
                "description": f"Slow-burn: {count} suspicious/blocked messages in 24h",
                "severity": "HIGH",
            })
            logger.warning(
                f"[L0/Sentinel] 🔥 SLOW-BURN CAMPAIGN: {sender} had {count} "
                f"suspicious/blocked messages in 24h"
            )
        return flags

    async def _handle_flag(self, flag: dict):
        """
        Handle a flagged sender:
        1. Upsert as SCAMMER in phone_reputation (future messages auto-blocked)
        2. Broadcast SENTINEL_ALERT to family dashboard
        """
        sender = flag["sender"]
        alert_key = f"{sender}:{flag['type']}"

        # Avoid duplicate alerts in same scan cycle
        if alert_key in self._alerts_sent:
            return
        self._alerts_sent.add(alert_key)

        # Mark as SCAMMER in reputation DB
        now = datetime.now(timezone.utc).isoformat()
        try:
            await self.db.upsert_phone_reputation(sender, "SCAMMER", now)
            logger.info(f"[L0/Sentinel] Marked {sender} as SCAMMER in reputation DB")
        except Exception as e:
            logger.error(f"[L0/Sentinel] Failed to update reputation for {sender}: {e}")

        # Broadcast to family dashboard
        if self.broadcast:
            alert_payload = json.dumps({
                "type": "SENTINEL_ALERT",
                "sender": sender,
                "alert_type": flag["type"],
                "description": flag["description"],
                "severity": flag["severity"],
                "action": "Pattern indicates coordinated attack — number marked as SCAMMER",
                "timestamp": now,
            })
            try:
                await self.broadcast(alert_payload)
                logger.info(
                    f"[L0/Sentinel] 📲 SENTINEL_ALERT broadcast for {sender}: {flag['type']}"
                )
            except Exception as e:
                logger.error(f"[L0/Sentinel] Broadcast failed: {e}")

        # Reset alert cache after 60 min to allow re-alerting
        # (uses a simple size-bounded approach)
        if len(self._alerts_sent) > 1000:
            self._alerts_sent.clear()
