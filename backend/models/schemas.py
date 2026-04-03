"""
ElderShield — Data Contracts & Pydantic Models
═══════════════════════════════════════════════
All data flowing through the 5-layer pipeline is typed here.
These contracts enforce consistency across L1→L2→L3→L4→L5.
"""

from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional


# ── Enums ─────────────────────────────────────────────────────

class Channel(str, Enum):
    """Communication channels ElderShield monitors."""
    WHATSAPP = "whatsapp"
    SMS = "sms"
    EMAIL = "email"
    VOICE = "voice"


class RiskLabel(str, Enum):
    """Classification labels for incoming messages."""
    BENIGN = "BENIGN"
    SUSPICIOUS = "SUSPICIOUS"
    SCAM = "SCAM"


class ActionType(str, Enum):
    """Actions the quarantine engine can take."""
    DELIVER = "deliver"
    HOLD_FOR_REVIEW = "hold_for_review"
    QUARANTINE = "quarantine"


# ── L1: Interception Models ──────────────────────────────────

class RawMessage(BaseModel):
    """Raw message as received from any communication channel."""
    channel: Channel
    sender: str
    text: Optional[str] = None
    audio_url: Optional[str] = None
    format: str = ""

    class Config:
        json_schema_extra = {
            "example": {
                "channel": "whatsapp",
                "sender": "+91-9876543210",
                "text": "Grandma, I'm in jail, send ₹50,000 urgently!",
                "audio_url": None,
                "format": "whatsapp",
            }
        }


class NormalizedMessage(BaseModel):
    """Unified message schema after L1 normalization."""
    id: str = Field(..., description="Unique message ID (UUID)")
    channel: Channel
    sender: str
    text: str = Field(..., description="Plain text content (or audio transcript)")
    metadata: dict = Field(default_factory=dict, description="Channel-specific metadata")
    intercepted_at: str = Field(..., description="ISO 8601 timestamp of interception")
    # ── NEW: PhoneReputationAgent (Phase A) ──────────────────
    prior_scam_probability: float = Field(
        default=0.50,
        description="Bayesian prior from PhoneReputationAgent: 0.0 (trusted) → 1.0 (known scammer)"
    )
    # ── NEW: EvidenceExtractor (Phase B) ─────────────────────
    evidence_bundle: list[dict] = Field(
        default_factory=list,
        description="Verbatim quotes from message matching known fraud patterns"
    )


# ── L2: Classification Models ────────────────────────────────

class ClassificationResult(BaseModel):
    """Output from the L2 classification layer."""
    label: RiskLabel
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str = Field(..., description="Machine-readable reason code")
    explanation: str = Field(default="", description="Human-readable explanation for audit")
    red_flags: list[str] = Field(default_factory=list)
    model_used: str = Field(..., description="Model that produced this result")
    probabilities: dict[str, float] = Field(default_factory=dict)
    gemma_fallback: bool = Field(default=False, description="True if GPT-4o was used as fallback")
    # ── NEW: CriticAgent (Phase C) ────────────────────────────
    critic_verdict: Optional[str] = Field(
        default=None,
        description="CriticAgent verdict: AGREE | DISAGREE | UNCERTAIN | SKIPPED"
    )
    critic_confidence_delta: float = Field(
        default=0.0,
        description="How much CriticAgent adjusted the confidence score (+/-)"
    )


# ── L3: Quarantine Models ────────────────────────────────────

class QuarantineAction(BaseModel):
    """Action decided by the quarantine engine, to be validated by L4."""
    message_id: str
    action: ActionType
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str
    user_explanation: Optional[str] = Field(
        default=None,
        description="Elder-friendly explanation shown to the user"
    )
    family_alert_level: Optional[str] = Field(
        default=None,
        description="Alert severity: HIGH / MEDIUM / None"
    )
    cryptographic_signature: Optional[str] = Field(
        default=None,
        description="HMAC-SHA256 signature from L4 ArmorClaw"
    )


# ── L4: Audit Models ─────────────────────────────────────────

class AuditEntry(BaseModel):
    """Immutable audit log entry — every action is recorded here."""
    message_id: str
    action: str
    confidence: float
    reason: str
    signature: str
    timestamp: str
    injection_detected: bool = False


# ── API Request Models ────────────────────────────────────────

class IncomingMessageRequest(BaseModel):
    """
    REST API request body for /api/intercept.
    Used by demo scripts and external integrations.
    """
    channel: str = Field(..., description="Channel: whatsapp, sms, email, voice")
    sender: str = Field(..., description="Sender identifier (phone / email)")
    text: Optional[str] = Field(default=None, description="Message text content")
    audio_url: Optional[str] = Field(default=None, description="URL to audio file for transcription")

    class Config:
        json_schema_extra = {
            "example": {
                "channel": "whatsapp",
                "sender": "+91-9876543210",
                "text": "Grandma, I'm in trouble, send money immediately!",
                "audio_url": None,
            }
        }


# ── L5: Dashboard / WebSocket Models ─────────────────────────

class ThreatAlert(BaseModel):
    """WebSocket payload pushed to the family dashboard."""
    type: str = "THREAT_DETECTED"
    message_id: str
    channel: str
    action: str
    confidence: float
    reason: str
    alert_level: str
    signature: str
    user_explanation: Optional[str] = None
    timestamp: str


class DashboardStats(BaseModel):
    """Aggregated stats for the dashboard overview."""
    total_intercepted: int = 0
    total_blocked: int = 0
    total_suspicious: int = 0
    total_safe: int = 0
    injection_attempts: int = 0
    avg_confidence: float = 0.0
