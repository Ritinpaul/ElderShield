"""
CriticAgent — L2.5 Independent Second Opinion
==============================================
Runs AFTER the Ensemble Classifier but BEFORE Quarantine Engine.

The Hallucination Problem it Solves:
  A single LLM can be confident and wrong. The Critic is a second, independent
  LLM call with a DIFFERENT system prompt that evaluates whether the first
  model's conclusion is justified. Two LLMs with different prompts cannot 
  reliably hallucinate the exact same incorrect conclusion.

What it does:
  1. Takes the original message text + the Ensemble's full output.
  2. Sends it to Groq (or Gemini as fallback) in "skeptical auditor" mode.
  3. The Critic responds with: AGREE | DISAGREE | UNCERTAIN
  4. Adjusts the confidence score:
       AGREE     → +0.05 confidence boost (consensus strengthens result)
       UNCERTAIN → -0.10 confidence penalty (force human review path)
       DISAGREE  → -0.20 confidence penalty + force label to SUSPICIOUS

  After DISAGREE, the confidence is almost always below threshold, so
  Quarantine Engine will choose HOLD_FOR_REVIEW instead of QUARANTINE —
  guaranteeing a human reviews any case of model disagreement.

Skipping logic (performance):
  - If evidence_bundle has ≥2 HIGH severity entries → SKIP (no need to double-check)
  - If prior_scam_probability is 0.90 (known scammer) → SKIP (reputation is definitive)
  - If label is BENIGN with confidence > 0.92 → SKIP (very high confidence benign)
  These skips are safe because the upstream signals are already highly reliable.
"""

import json
import logging
import asyncio
import os
from typing import Literal

from backend.models.schemas import ClassificationResult, NormalizedMessage, RiskLabel

logger = logging.getLogger("eldershield.l2_5.critic")

CriticVerdict = Literal["AGREE", "DISAGREE", "UNCERTAIN", "SKIPPED"]

CONFIDENCE_DELTA = {
    "AGREE": +0.05,
    "UNCERTAIN": -0.10,
    "DISAGREE": -0.20,
    "SKIPPED": 0.00,
}

CRITIC_SYSTEM_PROMPT = """You are a security audit AI reviewing another AI's scam classification decision.

Your ONLY job: Determine if the classification is justified based on the message content.

Rules:
- Be SKEPTICAL. Assume the first AI might be wrong.
- AGREE only if you can clearly see evidence in the text that supports the label.
- DISAGREE if the evidence seems weak, ambiguous, or if the classification seems like a stretch.
- UNCERTAIN if you genuinely cannot determine if the label is correct.

Respond with VALID JSON ONLY:
{
  "verdict": "AGREE|DISAGREE|UNCERTAIN",
  "reasoning": "One sentence explaining your decision (max 20 words)"
}"""


