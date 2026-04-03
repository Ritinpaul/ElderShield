"""
Quarantine Engine — L3 Decision Layer
═══════════════════════════════════════
Converts L2 classification results into quarantine decisions.

Decision matrix:
  SCAM   + confidence ≥ 0.75  →  QUARANTINE  +  HIGH family alert
  SCAM   + confidence < 0.75  →  HOLD        +  MEDIUM alert
  SUSPICIOUS  (any confidence)→  HOLD        +  MEDIUM alert
  BENIGN + confidence ≥ 0.80  →  DELIVER     +  No alert
  BENIGN + confidence < 0.80  →  HOLD        +  MEDIUM alert (cautious mode)

Fail-closed: any unhandled exception → HOLD (never auto-deliver on error).

Why HOLD instead of QUARANTINE for low-confidence SCAM?
  The family must have the final say. We show them the message and risk score;
  they decide. Over-blocking trusted family messages erodes trust in the system.
"""

import logging
from datetime import datetime, timezone

from backend.models.schemas import (
    ClassificationResult,
    NormalizedMessage,
    QuarantineAction,
    ActionType,
    RiskLabel,
)
from backend.quarantine.explainer import QuarantineExplainer

logger = logging.getLogger("eldershield.l3.quarantine")

# Decision thresholds
SCAM_QUARANTINE_THRESHOLD = 0.75   # Above this → definite QUARANTINE
BENIGN_DELIVER_THRESHOLD = 0.80    # Below this → HOLD even for benign


class QuarantineEngine:
    """
    Layer 3 — Quarantine Decision Engine.

    Takes a NormalizedMessage + ClassificationResult and produces
    a QuarantineAction with:
      - action (deliver / hold_for_review / quarantine)
      - user_explanation (elder-friendly text)
      - family_alert_level (HIGH / MEDIUM / None)
      - reason code
    """

    def __init__(self):
        self.explainer = QuarantineExplainer()

    async def decide(
        self,
        msg: NormalizedMessage,
        classification: ClassificationResult,
    ) -> QuarantineAction:
        """
        Core decision logic. Fail-closed — any error → HOLD.

        Args:
            msg: The normalized message from L1
            classification: The L2 classification result

        Returns:
            QuarantineAction ready to be signed by L4 ArmorClaw
        """
        try:
            return self._make_decision(msg, classification)
        except Exception as e:
            logger.error(
                f"[L3/Quarantine] Unexpected error deciding for "
                f"message {msg.id[:8]}: {e} — defaulting to HOLD"
            )
            return QuarantineAction(
                message_id=msg.id,
                action=ActionType.HOLD_FOR_REVIEW,
                confidence=0.5,
                reason="engine_error",
                user_explanation="ElderShield encountered an issue. This message has been held for manual review by your family.",
                family_alert_level="MEDIUM",
            )

    def _make_decision(
        self,
        msg: NormalizedMessage,
        c: ClassificationResult,
    ) -> QuarantineAction:
        """Deterministic decision logic."""
        label = c.label
        confidence = c.confidence
        reason = c.reason

        logger.info(
            f"[L3/Quarantine] Deciding for msg={msg.id[:8]} | "
            f"label={label.value} | confidence={confidence:.2f} | reason={reason}"
        )

        # ── SCAM ──────────────────────────────────────────────
        if label == RiskLabel.SCAM:
            if confidence >= SCAM_QUARANTINE_THRESHOLD:
                action = ActionType.QUARANTINE
                alert_level = "HIGH"
                log_prefix = "🚨 QUARANTINE"
            else:
                # Low-confidence SCAM → hold for family review
                action = ActionType.HOLD_FOR_REVIEW
                alert_level = "MEDIUM"
                log_prefix = "⚠️  HOLD (low-confidence scam)"

        # ── SUSPICIOUS ────────────────────────────────────────
        elif label == RiskLabel.SUSPICIOUS:
            action = ActionType.HOLD_FOR_REVIEW
            alert_level = "MEDIUM"
            log_prefix = "🔍 HOLD (suspicious)"

        # ── BENIGN ────────────────────────────────────────────
        else:  # BENIGN
            if confidence >= BENIGN_DELIVER_THRESHOLD:
                action = ActionType.DELIVER
                alert_level = None
                log_prefix = "✅ DELIVER"
            else:
                # Low-confidence benign → cautious hold
                action = ActionType.HOLD_FOR_REVIEW
                alert_level = "MEDIUM"
                log_prefix = "🔍 HOLD (low-confidence benign)"

        # Build elder-friendly explanation
        user_explanation = self.explainer.explain(
            label=label,
            action=action,
            reason=reason,
            red_flags=c.red_flags,
            confidence=confidence,
            channel=msg.channel.value,
            sender=msg.sender,
        )

        logger.info(
            f"[L3/Quarantine] {log_prefix} | "
            f"msg={msg.id[:8]} | alert_level={alert_level}"
        )

        return QuarantineAction(
            message_id=msg.id,
            action=action,
            confidence=round(confidence, 3),
            reason=reason,
            user_explanation=user_explanation,
            family_alert_level=alert_level,
        )
