"""
Groq LLM Classifier — L2 Primary Cloud Classifier
══════════════════════════════════════════════════
Uses Groq's ultra-fast inference API (llama-3.3-70b-versatile) for
zero-shot scam classification. Groq's LPU delivers OpenAI-compatible
API at ~10x lower latency — ideal for our <2s pipeline requirement.

Why Groq over OpenAI:
  - We have GROQ_API_KEY configured (not OpenAI)
  - Groq llama-3.3-70b is on par with GPT-4o for classification
  - 500+ tokens/sec throughput via Language Processing Unit (LPU)
  - OpenAI-compatible endpoint — minimal code change needed

API Docs: https://console.groq.com/docs/openai
"""

import os
import json
import logging
import re

import httpx

from backend.models.schemas import ClassificationResult, RiskLabel
from backend.classifier.prompts import SYSTEM_PROMPT, build_user_message, detect_prompt_injection

logger = logging.getLogger("eldershield.l2.groq")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Model: llama-3.3-70b-versatile — best Groq model for reasoning tasks
# Alternative: mixtral-8x7b-32768 for longer context
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Valid reason codes from prompts.py
VALID_SCAM_REASONS = {
    "deepfake_voice_pattern", "financial_urgency", "family_impersonation",
    "authority_impersonation", "phishing_link", "secrecy_demand",
    "prize_fraud", "emotional_blackmail", "prompt_injection_attempt",
    "unknown_high_risk",
}
VALID_SUSPICIOUS_REASONS = {
    "unusual_request", "unverified_sender", "ambiguous_intent",
    "unusual_financial_ask", "identity_claim_unverifiable",
}
VALID_BENIGN_REASONS = {
    "routine_communication", "known_contact_pattern", "service_notification",
}


class GroqClassifier:
    """
    Primary LLM classifier using Groq's high-speed inference API.

    Classification pipeline:
      1. Pre-screen for prompt injection (regex check)
      2. Send to Groq llama-3.3-70b via chat completions API
      3. Parse and validate JSON response
      4. Return ClassificationResult with full provenance

    Fails closed: any API error returns SUSPICIOUS with low confidence
    so the quarantine engine holds the message for review.
    """

    async def classify(self, text: str, metadata: dict) -> ClassificationResult:
        """
        Classify a message using Groq's LLM API.

        Args:
            text: Normalized message text (or voice transcript)
            metadata: Channel metadata from L1 normalizer

        Returns:
            ClassificationResult with label, confidence, reason, red_flags
        """
        # Step 1: Pre-screen for prompt injection
        if detect_prompt_injection(text):
            logger.warning(
                f"[L2/Groq] Prompt injection detected in pre-screen: "
                f"{text[:80]}..."
            )
            return ClassificationResult(
                label=RiskLabel.SCAM,
                confidence=0.99,
                reason="prompt_injection_attempt",
                explanation="Prompt injection pattern detected in message before LLM analysis.",
                red_flags=["prompt_injection", "jailbreak_attempt"],
                model_used="groq-injection-prescreen",
            )

        # Step 2: Check API key
        if not GROQ_API_KEY:
            logger.warning("[L2/Groq] No GROQ_API_KEY — failing to SUSPICIOUS")
            return self._make_error_result("groq-no-api-key")

        # Step 3: Call Groq API
        user_message = build_user_message(text, metadata)
        raw_json = await self._call_groq_api(user_message)

        if raw_json is None:
            return self._make_error_result("groq-api-error")

        # Step 4: Parse and validate response
        return self._parse_response(raw_json)

    async def _call_groq_api(self, user_message: str) -> dict | None:
        """Send request to Groq chat completions endpoint."""
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.1,
            "max_tokens": 300,
            "response_format": {"type": "json_object"},
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    GROQ_API_URL,
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

                if resp.status_code == 200:
                    data = resp.json()
                    content = data["choices"][0]["message"]["content"]
                    logger.info(
                        f"[L2/Groq] API call successful | "
                        f"model={GROQ_MODEL} | "
                        f"tokens={data.get('usage', {}).get('total_tokens', '?')}"
                    )
                    return json.loads(content)
                else:
                    logger.error(
                        f"[L2/Groq] API error: HTTP {resp.status_code} — {resp.text[:200]}"
                    )
                    return None

        except httpx.TimeoutException:
            logger.error("[L2/Groq] API timeout after 15s")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"[L2/Groq] JSON decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"[L2/Groq] Unexpected error: {e}")
            return None

    def _parse_response(self, raw: dict) -> ClassificationResult:
        """
        Parse and validate the LLM JSON response.

        Validates:
          - label is one of SCAM / SUSPICIOUS / BENIGN
          - confidence is float 0.0–1.0
          - reason code matches the label's valid set
        """
        try:
            label_str = raw.get("label", "SUSPICIOUS").upper()
            if label_str not in ("SCAM", "SUSPICIOUS", "BENIGN"):
                logger.warning(f"[L2/Groq] Unknown label '{label_str}' → SUSPICIOUS")
                label_str = "SUSPICIOUS"
            label = RiskLabel(label_str)

            confidence = float(raw.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))  # Clamp to [0,1]

            reason = raw.get("reason", "unknown_high_risk")
            # Validate and normalize reason code
            reason = self._validate_reason(reason, label_str)

            explanation = raw.get("explanation", "")
            red_flags = raw.get("red_flags", [])
            if not isinstance(red_flags, list):
                red_flags = []

            logger.info(
                f"[L2/Groq] Classified: label={label_str} | "
                f"confidence={confidence:.2f} | reason={reason}"
            )

            return ClassificationResult(
                label=label,
                confidence=confidence,
                reason=reason,
                explanation=explanation,
                red_flags=red_flags,
                model_used=f"groq/{GROQ_MODEL}",
            )

        except Exception as e:
            logger.error(f"[L2/Groq] Response parse error: {e} | raw={raw}")
            return self._make_error_result("groq-parse-error")

    def _validate_reason(self, reason: str, label: str) -> str:
        """Ensure the reason code matches the label category."""
        # Normalise: replace spaces/hyphens with underscores, lowercase
        reason = re.sub(r"[\s-]+", "_", reason.strip().lower())
        valid_map = {
            "SCAM": VALID_SCAM_REASONS,
            "SUSPICIOUS": VALID_SUSPICIOUS_REASONS,
            "BENIGN": VALID_BENIGN_REASONS,
        }
        valid = valid_map.get(label, set())
        if reason not in valid:
            # Try to find a close match (label mismatch)
            all_valid = VALID_SCAM_REASONS | VALID_SUSPICIOUS_REASONS | VALID_BENIGN_REASONS
            if reason in all_valid:
                return reason  # Accept even if category mismatch
            fallback = {
                "SCAM": "unknown_high_risk",
                "SUSPICIOUS": "ambiguous_intent",
                "BENIGN": "routine_communication",
            }
            return fallback.get(label, "unknown_high_risk")
        return reason

    def _make_error_result(self, model_tag: str) -> ClassificationResult:
        """Fail-closed: return SUSPICIOUS on any error."""
        return ClassificationResult(
            label=RiskLabel.SUSPICIOUS,
            confidence=0.50,
            reason="ambiguous_intent",
            explanation="ElderShield could not fully analyze this message. Held for review.",
            red_flags=["classifier_error"],
            model_used=model_tag,
        )
