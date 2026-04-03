"""
Gemini LLM Classifier — L2 Secondary Cloud Classifier
══════════════════════════════════════════════════════
Uses Google Gemini API (gemini-2.0-flash) as a second opinion classifier.
Activated by the ensemble when Groq confidence < CONFIDENCE_THRESHOLD,
or when Groq API is unavailable.

Why Gemini as second model:
  - We have GEMINI_API_KEY configured
  - Gemini 2.0 Flash is fast (~500ms) and accurate
  - Excellent at contextual safety classification
  - Cross-validation with two independent models raises reliability

API Docs: https://googleapis.github.io/python-genai/
Note: We use the REST API directly via httpx (no additional SDK needed).
"""

import os
import json
import logging
import re

import httpx

from backend.models.schemas import ClassificationResult, RiskLabel
from backend.classifier.prompts import SYSTEM_PROMPT, build_user_message, detect_prompt_injection

logger = logging.getLogger("eldershield.l2.gemini")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# gemini-2.0-flash-lite: ultra-fast, cost-effective for classification tasks
# upgrade to gemini-2.0-flash for higher accuracy if needed
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_API_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)


class GeminiClassifier:
    """
    Secondary LLM classifier using Google Gemini API.

    Used as:
      1. Fallback when Groq returns low confidence (<threshold)
      2. Cross-validator when Groq is unavailable
      3. Tiebreaker in ensemble voting

    Same fail-closed principle as GroqClassifier:
    any API error → SUSPICIOUS (held for family review).
    """

    async def classify(self, text: str, metadata: dict) -> ClassificationResult:
        """
        Classify a message using Google Gemini API.

        Args:
            text: Normalized message text (or voice transcript)
            metadata: Channel metadata from L1 normalizer

        Returns:
            ClassificationResult with label, confidence, reason, red_flags
        """
        # Step 1: Pre-screen for prompt injection
        if detect_prompt_injection(text):
            logger.warning(
                f"[L2/Gemini] Prompt injection detected in pre-screen: {text[:80]}..."
            )
            return ClassificationResult(
                label=RiskLabel.SCAM,
                confidence=0.99,
                reason="prompt_injection_attempt",
                explanation="Prompt injection pattern detected before Gemini analysis.",
                red_flags=["prompt_injection", "jailbreak_attempt"],
                model_used="gemini-injection-prescreen",
            )

        # Step 2: Check API key
        if not GEMINI_API_KEY:
            logger.warning("[L2/Gemini] No GEMINI_API_KEY — failing to SUSPICIOUS")
            return self._make_error_result("gemini-no-api-key")

        # Step 3: Build prompt and call Gemini
        user_message = build_user_message(text, metadata)
        raw_json = await self._call_gemini_api(user_message)

        if raw_json is None:
            return self._make_error_result("gemini-api-error")

        return self._parse_response(raw_json)

    async def _call_gemini_api(self, user_message: str) -> dict | None:
        """
        Call Gemini generateContent API.

        Gemini uses a different request format from OpenAI — system instructions
        are sent in the `systemInstruction` field, not as a message role.
        """
        payload = {
            "systemInstruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_message}]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 300,
                "responseMimeType": "application/json",
            },
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    GEMINI_API_URL,
                    headers={"Content-Type": "application/json"},
                    params={"key": GEMINI_API_KEY},
                    json=payload,
                )

                if resp.status_code == 200:
                    data = resp.json()
                    content = data["candidates"][0]["content"]["parts"][0]["text"]
                    logger.info(
                        f"[L2/Gemini] API call successful | "
                        f"model={GEMINI_MODEL}"
                    )
                    # Gemini sometimes wraps JSON in markdown fences — strip them
                    content = self._strip_markdown_fences(content)
                    return json.loads(content)
                else:
                    logger.error(
                        f"[L2/Gemini] API error: HTTP {resp.status_code} — {resp.text[:300]}"
                    )
                    return None

        except httpx.TimeoutException:
            logger.error("[L2/Gemini] API timeout after 15s")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"[L2/Gemini] JSON decode error: {e}")
            return None
        except (KeyError, IndexError) as e:
            logger.error(f"[L2/Gemini] Unexpected response structure: {e}")
            return None
        except Exception as e:
            logger.error(f"[L2/Gemini] Unexpected error: {e}")
            return None

    def _strip_markdown_fences(self, content: str) -> str:
        """Remove ```json ... ``` fences that Gemini sometimes adds."""
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            # Remove first line (```json or ```) and last line (```)
            lines = lines[1:] if lines[0].startswith("```") else lines
            lines = lines[:-1] if lines and lines[-1].strip() == "```" else lines
            content = "\n".join(lines).strip()
        return content

    def _parse_response(self, raw: dict) -> ClassificationResult:
        """Parse and validate Gemini JSON response (same format as Groq)."""
        try:
            label_str = raw.get("label", "SUSPICIOUS").upper()
            if label_str not in ("SCAM", "SUSPICIOUS", "BENIGN"):
                logger.warning(f"[L2/Gemini] Unknown label '{label_str}' → SUSPICIOUS")
                label_str = "SUSPICIOUS"
            label = RiskLabel(label_str)

            confidence = float(raw.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))

            reason = raw.get("reason", "unknown_high_risk")
            reason = re.sub(r"[\s-]+", "_", reason.strip().lower())

            explanation = raw.get("explanation", "")
            red_flags = raw.get("red_flags", [])
            if not isinstance(red_flags, list):
                red_flags = []

            logger.info(
                f"[L2/Gemini] Classified: label={label_str} | "
                f"confidence={confidence:.2f} | reason={reason}"
            )

            return ClassificationResult(
                label=label,
                confidence=confidence,
                reason=reason,
                explanation=explanation,
                red_flags=red_flags,
                model_used=f"gemini/{GEMINI_MODEL}",
            )

        except Exception as e:
            logger.error(f"[L2/Gemini] Response parse error: {e} | raw={raw}")
            return self._make_error_result("gemini-parse-error")

    def _make_error_result(self, model_tag: str) -> ClassificationResult:
        """Fail-closed: return SUSPICIOUS on any error."""
        return ClassificationResult(
            label=RiskLabel.SUSPICIOUS,
            confidence=0.50,
            reason="ambiguous_intent",
            explanation="ElderShield (Gemini) could not fully analyze this message. Held for review.",
            red_flags=["classifier_error"],
            model_used=model_tag,
        )
