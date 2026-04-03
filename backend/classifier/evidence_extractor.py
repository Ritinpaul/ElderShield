"""
EvidenceExtractor — L2a Grounded Evidence Agent
================================================
Runs BEFORE the Ensemble Classifier (Groq/Gemini).

The Hallucination Problem it Solves:
  LLMs jump straight to "SCAM because financial urgency" without verifying
  the text actually contains financial urgency language. This agent forces
  the model to cite verbatim quotes before classification can happen.

What it does:
  1. Sends the raw message text to an LLM with a HIGHLY CONSTRAINED prompt:
     "Find verbatim quotes from this text that match these 9 fraud patterns."
  2. Returns a structured EvidenceBundle: list of {quote, pattern, severity}.
  3. This bundle is injected into the Groq/Gemini classification prompt.
  4. If no evidence is found for a SCAM classification, confidence is
     automatically clamped to max 0.65 (forces HOLD, not QUARANTINE).

Hallucination shield:
  The downstream LLM classifier is instructed: "You MUST cite at least one
  evidence quote to justify SCAM label. If no quotes were found, lower
  your confidence accordingly."  The model cannot invent evidence — it
  must point to what the EvidenceExtractor actually found.
"""

import json
import logging
import asyncio
from typing import Optional

logger = logging.getLogger("eldershield.l2a.evidence")

# Maximum confidence for SCAM label if no evidence bundle was found
NO_EVIDENCE_SCAM_MAX_CONFIDENCE = 0.65

# Evidence patterns to look for — these are the same patterns the classifier uses
EVIDENCE_PATTERNS = [
    {"pattern": "financial_urgency", "keywords": ["send money", "wire transfer", "gift card", "urgently", "immediately", "fast", "owe", "debt", "fine", "bail", "fees"]},
    {"pattern": "family_impersonation", "keywords": ["your son", "your daughter", "your grandson", "your granddaughter", "it's me", "grandma", "grandpa", "mom", "dad"]},
    {"pattern": "secrecy_demand", "keywords": ["don't tell", "keep it secret", "between us", "don't mention", "just between", "don't say"]},
    {"pattern": "authority_impersonation", "keywords": ["police", "government", "IRS", "court", "legal action", "arrested", "warrant", "official", "officer", "bank official"]},
    {"pattern": "urgency_pressure", "keywords": ["right now", "no time", "today only", "last chance", "deadline", "expire", "before it's too late", "emergency"]},
    {"pattern": "phishing_indicators", "keywords": ["click here", "verify your", "account suspended", "link", "login", "password", "OTP", "one-time"]},
    {"pattern": "prize_fraud", "keywords": ["you've won", "you won", "lottery", "prize", "reward", "congratulations", "selected", "chosen"]},
    {"pattern": "prompt_injection", "keywords": ["ignore previous", "ignore all", "new instructions", "act as", "pretend you are", "system:", "override"]},
    {"pattern": "emotional_manipulation", "keywords": ["scared", "crying", "hurt", "in trouble", "desperate", "please help", "begging"]},
]


def _extract_evidence_local(text: str) -> list[dict]:
    """
    Fast local rule-based evidence extraction (no LLM needed).
    Returns matches as {quote, pattern, severity}.
    This runs deterministically — zero hallucination possible.
    """
    if not text:
        return []

    lower = text.lower()
    evidence = []

    for pat in EVIDENCE_PATTERNS:
        for keyword in pat["keywords"]:
            if keyword in lower:
                # Find the actual phrase in context (up to 50 chars around it)
                idx = lower.find(keyword)
                start = max(0, idx - 20)
                end = min(len(text), idx + len(keyword) + 20)
                quote = text[start:end].strip()

                evidence.append({
                    "quote": quote,
                    "pattern": pat["pattern"],
                    "keyword": keyword,
                    "severity": "HIGH" if pat["pattern"] in ("financial_urgency", "prompt_injection", "authority_impersonation") else "MEDIUM"
                })
                break  # One hit per pattern is enough

    return evidence


