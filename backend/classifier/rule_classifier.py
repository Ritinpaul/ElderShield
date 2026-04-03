"""
Rule-Based Classifier — L2 Fast Pre-Classifier
══════════════════════════════════════════════
Deterministic regex + keyword scam classifier used when:
  1. Both LLM classifiers are unavailable (no API keys)
  2. As a fast pre-filter before LLM calls
  3. For obvious high-confidence scam patterns

Speed: <1ms (no network call)
Accuracy: ~75% on known scam patterns
Coverage: Hardcoded scam patterns from real Indian elderly fraud cases

This replaces the Gemma 2B local model requirement since we don't
have a GPU available. For production, this becomes the on-device
privacy-first pre-screener before any cloud LLM call.
"""

import re
import logging
from typing import NamedTuple

from backend.models.schemas import ClassificationResult, RiskLabel

logger = logging.getLogger("eldershield.l2.rules")


class ScoredPattern(NamedTuple):
    pattern: str          # regex pattern
    score: float          # risk contribution (0.0–1.0)
    reason_code: str      # machine-readable reason
    flags: list[str]      # red flag tags


# ── Scam Pattern Library ──────────────────────────────────────
# Sourced from India CERT-In advisories, FTC Sentinel, and RBI fraud alerts.

SCAM_PATTERNS: list[ScoredPattern] = [
    # Financial urgency
    ScoredPattern(
        r"send\s*(money|cash|funds|₹|rs\.?|rupee)",
        0.8, "financial_urgency", ["financial_request", "urgency"]
    ),
    ScoredPattern(
        r"(urgent|emergency|immediately|right\s*now|asap|hurry)\b.*?(money|transfer|send|pay)",
        0.85, "financial_urgency", ["urgency", "financial_request"]
    ),
    ScoredPattern(
        r"(wire\s*transfer|bank\s*transfer|neft|rtgs|upi|google\s*pay|paytm)\b.*?(₹|\d{4,})",
        0.8, "financial_urgency", ["financial_request", "payment_method"]
    ),
    ScoredPattern(
        r"gift\s*card|amazon\s*gift|itunes|voucher\s*code",
        0.9, "financial_urgency", ["gift_card_scam", "unusual_payment"]
    ),

    # Family / voice impersonation
    ScoredPattern(
        r"(i'?m\s*your|it'?s\s*(me|your)|this\s*is\s*(your|me))\s*(son|daughter|grandson|granddaughter|beta|beti|chacha|mama|papa|mummy|bhaiya|didi)",
        0.85, "family_impersonation", ["impersonation", "family_claim"]
    ),
    ScoredPattern(
        r"(i'?m\s*in\s*(jail|prison|hospital|trouble)|(had|have)\s*(an\s*)?accident|arrested|injured|hurt)\s*.*?(help|money|send|need)",
        0.9, "family_impersonation", ["emergency_scam", "impersonation"]
    ),

    # Authority impersonation
    ScoredPattern(
        r"(income\s*tax|it\s*department|cbi|police|court|rbi|sebi|trai)\s*(officer|department|notice|case|action)",
        0.85, "authority_impersonation", ["official_impersonation"]
    ),
    ScoredPattern(
        r"(arrest|warrant|legal\s*action|fir|case\s*filed)\s*(will\s*be\s*)?issued",
        0.85, "authority_impersonation", ["legal_threat"]
    ),
    ScoredPattern(
        r"kyc\s*(update|verification|expired|pending)\s*(or|else|otherwise)",
        0.85, "authority_impersonation", ["kyc_scam", "bank_fraud"]
    ),

    # Phishing links
    ScoredPattern(
        r"(click|visit|open|tap)\s*(this|the|here|url|link)",
        0.65, "phishing_link", ["link_present"]
    ),
    ScoredPattern(
        r"https?://(?!(?:google|youtube|amazon|flipkart|sbi\.co|hdfcbank|icicibank|paytm|upi))[^\s]{10,}",
        0.7, "phishing_link", ["suspicious_url"]
    ),
    ScoredPattern(
        r"(bit\.ly|tinyurl|t\.co|rb\.gy|cutt\.ly|is\.gd)/",
        0.75, "phishing_link", ["shortened_url"]
    ),

    # Prize / lottery fraud
    ScoredPattern(
        r"(you'?ve?\s*(won|win)|congratulations|lucky\s*(winner|draw|prize))",
        0.75, "prize_fraud", ["lottery_scam"]
    ),
    ScoredPattern(
        r"(claim\s*your|collect\s*your)\s*(prize|reward|cash|crore|lakh)",
        0.85, "prize_fraud", ["lottery_scam", "financial_request"]
    ),

    # Secrecy demand
    ScoredPattern(
        r"(don'?t\s*tell|keep\s*(it\s*)?secret|between\s*us|nobody\s*should\s*know|secret|confidential)\b.*?(money|bank|transfer|send)",
        0.9, "secrecy_demand", ["secrecy_request"]
    ),

    # OTP / credential phishing
    ScoredPattern(
        r"(share|send|give|tell)\s*(your\s*)?(otp|pin|password|cvv|card\s*number)",
        0.95, "phishing_link", ["credential_theft", "bank_fraud"]
    ),
    ScoredPattern(
        r"(your\s*)?(account|bank|card)\s*(blocked|suspended|deactivated|compromised)",
        0.8, "authority_impersonation", ["account_threat"]
    ),
]

