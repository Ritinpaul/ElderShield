"""
WhatsApp Sender — Twilio Sandbox
═════════════════════════════════
Sends real WhatsApp messages via Twilio's WhatsApp sandbox.
Used by the demo endpoint to simulate the attacker sending a scam.

Setup:
  1. Create a free Twilio account: https://www.twilio.com/try-twilio
  2. Go to Messaging > Try it out > Send a WhatsApp message
  3. The target phone must join the sandbox first by sending:
       "join <your-sandbox-word>"  to  +1 415 523 8886  on WhatsApp
  4. Add to .env:
       TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
       TWILIO_AUTH_TOKEN=your_auth_token
       TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
"""

import os
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("eldershield.whatsapp")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN  = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_FROM        = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")


def _is_configured() -> bool:
    return bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN)


async def send_whatsapp(to_phone: str, body: str) -> dict:
    """
    Send a real WhatsApp message via Twilio sandbox.

    Args:
        to_phone: Target phone number, e.g. '+919876543210'
        body:     Message text to send

    Returns:
        dict with keys: status, sid, error
    """
    if not _is_configured():
        logger.warning("[WhatsApp] Twilio not configured — returning simulated response")
        return {
            "status": "simulated",
            "sid": "SIM-" + os.urandom(4).hex().upper(),
            "error": None,
            "note": "Add TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN to .env to send real messages",
        }

    # Normalise the phone number to WhatsApp format
    if not to_phone.startswith("+"):
        to_phone = "+" + to_phone
    to_wa = f"whatsapp:{to_phone}"

    try:
        # Run blocking Twilio call in a thread so we don't block the event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _send_sync, to_wa, body)
        return result
    except Exception as e:
        logger.error(f"[WhatsApp] Send failed: {e}")
        return {"status": "error", "sid": None, "error": str(e)}


def _send_sync(to_wa: str, body: str) -> dict:
    """Blocking Twilio call — run in executor."""
    from twilio.rest import Client  # imported here so missing package doesn't crash startup
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    msg = client.messages.create(
        from_=TWILIO_FROM,
        to=to_wa,
        body=body,
    )
    logger.info(f"[WhatsApp] Sent ► SID={msg.sid} Status={msg.status}")
    return {"status": msg.status, "sid": msg.sid, "error": None}
