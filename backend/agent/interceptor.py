"""
Channel-Specific Interceptors — L1 Sub-Component
═════════════════════════════════════════════════
Interceptor stubs for each communication channel.

In real usage, each interceptor connects to its platform's API
and converts incoming events into RawMessage objects. For the
hackathon demo, messages are injected via the /api/intercept
REST endpoint instead.

Production integration notes are documented in each class.
"""

import logging
from abc import ABC, abstractmethod
from typing import AsyncGenerator

from backend.models.schemas import RawMessage, Channel

logger = logging.getLogger("eldershield.l1.interceptor")


class BaseInterceptor(ABC):
    """Abstract base for all channel interceptors."""

    @abstractmethod
    async def listen(self) -> AsyncGenerator[RawMessage, None]:
        """Yield incoming messages as they arrive."""
        ...

    @abstractmethod
    async def start(self):
        """Start listening on this channel."""
        ...

    @abstractmethod
    async def stop(self):
        """Stop listening on this channel."""
        ...


class WhatsAppInterceptor(BaseInterceptor):
    """
    WhatsApp message interceptor.

    Production options:
      1. Baileys (Node.js) — open-source WhatsApp Web API
         - github.com/WhiskeySockets/Baileys
         - Bridges to Python via subprocess or HTTP
      2. Android Accessibility Service
         - Reads WhatsApp notifications in real-time
         - Requires device-level installation
      3. whatsapp-web.js
         - Headless WhatsApp Web client
         - Good for demo environments
    """

    def __init__(self):
        self.active = False

    async def listen(self) -> AsyncGenerator[RawMessage, None]:
        """Stub: In production, yields WhatsApp messages as they arrive."""
        logger.info("[Interceptor] WhatsApp listener started (stub)")
        self.active = True
        # Production: yield RawMessage from WhatsApp API events
        return
        yield  # Makes this a generator

    async def start(self):
        self.active = True
        logger.info("[Interceptor] WhatsApp interceptor started")

    async def stop(self):
        self.active = False
        logger.info("[Interceptor] WhatsApp interceptor stopped")


class SMSInterceptor(BaseInterceptor):
    """
    SMS message interceptor.

    Production options:
      1. Android ADB bridge
         - Read SMS via `adb shell content query --uri content://sms/inbox`
         - Real-time monitoring via ContentObserver
      2. Twilio Programmable SMS
         - Webhook receives incoming SMS
         - Cloud-hosted, no device access needed
      3. Android SMS Content Provider
         - Direct access via accessibility service
    """

    def __init__(self):
        self.active = False

    async def listen(self) -> AsyncGenerator[RawMessage, None]:
        """Stub: In production, yields SMS messages as they arrive."""
        logger.info("[Interceptor] SMS listener started (stub)")
        self.active = True
        return
        yield

    async def start(self):
        self.active = True
        logger.info("[Interceptor] SMS interceptor started")

    async def stop(self):
        self.active = False
        logger.info("[Interceptor] SMS interceptor stopped")


class EmailInterceptor(BaseInterceptor):
    """
    Email interceptor via IMAP IDLE.

    Production options:
      1. IMAP IDLE (recommended)
         - Push-based email notification
         - Uses `aioimaplib` for async IMAP
      2. Gmail API (OAuth 2.0)
         - Google-specific, requires OAuth setup
         - Best for Gmail users
      3. Microsoft Graph API
         - Outlook/Exchange via REST API
    """

    def __init__(self):
        self.active = False

    async def listen(self) -> AsyncGenerator[RawMessage, None]:
        """Stub: In production, yields emails as they arrive via IMAP IDLE."""
        logger.info("[Interceptor] Email listener started (stub)")
        self.active = True
        return
        yield

    async def start(self):
        self.active = True
        logger.info("[Interceptor] Email interceptor started")

    async def stop(self):
        self.active = False
        logger.info("[Interceptor] Email interceptor stopped")


class VoiceCallInterceptor(BaseInterceptor):
    """
    Voice call interceptor with real-time transcription.

    Production options:
      1. Android CallScreeningService
         - Screen calls before they ring
         - Requires Android 10+ (API 29)
      2. Twilio Programmable Voice
         - Cloud-based call interception
         - Real-time audio stream via WebSocket
      3. On-device Whisper
         - Local ASR model (whisper.cpp)
         - Privacy-first, no cloud needed
    """

    def __init__(self):
        self.active = False

    async def listen(self) -> AsyncGenerator[RawMessage, None]:
        """Stub: In production, yields transcribed voice calls."""
        logger.info("[Interceptor] Voice call listener started (stub)")
        self.active = True
        return
        yield

    async def start(self):
        self.active = True
        logger.info("[Interceptor] Voice call interceptor started")

    async def stop(self):
        self.active = False
        logger.info("[Interceptor] Voice call interceptor stopped")


# ── Interceptor Registry ──────────────────────────────────────

INTERCEPTORS: dict[Channel, type[BaseInterceptor]] = {
    Channel.WHATSAPP: WhatsAppInterceptor,
    Channel.SMS: SMSInterceptor,
    Channel.EMAIL: EmailInterceptor,
    Channel.VOICE: VoiceCallInterceptor,
}


def get_interceptor(channel: Channel) -> BaseInterceptor:
    """Factory: Get the interceptor for a specific channel."""
    interceptor_class = INTERCEPTORS.get(channel)
    if not interceptor_class:
        raise ValueError(f"No interceptor registered for channel: {channel}")
    return interceptor_class()
