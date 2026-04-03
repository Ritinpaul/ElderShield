"""
ArmorClaw Governance — L4 Validation Pipeline
══════════════════════════════════════════════
The main L4 ArmorClaw module that orchestrates the full governance flow:

  1. Injection Detection    — re-scan action fields for adversarial input
  2. Scope Validation       — whitelist check: only permitted actions allowed
  3. HMAC-SHA256 Signing    — cryptographically bind the action to its content
  4. Immutable Audit Log    — write to tamper-proof SQLite audit trail
  5. Return signed action   — with signature embedded in QuarantineAction

Fail-closed guarantee:
  If injection is detected OR scope validation fails:
    → The original quarantine action is OVERRIDDEN with HOLD_FOR_REVIEW
    → An alert is recorded with injection_detected=True
  This means even if an adversary tampers with the classification result,
  ArmorClaw catches it and prevents auto-delivery.

This module is the last line of defense before an action reaches L5 (dashboard).
"""

import logging
from datetime import datetime, timezone

from backend.models.schemas import QuarantineAction, ActionType
from backend.armorclaw.validator import ScopeValidator, check_injection
from backend.armorclaw.signer import sign
from backend.armorclaw import audit_log

logger = logging.getLogger("eldershield.l4.armorclaw")


class ArmorClaw:
    """
    L4 Governance layer — validates, signs, and audits every quarantine action.

    Usage:
        armorclaw = ArmorClaw()
        signed_action = await armorclaw.validate_and_sign(quarantine_action)

    The returned action always has a non-None `cryptographic_signature`.
    """

    def __init__(self):
        self.validator = ScopeValidator()
        self._injection_attempts = 0

    async def validate_and_sign(self, action: QuarantineAction) -> QuarantineAction:
        """
        Full L4 governance pipeline for a quarantine action.

        Steps:
          1. Pre-injection check on all fields
          2. Scope validation against whitelist
          3. HMAC-SHA256 signature generation
          4. Immutable audit log write
          5. Return signed QuarantineAction

        Fail-closed: injection or scope failure → override to HOLD + sign + audit.

        Args:
            action: Unsigned QuarantineAction from L3 quarantine engine

        Returns:
            QuarantineAction with cryptographic_signature populated.
        """
        injection_detected = False

        # action.action may be ActionType enum OR a raw string (when Pydantic validation
        # is bypassed in tests by directly assigning a string). We handle both.
        def _action_str(a) -> str:
            return a.value if hasattr(a, "value") else str(a)

        # Step 1 — Scope validation (includes injection detection)
        is_valid, rejection_reason = self.validator.validate(
            action=_action_str(action.action),
            message_id=action.message_id,
            reason_code=action.reason,
            user_explanation=action.user_explanation or "",
        )

        if not is_valid:
            injection_detected = "injection" in rejection_reason
            self._injection_attempts += 1

            logger.error(
                f"[L4/ArmorClaw] GOVERNANCE BLOCK | "
                f"msg={action.message_id[:8]}... | "
                f"reason={rejection_reason} | "
                f"injection={injection_detected}"
            )

            # Override to safe HOLD action
            action = QuarantineAction(
                message_id=action.message_id,
                action=ActionType.HOLD_FOR_REVIEW,
                confidence=action.confidence,
                reason="armorclaw_governance_block",
                user_explanation=(
                    "ElderShield's security layer detected an unusual pattern in "
                    "this message. It has been held for manual review. "
                    "Please contact your family immediately."
                ),
                family_alert_level="HIGH",
            )

        # Step 2 — Sign the (possibly overridden) action
        signature, timestamp = sign(
            message_id=action.message_id,
            action=_action_str(action.action),
            confidence=action.confidence,
            reason=action.reason,
            timestamp=None,  # Will use current UTC time
        )

        # Step 3 — Write immutable audit entry
        await audit_log.record(
            message_id=action.message_id,
            action=_action_str(action.action),
            confidence=action.confidence,
            reason=action.reason,
            signature=signature,
            timestamp=timestamp,
            injection_detected=injection_detected,
        )

        # Step 4 — Attach signature to action
        action.cryptographic_signature = signature

        logger.info(
            f"[L4/ArmorClaw] Action signed & audited | "
            f"msg={action.message_id[:8]}... | "
            f"action={_action_str(action.action)} | "
            f"sig={signature[:16]}... | "
            f"injection_detected={injection_detected}"
        )

        return action

    @property
    def injection_attempt_count(self) -> int:
        """Total injection attempts blocked by this ArmorClaw instance."""
        return self._injection_attempts