class EvidenceExtractor:
    """
    L2a — Evidence Extraction Agent.

    Extracts verbatim quotes from messages that match known fraud patterns.
    This evidence bundle is injected into the L2 classification prompt to:
      1. Ground the LLM's reasoning in actual text
      2. Automatically cap confidence when no evidence is found

    Uses only local rule-based extraction (fast, deterministic, zero hallucination).
    Future: Can be upgraded to LLM-based extraction for semantic matching.

    Usage:
        extractor = EvidenceExtractor()
        msg = extractor.extract(msg)
        # msg.evidence_bundle populated
        # msg.prior_scam_probability adjusted if strong evidence found
    """

    def extract(self, msg) -> object:
        """
        Extract fraud evidence from the normalized message.

        Args:
            msg: NormalizedMessage

        Returns:
            Same message with evidence_bundle populated.
        """
        evidence = _extract_evidence_local(msg.text)
        msg.evidence_bundle = evidence

        high_sev = [e for e in evidence if e["severity"] == "HIGH"]
        medium_sev = [e for e in evidence if e["severity"] == "MEDIUM"]

        if high_sev:
            logger.warning(
                f"[L2a/Evidence] 🚨 {len(high_sev)} HIGH severity evidence found "
                f"in msg={msg.id[:8]}: {[e['pattern'] for e in high_sev]}"
            )
        elif medium_sev:
            logger.info(
                f"[L2a/Evidence] ⚠️ {len(medium_sev)} MEDIUM severity evidence found "
                f"in msg={msg.id[:8]}: {[e['pattern'] for e in medium_sev]}"
            )
        else:
            logger.info(
                f"[L2a/Evidence] ✅ No fraud evidence found in msg={msg.id[:8]} "
                f"— SCAM confidence will be capped at {NO_EVIDENCE_SCAM_MAX_CONFIDENCE}"
            )

        return msg

    def build_evidence_prompt_section(self, evidence_bundle: list[dict]) -> str:
        """
        Format the evidence bundle as a section to inject into classification prompts.
        This is called by groq_classifier.py and gemini_classifier.py.
        """
        if not evidence_bundle:
            return (
                "\n## Evidence Analysis\n"
                "NO fraud evidence found verbatim in the message text.\n"
                f"If you label this SCAM, your confidence MUST be at most {NO_EVIDENCE_SCAM_MAX_CONFIDENCE}.\n"
            )

        lines = ["\n## Evidence Analysis", "The following verbatim quotes were found matching fraud patterns:"]
        for e in evidence_bundle:
            lines.append(f'  - Pattern: {e["pattern"]} | Severity: {e["severity"]}')
            lines.append(f'    Quote: "{e["quote"]}"')

        lines.append(
            "\nYou MUST cite at least one of these quotes in your classification reasoning. "
            "High severity evidence supports SCAM label. "
            "If no HIGH evidence exists, prefer SUSPICIOUS over SCAM.\n"
        )
        return "\n".join(lines)

    @staticmethod
    def clamp_confidence_if_no_evidence(
        label: str,
        confidence: float,
        evidence_bundle: list[dict],
    ) -> float:
        """
        Clamp SCAM confidence to NO_EVIDENCE_SCAM_MAX_CONFIDENCE if no evidence was found.
        This is the structural hallucination guard.

        Called by ensemble.py after classification.
        """
        if label == "SCAM" and not evidence_bundle:
            if confidence > NO_EVIDENCE_SCAM_MAX_CONFIDENCE:
                logger.warning(
                    f"[L2a/Evidence] Clamping confidence: {confidence:.2f} → "
                    f"{NO_EVIDENCE_SCAM_MAX_CONFIDENCE} (no evidence bundle)"
                )
                return NO_EVIDENCE_SCAM_MAX_CONFIDENCE
        return confidence
