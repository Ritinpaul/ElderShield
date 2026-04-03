"""
Message Normalizer — L1 Sub-Component
══════════════════════════════════════
Converts any channel-specific message format into the unified
NormalizedMessage schema used by all downstream layers.

Handles:
  - Text extraction from diverse message formats
  - Audio transcription via OpenAI Whisper API
  - Metadata extraction for classification context
"""

import os
import logging

import httpx

from backend.models.schemas import RawMessage, NormalizedMessage

logger = logging.getLogger("eldershield.l1.normalizer")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
WHISPER_API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"


class MessageNormalizer:
    """
    Normalizes raw messages from any channel into a unified schema.

    The normalizer is responsible for:
      1. Extracting text from the message body
      2. Transcribing audio (voice messages, calls) to text via Whisper
      3. Building metadata context for the LLM classifier

    Example:
        normalizer = MessageNormalizer()
        normalized = await normalizer.normalize(raw_msg, "uuid-123", "2026-04-02T12:00:00Z")
    """

    async def normalize(
        self,
        raw: RawMessage,
        msg_id: str,
        intercepted_at: str,
    ) -> NormalizedMessage:
        """
        Transform a RawMessage into a NormalizedMessage.

        If the message contains audio, it will be transcribed to text
        via OpenAI Whisper before normalization.
        """
        text = raw.text or ""

        # Transcribe audio if present (voice messages, calls)
        if raw.audio_url:
            logger.info(f"[L1] Transcribing audio via Groq Whisper: {raw.audio_url[:50]}...")
            transcript = await self._transcribe_audio(raw.audio_url)
            if transcript:
                text = transcript
                logger.info(f"[L1] Audio transcribed: {len(transcript)} chars")
            else:
                logger.warning("[L1] Audio transcription failed — using empty text")

        # Build metadata for classifier context
        metadata = self._extract_metadata(raw)

        return NormalizedMessage(
            id=msg_id,
            channel=raw.channel,
            sender=raw.sender,
            text=text,
            intercepted_at=intercepted_at,
            metadata=metadata,
        )

    def _extract_metadata(self, raw: RawMessage) -> dict:
        """
        Extract channel-specific metadata for LLM context.

        The classifier uses this metadata to understand the message
        context — e.g., voice messages are treated differently from
        text SMS in terms of scam patterns.
        """
        return {
            "original_format": raw.format or raw.channel.value,
            "has_audio": raw.audio_url is not None,
            "sender_number": raw.sender,
            "channel": raw.channel.value,
        }

    async def _transcribe_audio(self, audio_url: str) -> str | None:
        """
        Transcribe voice audio via Groq Whisper API (blazing fast).

        Falls back gracefully if:
          - No API key is configured
          - The audio file is unreachable
          - Groq API returns an error

        Args:
            audio_url: URL to the audio file (ogg, mp3, wav, etc.)

        Returns:
            Transcribed text, or None if transcription fails
        """
        if not GROQ_API_KEY:
            logger.warning("[L1] No GROQ_API_KEY set — skipping audio transcription")
            return None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Step 1: Download the audio file
                audio_resp = await client.get(audio_url)
                if audio_resp.status_code != 200:
                    logger.error(
                        f"[L1] Failed to download audio: HTTP {audio_resp.status_code}"
                    )
                    return None

                # Determine file extension from URL
                ext = audio_url.rsplit(".", 1)[-1] if "." in audio_url else "ogg"
                mime_map = {
                    "ogg": "audio/ogg",
                    "mp3": "audio/mpeg",
                    "wav": "audio/wav",
                    "m4a": "audio/m4a",
                    "webm": "audio/webm",
                }
                mime = mime_map.get(ext, "audio/ogg")

                # Step 2: Send to Groq Whisper API (compatible with OpenAI format)
                resp = await client.post(
                    WHISPER_API_URL,
                    headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                    files={"file": (f"audio.{ext}", audio_resp.content, mime)},
                    data={"model": "whisper-large-v3"},
                )

                if resp.status_code == 200:
                    result = resp.json()
                    return result.get("text", "")
                else:
                    logger.error(
                        f"[L1] Groq API error: HTTP {resp.status_code} — "
                        f"{resp.text[:200]}"
                    )
                    return None

        except httpx.TimeoutException:
            logger.error("[L1] Groq API timeout — audio transcription skipped")
            return None
        except Exception as e:
            logger.error(f"[L1] Audio transcription error: {e}")
            return None
