"""
ElderShield — Database Layer (SQLite + aiosqlite)
══════════════════════════════════════════════════
Async SQLite database for:
  - Intercept event log (L1)
  - Audit trail (L4)
  - Dashboard statistics (L5)

All tables are append-friendly. The audit_log table is
protected by triggers that prevent UPDATE and DELETE.
"""

import os
import logging
from datetime import datetime, timezone

import aiosqlite

logger = logging.getLogger("eldershield.db")

DB_PATH = os.getenv("DB_PATH", "./eldershield.db")


class Database:
    """
    Async SQLite wrapper for ElderShield.

    Usage:
        db = Database()
        await db.initialize()
        await db.log_intercept_event(msg_id, raw, timestamp)
    """

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or DB_PATH

    # ── Schema Initialization ─────────────────────────────────

    async def initialize(self):
        """
        Create all tables and triggers.
        Safe to call multiple times (IF NOT EXISTS).
        """
        async with aiosqlite.connect(self.db_path) as db:

            # ── Intercept Events (L1) ─────────────────────────
            await db.execute("""
                CREATE TABLE IF NOT EXISTS intercept_events (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id  TEXT    NOT NULL UNIQUE,
                    channel     TEXT    NOT NULL,
                    sender      TEXT    NOT NULL,
                    text        TEXT,
                    audio_url   TEXT,
                    raw_format  TEXT,
                    intercepted_at TEXT NOT NULL,
                    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
                )
            """)

            # ── Audit Log (L4) — Immutable ────────────────────
            await db.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                    message_id         TEXT    NOT NULL,
                    action             TEXT    NOT NULL,
                    confidence         REAL    NOT NULL,
                    reason             TEXT    NOT NULL,
                    signature          TEXT    NOT NULL,
                    timestamp          TEXT    NOT NULL,
                    injection_detected BOOLEAN DEFAULT FALSE,
                    source_channel     TEXT,
                    source_sender      TEXT
                )
            """)

            # Backward-compatible migration for existing databases
            async with db.execute("PRAGMA table_info(audit_log)") as cursor:
                cols = {row[1] for row in await cursor.fetchall()}

            if "source_channel" not in cols:
                await db.execute("ALTER TABLE audit_log ADD COLUMN source_channel TEXT")
            if "source_sender" not in cols:
                await db.execute("ALTER TABLE audit_log ADD COLUMN source_sender TEXT")

            # ── Immutability Triggers ─────────────────────────
            # These triggers prevent any UPDATE or DELETE on the
            # audit_log table, making it a true append-only log.
            await db.execute("""
                CREATE TRIGGER IF NOT EXISTS prevent_audit_update
                BEFORE UPDATE ON audit_log
                BEGIN
                    SELECT RAISE(ABORT, 'ArmorClaw: audit log is immutable — UPDATE denied');
                END
            """)

            await db.execute("""
                CREATE TRIGGER IF NOT EXISTS prevent_audit_delete
                BEFORE DELETE ON audit_log
                BEGIN
                    SELECT RAISE(ABORT, 'ArmorClaw: audit log is immutable — DELETE denied');
                END
            """)

            # ── Dashboard Stats Cache ─────────────────────────
            await db.execute("""
                CREATE TABLE IF NOT EXISTS stats (
                    key   TEXT PRIMARY KEY,
                    value INTEGER NOT NULL DEFAULT 0
                )
            """)

            # Seed default stats
            for key in [
                "total_intercepted", "total_blocked",
                "total_suspicious", "total_safe",
                "injection_attempts",
            ]:
                await db.execute(
                    "INSERT OR IGNORE INTO stats (key, value) VALUES (?, 0)", (key,)
                )

            # ── Phone Reputation Cache (L1.5 — PhoneReputationAgent) ──
            await db.execute("""
                CREATE TABLE IF NOT EXISTS phone_reputation (
                    phone_number   TEXT NOT NULL PRIMARY KEY,
                    label          TEXT NOT NULL DEFAULT 'UNKNOWN',
                    incident_count INTEGER NOT NULL DEFAULT 1,
                    last_seen_at   TEXT NOT NULL
                )
            """)

            await db.commit()
            logger.info("✅ Database initialized — all tables and triggers ready")

    # ── L1: Intercept Events ──────────────────────────────────

    async def log_intercept_event(
        self,
        message_id: str,
        raw,  # RawMessage
        intercepted_at: str,
    ):
        """Log a raw message interception event (L1)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT INTO intercept_events
                   (message_id, channel, sender, text, audio_url, raw_format, intercepted_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    message_id,
                    raw.channel.value if hasattr(raw.channel, 'value') else raw.channel,
                    raw.sender,
                    raw.text,
                    raw.audio_url,
                    raw.format,
                    intercepted_at,
                ),
            )
            await db.commit()
            logger.debug(f"[DB] Logged intercept event: {message_id[:8]}...")

    # ── L4: Audit Log ─────────────────────────────────────────

    async def write_audit(self, entry) -> int:
        """
        Append an audit entry. Returns the new row ID.
        Cannot be modified or deleted (triggers enforce immutability).
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """INSERT INTO audit_log
                   (message_id, action, confidence, reason, signature, timestamp, injection_detected, source_channel, source_sender)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    entry.message_id,
                    entry.action,
                    entry.confidence,
                    entry.reason,
                    entry.signature,
                    entry.timestamp,
                    entry.injection_detected,
                    getattr(entry, "source_channel", None),
                    getattr(entry, "source_sender", None),
                ),
            )
            await db.commit()
            row_id = cursor.lastrowid
            logger.debug(f"[DB] Audit entry #{row_id} written for {entry.message_id[:8]}...")
            return row_id

    async def get_recent_audits(self, limit: int = 50) -> list[dict]:
        """Fetch the most recent audit log entries."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM audit_log ORDER BY id DESC LIMIT ?", (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    # ── L5: Dashboard Stats ───────────────────────────────────

    async def increment_stat(self, key: str, amount: int = 1):
        """Atomically increment a stats counter."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE stats SET value = value + ? WHERE key = ?", (amount, key)
            )
            await db.commit()

    async def get_stats(self) -> dict[str, int]:
        """Get all dashboard stats as a dictionary."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT key, value FROM stats") as cursor:
                rows = await cursor.fetchall()
                return {row["key"]: row["value"] for row in rows}

    # ── Utilities ─────────────────────────────────────────────

    async def get_intercept_count(self) -> int:
        """Total number of intercepted messages."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM intercept_events") as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def get_message_by_id(self, message_id: str) -> dict | None:
        """Fetch a specific intercepted message by its ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM intercept_events WHERE message_id = ?", (message_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    # ── L1.5: Phone Reputation (PhoneReputationAgent) ─────────

    async def get_phone_reputation(self, phone_number: str) -> dict | None:
        """Lookup reputation record for a phone number. Returns None if unknown."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM phone_reputation WHERE phone_number = ?", (phone_number,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def upsert_phone_reputation(
        self,
        phone_number: str,
        label: str,  # 'SCAMMER' | 'TRUSTED' | 'UNKNOWN'
        last_seen_at: str,
    ) -> None:
        """Insert or update a phone number reputation record."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO phone_reputation (phone_number, label, incident_count, last_seen_at)
                VALUES (?, ?, 1, ?)
                ON CONFLICT(phone_number) DO UPDATE SET
                    label = excluded.label,
                    incident_count = incident_count + 1,
                    last_seen_at = excluded.last_seen_at
                """,
                (phone_number, label, last_seen_at),
            )
            await db.commit()
            logger.debug(f"[DB] Phone reputation upserted: {phone_number} -> {label}")

    # ── L0: Sentinel History (SentinelAgent) ───────────────────

    async def get_sender_history(
        self,
        sender: str,
        hours: int = 24,
    ) -> list[dict]:
        """
        Fetch all intercept events from a sender within the last N hours.
        Used by SentinelAgent for temporal pattern analysis.
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT message_id, channel, sender, intercepted_at
                FROM intercept_events
                WHERE sender = ?
                  AND datetime(intercepted_at) >= datetime('now', ? || ' hours')
                ORDER BY intercepted_at DESC
                """,
                (sender, f"-{hours}"),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_recent_senders(
        self,
        minutes: int = 5,
        min_messages: int = 3,
    ) -> list[dict]:
        """
        Find senders who sent >= min_messages in the last N minutes.
        Used by SentinelAgent to detect volumetric/burst attacks.
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT sender, COUNT(*) as message_count, MAX(intercepted_at) as last_seen
                FROM intercept_events
                WHERE datetime(intercepted_at) >= datetime('now', ? || ' minutes')
                GROUP BY sender
                HAVING COUNT(*) >= ?
                ORDER BY message_count DESC
                """,
                (f"-{minutes}", min_messages),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
