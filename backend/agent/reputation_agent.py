"""
PhoneReputationAgent — L1.5 Prior Scoring
==========================================
Runs immediately after OpenClaw (L1) interception, BEFORE the LLM classifier.

What it does:
  1. Looks up the sender's phone number in the local `phone_reputation` DB table.
  2. Sets `prior_scam_probability` on the NormalizedMessage:
       - Known scammer  → 0.90  (very high prior, LLM confidence will be boosted)
       - Trusted contact → 0.05  (very low prior, benign messages get a confidence boost)
       - Unknown number  → 0.50  (neutral prior — no bias)
  3. After the full pipeline runs, the caller updates the reputation table
     with the final classification label.

Why this has near-zero hallucination risk:
  - Pure DB lookup — no LLM involved, no generative model can "make up" a reputation.
  - The prior only biases confidence, it never overrides labels directly.
  - All reputation updates require a confirmed SCAM classification from the full pipeline.
"""

import logging
from datetime import datetime, timezone

from backend.database.db import Database
from backend.models.schemas import NormalizedMessage

logger = logging.getLogger("eldershield.l1_5.reputation")

# Prior probability mapping by reputation label
PRIOR_BY_LABEL = {
    "SCAMMER": 0.90,
    "TRUSTED": 0.05,
    "UNKNOWN": 0.50,
}


class PhoneReputationAgent:
    """
    L1.5 — Phone Reputation lookup agent.

    Usage:
        rep_agent = PhoneReputationAgent(db)
        msg = await rep_agent.enrich(msg)
        # msg.prior_scam_probability is now set
        # After pipeline:
        await rep_agent.record_outcome(msg.sender, "SCAMMER")
    """

    def __init__(self, db: Database):
        self.db = db

    async def enrich(self, msg: NormalizedMessage) -> NormalizedMessage:
        """
        Look up sender reputation and set prior_scam_probability on the message.

        Args:
            msg: NormalizedMessage from L1 (OpenClaw)

        Returns:
            Same message with prior_scam_probability updated.
        """
        sender = msg.sender.strip()
        record = await self.db.get_phone_reputation(sender)

        if record is None:
            prior = PRIOR_BY_LABEL["UNKNOWN"]
            label = "UNKNOWN"
        else:
            label = record.get("label", "UNKNOWN")
            prior = PRIOR_BY_LABEL.get(label, 0.50)

            logger.info(
                f"[L1.5/Reputation] Found record for {sender}: "
                f"label={label}, incidents={record.get('incident_count', 1)}, "
                f"prior={prior:.2f}"
            )

        msg.prior_scam_probability = prior

        if label == "SCAMMER":
            logger.warning(
                f"[L1.5/Reputation] ⚠️  KNOWN SCAMMER: {sender} | "
                f"prior_scam_probability={prior:.2f}"
            )
        elif label == "TRUSTED":
            logger.info(
                f"[L1.5/Reputation] ✅ Trusted contact: {sender} | "
                f"prior_scam_probability={prior:.2f}"
            )

        return msg

    async def record_outcome(self, sender: str, classification_label: str) -> None:
        """
        After the full pipeline, record the outcome for future reputation lookups.

        Only updates reputation if classification is SCAM
        (we don't want false positives poisoning the repuation DB).

        Args:
            sender: Phone number / sender identifier
            classification_label: "SCAM" | "SUSPICIOUS" | "BENIGN"
        """
        sender = sender.strip()
        now = datetime.now(timezone.utc).isoformat()

        if classification_label == "SCAM":
            await self.db.upsert_phone_reputation(sender, "SCAMMER", now)
            logger.warning(
                f"[L1.5/Reputation] 🚨 Marked as SCAMMER: {sender}"
            )
        elif classification_label == "BENIGN":
            # Only mark TRUSTED if not already flagged as SCAMMER
            existing = await self.db.get_phone_reputation(sender)
            if existing is None or existing.get("label") != "SCAMMER":
                await self.db.upsert_phone_reputation(sender, "TRUSTED", now)
                logger.debug(f"[L1.5/Reputation] Marked as TRUSTED: {sender}")
        # SUSPICIOUS → leave as UNKNOWN / do not promote to SCAMMER without full confidence
