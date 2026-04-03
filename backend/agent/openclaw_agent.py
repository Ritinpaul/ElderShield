"""
OpenClaw Background Agent — L1
═══════════════════════════════
Intercepts all incoming messages before delivery to the elderly user.
Built on the OpenClaw autonomous agent framework principles.

Responsibilities:
  - Monitor incoming channels (WhatsApp, SMS, Email, Voice)
  - Normalize diverse message formats into a unified schema
  - Queue messages for L2 classification
  - Maintain real-time intercept log

Constraints (enforced by L4 ArmorClaw):
  - Read-only access to user data
  - Cannot modify messages before quarantine decision
  - Cannot exfiltrate data to external endpoints
"""

import asyncio
import logging
from datetime import datetime, timezone
from uuid import uuid4

from backend.models.schemas import RawMessage, NormalizedMessage, Channel
from backend.agent.normalizer import MessageNormalizer
from backend.database.db import Database

logger = logging.getLogger("eldershield.l1")


class OpenClawAgent:
    """
    Background daemon that intercepts communications in real time.

    The agent sits between the communication channel and the user,
    ensuring every message is analyzed before it reaches the elderly
    individual. Think of it as a mail room that x-rays every package.

    Usage:
        db = Database()
        queue = asyncio.Queue()
        agent = OpenClawAgent(db, queue)
        await agent.start()  # Runs forever, monitoring all channels
    """

    def __init__(self, db: Database, classifier_queue: asyncio.Queue):
        self.db = db
        self.queue = classifier_queue
        self.normalizer = MessageNormalizer()
        self.running = False
        self._intercepted_count = 0
        self._start_time = None

    # ── Lifecycle ──────────────────────────────────────────────

    async def start(self):
        """Start the background interception daemon."""
        self.running = True
        self._start_time = datetime.now(timezone.utc)
        logger.info("🛡️  OpenClaw Agent started — monitoring all channels")
        logger.info("    Channels: WhatsApp · SMS · Email · Voice")

        # Run all channel monitors concurrently
        await asyncio.gather(
            self._monitor_whatsapp(),
            self._monitor_sms(),
            self._monitor_email(),
            self._monitor_voice_calls(),
        )

    async def stop(self):
        """Gracefully stop the agent."""
        self.running = False
        logger.info(
            f"🛑 OpenClaw Agent stopped — "
            f"intercepted {self._intercepted_count} messages"
        )

    # ── Core Interception ─────────────────────────────────────

    async def intercept(self, raw: RawMessage) -> NormalizedMessage:
        """
        Core interception method — INTERCEPT → NORMALIZE → QUEUE.

        This is the main entry point for all messages, whether they
        come from channel monitors or from the /api/intercept endpoint.

        Args:
            raw: Raw message from any communication channel

        Returns:
            NormalizedMessage: Unified message ready for L2 classification
        """
        # Generate unique ID and timestamp
        msg_id = str(uuid4())
        intercepted_at = datetime.now(timezone.utc).isoformat()

        # Step 1: Log the raw intercept event
        await self.db.log_intercept_event(msg_id, raw, intercepted_at)

        # Step 2: Normalize into unified schema
        normalized = await self.normalizer.normalize(raw, msg_id, intercepted_at)

        # Step 3: Enqueue for L2 classification
        await self.queue.put(normalized)

        # Step 4: Update stats
        self._intercepted_count += 1
        await self.db.increment_stat("total_intercepted")

        logger.info(
            f"[L1] Intercepted {raw.channel.value} message | "
            f"ID: {msg_id[:8]}... | "
            f"Sender: {raw.sender} | "
            f"Total: {self._intercepted_count}"
        )

        return normalized

    # ── Channel Monitors ──────────────────────────────────────
    # These are stubs for the hackathon demo. In production,
    # each would connect to the actual communication platform.

    async def _monitor_whatsapp(self):
        """
        WhatsApp monitoring stub.

        Production implementation:
          - Use Baileys (open-source WhatsApp API) or
          - Android accessibility service to read notifications
          - whatsapp-web.js for web-based interception
        """
        logger.debug("[L1] WhatsApp monitor active (stub)")
        while self.running:
            await asyncio.sleep(0.5)

    async def _monitor_sms(self):
        """
        SMS monitoring stub.

        Production implementation:
          - ADB bridge for Android device SMS reading
          - Twilio webhook for cloud-based SMS interception
          - Android SMS Content Provider via accessibility
        """
        logger.debug("[L1] SMS monitor active (stub)")
        while self.running:
            await asyncio.sleep(0.5)

    async def _monitor_email(self):
        """
        Email monitoring stub.

        Production implementation:
          - IMAP IDLE for real-time email notification
          - Gmail API via OAuth for Google accounts
          - Microsoft Graph API for Outlook
        """
        logger.debug("[L1] Email monitor active (stub)")
        while self.running:
            await asyncio.sleep(1.0)

    async def _monitor_voice_calls(self):
        """
        Voice call monitoring stub.

        Production implementation:
          - Android CallScreeningService API
          - Twilio Programmable Voice for cloud interception
          - Real-time audio stream → Whisper ASR → text classification
        """
        logger.debug("[L1] Voice call monitor active (stub)")
        while self.running:
            await asyncio.sleep(0.5)

    # ── Status ────────────────────────────────────────────────

    @property
    def status(self) -> dict:
        """Return agent status for dashboard display."""
        uptime = None
        if self._start_time:
            delta = datetime.now(timezone.utc) - self._start_time
            uptime = str(delta).split(".")[0]  # Remove microseconds

        return {
            "running": self.running,
            "intercepted_count": self._intercepted_count,
            "uptime": uptime,
            "channels": ["whatsapp", "sms", "email", "voice"],
        }
