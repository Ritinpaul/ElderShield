"""
Ensemble Classifier — L2 Orchestrator
══════════════════════════════════════
Smart routing between Rule-Based → Groq → Gemini classifiers.

Strategy:
  ┌─────────────────────────────────────────────────────────┐
  │  1. Rule-based pre-screen (always runs, <1ms)           │
  │     • HIGH confidence (≥0.90) → Return immediately      │
  │     • LOW confidence → Escalate to Groq                 │
  │                                                         │
  │  2. Groq LLM (primary, llama-3.3-70b)                  │
  │     • High confidence (≥0.75) → Return result           │
  │     • Low confidence (<0.75) → Escalate to Gemini       │
  │     • API error → Escalate to Gemini                    │
  │                                                         │
  │  3. Gemini LLM (secondary, gemini-2.0-flash)            │
  │     • Return Gemini result regardless of confidence     │
  │     • API error → Return best available result           │
  └─────────────────────────────────────────────────────────┘

Fail-closed: Any unhandled error → SUSPICIOUS (held for review).

Environment variables:
  CONFIDENCE_THRESHOLD (default: 0.75)
    — Groq confidence below this triggers Gemini escalation
  RULE_CONFIDENCE_FAST_PATH (default: 0.90)
    — Rule-based confidence above this skips LLM calls
"""

import os
import logging
import asyncio

from backend.models.schemas import ClassificationResult, NormalizedMessage, RiskLabel
from backend.classifier.rule_classifier import RuleBasedClassifier
from backend.classifier.groq_classifier import GroqClassifier
from backend.classifier.gemini_classifier import GeminiClassifier
from backend.classifier.evidence_extractor import EvidenceExtractor, NO_EVIDENCE_SCAM_MAX_CONFIDENCE

logger = logging.getLogger("eldershield.l2.ensemble")

# Thresholds
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))
RULE_FAST_PATH = float(os.getenv("RULE_CONFIDENCE_FAST_PATH", "0.90"))


