"""
ArmorClaw Validator — Intent Scope Validator
═════════════════════════════════════════════
Ensures the quarantine engine only produces actions within the
permitted whitelist. This is the core "read-only AI" enforcement —
ArmorClaw prevents the AI from taking any action outside its
pre-approved scope.

Permitted actions (whitelist):
  deliver         — Pass a safe message through to recipient
  hold_for_review — Hold message, notify family, await review
  quarantine      — Block message, quarantine, alert family

ANY action NOT in this list is rejected. The AI cannot:
  - Delete messages permanently
  - Modify message content
  - Access contacts or call logs
  - Send messages on behalf of the user
  - Escalate to actions involving money or external systems

Prompt injection detection:
  Before validating scope, we check the proposed action string
  for injection patterns (same as L2 classifier pre-screen).
  This prevents adversarial inputs from bypassing scope validation.
"""

import re
import logging
from backend.models.schemas import ActionType

logger = logging.getLogger("eldershield.l4.validator")


# ── Permitted Action Whitelist ─────────────────────────────────
PERMITTED_ACTIONS: frozenset[str] = frozenset({
    ActionType.DELIVER.value,
    ActionType.HOLD_FOR_REVIEW.value,
    ActionType.QUARANTINE.value,
})

# ── Injection Patterns for Action Field ───────────────────────
# Prevents an adversary from crafting a quarantine action that
# contains injected instructions in the reason or action fields.
INJECTION_PATTERNS: list[str] = [
    r"ignore\s+(previous|all|your)",
    r"act\s+as\s+",
    r"you\s+are\s+now\s+",
    r"(jailbreak|dan\s+mode)",
    r"forget\s+your\s+instructions",
    r"system\s*:",
    r"<\s*script",
    r"eval\(",
    r"exec\(",
    r"__import__",
    r"os\.system",
    r"subprocess",
    r"DROP\s+TABLE",
    r"SELECT\s+\*\s+FROM",
    r";\s*(DELETE|UPDATE|INSERT)",
]

_COMPILED_INJECTION = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def check_injection(text: str) -> bool:
    """
    Check if a text field contains prompt/code injection patterns.

    Returns:
        True if injection detected, False if clean.
    """
    if not text:
        return False
    for pattern in _COMPILED_INJECTION:
        if pattern.search(text):
            logger.warning(f"[L4/Validator] Injection pattern detected in: '{text[:80]}'")
            return True
    return False


class ScopeValidator:
    """
    ArmorClaw scope validation.

    Usage:
        validator = ScopeValidator()
        ok, reason = validator.validate(action, message_id, reason_code)
        if not ok:
            raise PermissionError(reason)
    """

    def validate(
        self,
        action: str,
        message_id: str,
        reason_code: str,
        user_explanation: str = "",
    ) -> tuple[bool, str]:
        """
        Validate a proposed quarantine action against the whitelist.

        Args:
            action: The proposed action string
            message_id: UUID of the message
            reason_code: Machine-readable reason from classifier
            user_explanation: Human-readable explanation (injection-checked)

        Returns:
            (is_valid: bool, rejection_reason: str | "")
        """
        # 1. Check for injection in all string fields
        for field_name, field_value in [
            ("action", action),
            ("reason_code", reason_code),
            ("user_explanation", user_explanation),
        ]:
            if check_injection(field_value):
                logger.error(
                    f"[L4/Validator] SCOPE_REJECTED: injection in field='{field_name}' "
                    f"msg={message_id[:8]}..."
                )
                return False, f"injection_detected_in_{field_name}"

        # 2. Check action is within whitelist
        if action not in PERMITTED_ACTIONS:
            logger.error(
                f"[L4/Validator] SCOPE_REJECTED: unknown action='{action}' "
                f"msg={message_id[:8]}... — not in whitelist"
            )
            return False, f"action_out_of_scope:{action}"

        # 3. Validate message_id is a plausible UUID (basic sanity check)
        if not message_id or len(message_id) < 8:
            logger.error(f"[L4/Validator] SCOPE_REJECTED: invalid message_id='{message_id}'")
            return False, "invalid_message_id"

        logger.debug(
            f"[L4/Validator] SCOPE_OK: action={action} | "
            f"msg={message_id[:8]}... | reason={reason_code}"
        )
        return True, ""