# Suspicious-level patterns (lower score)
SUSPICIOUS_PATTERNS: list[ScoredPattern] = [
    ScoredPattern(
        r"(unknown|new)\s*(number|contact|person)\s*(here|calling)",
        0.45, "unverified_sender", ["unverified_sender"]
    ),
    ScoredPattern(
        r"can\s*you\s*(help|lend|give|send)\s*me",
        0.4, "unusual_request", ["assistance_request"]
    ),
    ScoredPattern(
        r"(personal|private)\s*(details|information|data)\s*(required|needed|verify)",
        0.55, "identity_claim_unverifiable", ["data_request"]
    ),
]


class RuleBasedClassifier:
    """
    Deterministic pattern-based classifier.

    Scoring algorithm:
      - Sum up risk scores from all matching patterns
      - Clamp to [0, 1] range
      - threshold ≥ 0.75 → SCAM
      - threshold ≥ 0.45 → SUSPICIOUS
      - else → BENIGN

    Multiple pattern matches compound the score.
    """

    async def classify(self, text: str, metadata: dict) -> ClassificationResult:
        """
        Classify text using rule-based pattern matching.
        No network call — returns sub-millisecond.
        """
        if not text or not text.strip():
            return ClassificationResult(
                label=RiskLabel.SUSPICIOUS,
                confidence=0.5,
                reason="ambiguous_intent",
                explanation="Message text is empty.",
                red_flags=["empty_message"],
                model_used="rule-based",
            )

        lower_text = text.lower()
        cumulative_score = 0.0
        matched_reasons: list[str] = []
        all_red_flags: list[str] = []
        primary_reason = "routine_communication"

        # Check scam patterns
        for pattern in SCAM_PATTERNS:
            if re.search(pattern.pattern, lower_text, re.IGNORECASE):
                cumulative_score += pattern.score
                matched_reasons.append(pattern.reason_code)
                all_red_flags.extend(pattern.flags)
                logger.debug(
                    f"[L2/Rules] Hit: pattern='{pattern.pattern[:40]}...' "
                    f"score={pattern.score} reason={pattern.reason_code}"
                )

        # Check suspicious patterns (only if not already high-risk)
        if cumulative_score < 0.75:
            for pattern in SUSPICIOUS_PATTERNS:
                if re.search(pattern.pattern, lower_text, re.IGNORECASE):
                    cumulative_score += pattern.score
                    matched_reasons.append(pattern.reason_code)
                    all_red_flags.extend(pattern.flags)

        # Clamp and determine label
        final_score = min(cumulative_score, 0.98)  # Never 1.0 — that's reserved for injection
        unique_flags = list(dict.fromkeys(all_red_flags))  # Deduplicated

        if matched_reasons:
            primary_reason = matched_reasons[0]

        if final_score >= 0.75:
            label = RiskLabel.SCAM
            explanation = f"Rule-based: {len(matched_reasons)} scam indicator(s) detected."
        elif final_score >= 0.45:
            label = RiskLabel.SUSPICIOUS
            if primary_reason in ("routine_communication",):
                primary_reason = "ambiguous_intent"
            explanation = f"Rule-based: {len(matched_reasons)} suspicious indicator(s) detected."
        else:
            label = RiskLabel.BENIGN
            primary_reason = "routine_communication"
            explanation = "No known scam patterns detected."
            unique_flags = []

        confidence = final_score if final_score >= 0.45 else (1.0 - final_score)

        logger.info(
            f"[L2/Rules] Result: label={label.value} | "
            f"score={final_score:.2f} | patterns_hit={len(matched_reasons)}"
        )

        return ClassificationResult(
            label=label,
            confidence=round(confidence, 3),
            reason=primary_reason,
            explanation=explanation,
            red_flags=unique_flags[:8],  # Cap at 8 flags
            model_used="rule-based-v1",
            probabilities={
                "SCAM": round(min(final_score, 0.98), 3),
                "SUSPICIOUS": round(max(0, 0.5 - abs(final_score - 0.5)), 3),
                "BENIGN": round(max(0, 1.0 - final_score), 3),
            },
        )