class EnsembleClassifier:
    """
    Orchestrates classification across three layers:
      Layer A: Rule-Based (deterministic, instant)
      Layer B: Groq LLM (primary LLM, llama-3.3-70b)
      Layer C: Gemini LLM (secondary LLM, gemini-2.0-flash)

    Designed to deliver <2s end-to-end classification for the
    hackathon demo, while maximising accuracy through ensemble logic.
    """

    def __init__(self):
        self.rules = RuleBasedClassifier()
        self.groq = GroqClassifier()
        self.gemini = GeminiClassifier()
        self.evidence_extractor = EvidenceExtractor()  # Phase B: EvidenceExtractor
        self._stats = {
            "total": 0,
            "rule_fast_path": 0,
            "groq_confident": 0,
            "gemini_escalation": 0,
            "errors": 0,
        }

    async def classify(self, msg: NormalizedMessage) -> ClassificationResult:
        """
        Core ensemble classification pipeline.

        Args:
            msg: Normalized message from L1 agent

        Returns:
            ClassificationResult — best available result from the ensemble
        """
        self._stats["total"] += 1
        text = msg.text
        metadata = msg.metadata

        logger.info(
            f"[L2/Ensemble] Classifying message | "
            f"id={msg.id[:8]}... | channel={msg.channel.value} | "
            f"text_len={len(text or '')} chars"
        )

        # ── Phase B: EvidenceExtractor ──────────────────────────
        # Extract verbatim fraud quotes before LLM runs
        msg = self.evidence_extractor.extract(msg)
        evidence_section = self.evidence_extractor.build_evidence_prompt_section(msg.evidence_bundle)
        # Inject prior_scam_probability bias into metadata for classifiers
        metadata = dict(metadata)
        metadata["prior_scam_probability"] = msg.prior_scam_probability
        metadata["evidence_section"] = evidence_section

        # ── Layer A: Rule-based pre-screen ────────────────────
        rule_result = await self.rules.classify(text, metadata)
        logger.debug(
            f"[L2/Ensemble] Rules: label={rule_result.label.value} | "
            f"confidence={rule_result.confidence:.2f}"
        )

        # Fast path: obvious scam with high rule confidence → skip LLM
        if rule_result.label == RiskLabel.SCAM and rule_result.confidence >= RULE_FAST_PATH:
            self._stats["rule_fast_path"] += 1
            logger.info(
                f"[L2/Ensemble] ⚡ Fast path: Rules detected obvious scam "
                f"(confidence={rule_result.confidence:.2f}) — skipping LLM"
            )
            rule_result.model_used = "rule-based-fast-path"
            return rule_result

        # ── Layer B: Groq LLM ─────────────────────────────────
        groq_result = await self._safe_classify(self.groq.classify, text, metadata, "Groq")

        if groq_result is None:
            logger.warning("[L2/Ensemble] Groq unavailable — escalating to Gemini directly")
            return await self._fallback_to_gemini(text, metadata, rule_result)

        logger.debug(
            f"[L2/Ensemble] Groq: label={groq_result.label.value} | "
            f"confidence={groq_result.confidence:.2f}"
        )

        # Check if Groq is confident enough to return directly
        if groq_result.confidence >= CONFIDENCE_THRESHOLD:
            self._stats["groq_confident"] += 1
            logger.info(
                f"[L2/Ensemble] \u2705 Groq confident: "
                f"label={groq_result.label.value} | "
                f"confidence={groq_result.confidence:.2f}"
            )
            # Merge rule-based red flags into Groq result for richer output
            result = self._merge_flags(groq_result, rule_result)
            # Phase B: Clamp confidence if no evidence was found
            result.confidence = EvidenceExtractor.clamp_confidence_if_no_evidence(
                result.label.value, result.confidence, msg.evidence_bundle
            )
            return result

        # ── Layer C: Gemini escalation ────────────────────────
        logger.info(
            f"[L2/Ensemble] 🔄 Groq low confidence ({groq_result.confidence:.2f} < "
            f"{CONFIDENCE_THRESHOLD}) — escalating to Gemini"
        )
        return await self._fallback_to_gemini(
            text, metadata, rule_result, primary_result=groq_result
        )

    async def _fallback_to_gemini(
        self,
        text: str,
        metadata: dict,
        rule_result: ClassificationResult,
        primary_result: ClassificationResult | None = None,
    ) -> ClassificationResult:
        """
        Escalate to Gemini as secondary classifier.
        If Gemini also fails, combine rule + Groq results.
        """
        self._stats["gemini_escalation"] += 1
        gemini_result = await self._safe_classify(self.gemini.classify, text, metadata, "Gemini")

        if gemini_result is not None:
            logger.info(
                f"[L2/Ensemble] ✅ Gemini result: "
                f"label={gemini_result.label.value} | "
                f"confidence={gemini_result.confidence:.2f}"
            )
            gemini_result.gemma_fallback = True  # Marks 'secondary model was used'
            return self._merge_flags(gemini_result, rule_result)

        # All LLMs failed — use Groq result if available, else rule-based
        logger.warning("[L2/Ensemble] ⚠️ All LLMs failed — using best available result")
        self._stats["errors"] += 1

        if primary_result:
            primary_result.model_used = f"{primary_result.model_used}+rule-fallback"
            return self._merge_flags(primary_result, rule_result)

        return rule_result

    async def _safe_classify(
        self,
        classify_fn,
        text: str,
        metadata: dict,
        name: str,
    ) -> ClassificationResult | None:
        """
        Wrapper that catches all exceptions from a classifier call.
        Returns None on any error (ensemble then escalates).
        """
        try:
            result = await asyncio.wait_for(
                classify_fn(text, metadata),
                timeout=20.0,
            )
            return result
        except asyncio.TimeoutError:
            logger.error(f"[L2/Ensemble] {name} classifier timed out after 20s")
            return None
        except Exception as e:
            logger.error(f"[L2/Ensemble] {name} classifier error: {e}")
            return None

    def _merge_flags(
        self,
        primary: ClassificationResult,
        rule_result: ClassificationResult,
    ) -> ClassificationResult:
        """
        Merge rule-based red flags into the primary result.
        This enriches LLM results with specific pattern matches.
        """
        combined_flags = list(dict.fromkeys(
            primary.red_flags + rule_result.red_flags
        ))[:10]  # Cap at 10 total flags
        primary.red_flags = combined_flags
        return primary

    @property
    def stats(self) -> dict:
        """Return ensemble routing statistics."""
        return dict(self._stats)
