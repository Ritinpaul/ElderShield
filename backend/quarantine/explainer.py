"""
Quarantine Explainer — Elder-Friendly Explanation Generator
═══════════════════════════════════════════════════════════
Converts machine-readable classification results into plain-language
explanations that elderly users and their families can understand.

Design principles:
  1. No technical jargon — no "confidence score", "model", "LLM"
  2. Warm, reassuring tone — don't panic the user
  3. Actionable — tell the user what happened and what to do next
  4. Hindi-friendly phrasing — familiar for Indian elderly users

Reason code → plain English mapping covers all codes from:
  - prompts.py REASON_CODES
  - rule_classifier.py reason codes
  - Internal engine codes (engine_error, ambiguous_intent)
"""

import logging
from backend.models.schemas import ActionType, RiskLabel

logger = logging.getLogger("eldershield.l3.explainer")


# ── Reason Code → Human Summary ──────────────────────────────
# Maps classifier reason codes to elder-friendly short summaries.

REASON_TO_SUMMARY: dict[str, str] = {
    # LLM reason codes (from prompts.py)
    "financial_urgency":            "asking you for money urgently",
    "family_impersonation":         "pretending to be a family member in trouble",
    "authority_impersonation":      "pretending to be a government or bank official",
    "prize_fraud":                  "claiming you've won a fake prize or lottery",
    "phishing_link":                "containing a suspicious link to steal your information",
    "technical_support_scam":       "pretending to be technical support to access your device",
    "romance_scam":                 "building false trust to ask for money",
    "investment_fraud":             "offering fake investment or money-doubling schemes",
    "secrecy_demand":               "asking you to keep this secret from your family",

    # Rule-based reason codes
    "credential_theft":             "trying to steal your OTP, password, or card details",
    "account_threat":               "threatening to block your bank account",
    "kyc_scam":                     "falsely claiming your KYC update is required",
    "gift_card_scam":               "asking you to buy gift cards as payment",
    "lottery_scam":                 "claiming you've won a lottery or prize",
    "secrecy_request":              "telling you to keep this secret from your family",
    "legal_threat":                 "threatening legal action or arrest",
    "shortened_url":                "containing a hidden suspicious link",
    "prompt_injection_attempt":     "trying to manipulate ElderShield's security",

    # Fallback / engine codes
    "ambiguous_intent":             "that ElderShield could not fully verify",
    "unverified_sender":            "from an unknown sender",
    "unusual_request":              "making an unusual request",
    "routine_communication":        "that appears safe",
    "engine_error":                 "that could not be analyzed",
    "identity_claim_unverifiable":  "from someone whose identity could not be verified",
    "unknown_high_risk":            "that contains suspicious patterns",
}

# ── Action → Template ─────────────────────────────────────────

def _quarantine_explanation(reason: str, sender: str, channel: str) -> str:
    summary = REASON_TO_SUMMARY.get(reason, "that contains suspicious content")
    channel_label = {"whatsapp": "WhatsApp", "sms": "SMS", "email": "email", "voice": "voice call"}.get(channel, channel)
    return (
        f"🚨 ElderShield has blocked a {channel_label} message from {sender} "
        f"because it appears to be a scam {summary}. "
        f"This message has been safely quarantined. "
        f"You do not need to respond. Your family has been notified."
    )


def _hold_explanation(
    reason: str,
    sender: str,
    channel: str,
    label: RiskLabel,
    red_flags: list[str],
) -> str:
    summary = REASON_TO_SUMMARY.get(reason, "that needs a closer look")
    channel_label = {"whatsapp": "WhatsApp", "sms": "SMS", "email": "email", "voice": "voice call"}.get(channel, channel)

    if label == RiskLabel.SCAM:
        tone = "looks like a scam"
    elif label == RiskLabel.SUSPICIOUS:
        tone = "looks suspicious"
    else:
        tone = "ElderShield wants to double-check"

    flags_note = ""
    if "credential_theft" in red_flags or "bank_fraud" in red_flags:
        flags_note = " Never share your OTP, PIN, or password with anyone."
    elif "financial_request" in red_flags or "gift_card_scam" in red_flags:
        flags_note = " Do not send money or buy gift cards before talking to your family."

    return (
        f"⚠️ A {channel_label} message from {sender} has been held for review — "
        f"it {tone} ({summary}).{flags_note} "
        f"Please show this to a trusted family member before taking any action."
    )


def _deliver_explanation(sender: str, channel: str) -> str:
    channel_label = {"whatsapp": "WhatsApp", "sms": "SMS", "email": "email", "voice": "voice call"}.get(channel, channel)
    return (
        f"✅ A {channel_label} message from {sender} has been checked "
        f"by ElderShield and appears safe to read."
    )


class QuarantineExplainer:
    """
    Generates elder-friendly explanations for quarantine decisions.
    All output is in plain English with no technical terms.
    """

    def explain(
        self,
        label: RiskLabel,
        action: ActionType,
        reason: str,
        red_flags: list[str],
        confidence: float,
        channel: str,
        sender: str,
    ) -> str:
        """
        Generate a user-facing explanation for a quarantine action.

        Args:
            label: Classification label (SCAM / SUSPICIOUS / BENIGN)
            action: Quarantine action (quarantine / hold / deliver)
            reason: Machine-readable reason code
            red_flags: List of specific risk flags from classifier
            confidence: Classification confidence [0,1]
            channel: Communication channel
            sender: Sender identifier

        Returns:
            Plain-English explanation string
        """
        try:
            if action == ActionType.QUARANTINE:
                return _quarantine_explanation(reason, sender, channel)
            elif action == ActionType.HOLD_FOR_REVIEW:
                return _hold_explanation(reason, sender, channel, label, red_flags)
            else:  # DELIVER
                return _deliver_explanation(sender, channel)
        except Exception as e:
            logger.error(f"[L3/Explainer] Error generating explanation: {e}")
            return "This message has been flagged by ElderShield. Please consult your family before taking any action."