class CriticAgent:
    """
    L2.5 — Independent Critic Agent.

    Provides a second opinion on the Ensemble Classifier's output.
    Adjusts confidence score based on agreement/disagreement.

    Usage:
        critic = CriticAgent()
        result = await critic.review(msg, classification_result)
    """

    def __init__(self):
        self._groq_api_key = os.getenv("GROQ_API_KEY")
        self._gemini_api_key = os.getenv("GEMINI_API_KEY")

    async def review(
        self,
        msg: NormalizedMessage,
        result: ClassificationResult,
    ) -> ClassificationResult:
        """
        Review the classification result and adjust confidence.

        Args:
            msg: Original normalized message
            result: Classification result from Ensemble

        Returns:
            Updated ClassificationResult with critic_verdict and adjusted confidence.
        """
        # Skip logic — critic not needed in these high-certainty cases
        skip_reason = self._should_skip(msg, result)
        if skip_reason:
            result.critic_verdict = "SKIPPED"
            result.critic_confidence_delta = 0.0
            logger.debug(f"[L2.5/Critic] Skipping review for {msg.id[:8]}: {skip_reason}")
            return result

        verdict, reasoning = await self._get_verdict(msg, result)

        delta = CONFIDENCE_DELTA.get(verdict, 0.0)
        old_confidence = result.confidence
        new_confidence = min(1.0, max(0.0, result.confidence + delta))

        result.critic_verdict = verdict
        result.critic_confidence_delta = delta
        result.confidence = round(new_confidence, 3)

        # DISAGREE forces label down to SUSPICIOUS to guarantee human review
        if verdict == "DISAGREE" and result.label == RiskLabel.SCAM:
            result.label = RiskLabel.SUSPICIOUS
            result.reason = "critic_disagreement_downgraded"
            logger.warning(
                f"[L2.5/Critic] ⚠️  DISAGREE on SCAM label for {msg.id[:8]} — "
                f"downgraded to SUSPICIOUS. Reasoning: {reasoning}"
            )
        else:
            log_fn = logger.warning if verdict == "UNCERTAIN" else logger.info
            log_fn(
                f"[L2.5/Critic] {verdict} | msg={msg.id[:8]} | "
                f"label={result.label.value} | "
                f"confidence: {old_confidence:.2f} → {new_confidence:.2f} "
                f"({delta:+.2f}) | {reasoning}"
            )

        return result

    def _should_skip(self, msg: NormalizedMessage, result: ClassificationResult) -> str | None:
        """Return a skip reason string if critic review can be skipped, else None."""
        # High-severity evidence already found → very reliable signal
        high_evidence = [e for e in msg.evidence_bundle if e.get("severity") == "HIGH"]
        if len(high_evidence) >= 2:
            return f"strong_evidence ({len(high_evidence)} HIGH severity matches)"

        # Known scammer from reputation DB → trust the prior
        if msg.prior_scam_probability >= 0.90:
            return "known_scammer_prior"

        # Very high-confidence benign → no need for critic
        if result.label == RiskLabel.BENIGN and result.confidence > 0.92:
            return f"high_confidence_benign ({result.confidence:.2f})"

        return None

    async def _get_verdict(
        self,
        msg: NormalizedMessage,
        result: ClassificationResult,
    ) -> tuple[CriticVerdict, str]:
        """Call Groq (or Gemini) in critic mode to get a verdict."""
        user_content = (
            f"Message being reviewed:\n"
            f"---\n"
            f"Channel: {msg.channel.value.upper()}\n"
            f"Sender: {msg.sender}\n"
            f"Text: {msg.text}\n"
            f"---\n\n"
            f"First AI's classification:\n"
            f"  Label: {result.label.value}\n"
            f"  Confidence: {result.confidence:.0%}\n"
            f"  Reason: {result.reason}\n"
            f"  Red Flags: {', '.join(result.red_flags) if result.red_flags else 'none'}\n"
        )

        # Try Groq first
        verdict, reasoning = await self._call_groq(user_content)
        if verdict is None:
            # Fallback to Gemini
            verdict, reasoning = await self._call_gemini(user_content)
        if verdict is None:
            # All APIs failed — default to UNCERTAIN (safe)
            logger.warning(f"[L2.5/Critic] All APIs failed for {msg.id[:8]} — defaulting to UNCERTAIN")
            return "UNCERTAIN", "api_failure"

        return verdict, reasoning

    async def _call_groq(self, user_content: str) -> tuple[CriticVerdict | None, str]:
        """Call Groq API in critic mode."""
        if not self._groq_api_key:
            return None, ""
        try:
            from groq import AsyncGroq
            client = AsyncGroq(api_key=self._groq_api_key)
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    temperature=0.1,
                    max_tokens=100,
                ),
                timeout=10.0,
            )
            raw = response.choices[0].message.content.strip()
            return self._parse_verdict(raw)
        except Exception as e:
            logger.warning(f"[L2.5/Critic] Groq API error: {e}")
            return None, ""

    async def _call_gemini(self, user_content: str) -> tuple[CriticVerdict | None, str]:
        """Call Gemini API in critic mode."""
        if not self._gemini_api_key:
            return None, ""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self._gemini_api_key)
            model = genai.GenerativeModel("gemini-2.0-flash")
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    model.generate_content,
                    f"{CRITIC_SYSTEM_PROMPT}\n\nUser: {user_content}",
                ),
                timeout=10.0,
            )
            raw = response.text.strip()
            return self._parse_verdict(raw)
        except Exception as e:
            logger.warning(f"[L2.5/Critic] Gemini API error: {e}")
            return None, ""

    def _parse_verdict(self, raw: str) -> tuple[CriticVerdict | None, str]:
        """Parse the JSON response from the critic LLM."""
        try:
            # Strip markdown code fences if present
            if "```" in raw:
                raw = raw.split("```")[-2] if "```" in raw else raw
                raw = raw.replace("json", "").strip()
            data = json.loads(raw)
            verdict = data.get("verdict", "").upper()
            if verdict not in ("AGREE", "DISAGREE", "UNCERTAIN"):
                return "UNCERTAIN", "invalid_response"
            return verdict, data.get("reasoning", "")
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"[L2.5/Critic] Failed to parse verdict: {e} | raw={raw[:100]}")
            return "UNCERTAIN", "parse_error"
