import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import logging

from backend.models.schemas import QuarantineAction, ActionType

logger = logging.getLogger("eldershield.l5.notifications")

@dataclass
class FamilyAlert:
    """Format for pushing alerts to the family dashboard via WebSocket."""
    alert_type: str        # 'SCAM', 'SUSPICIOUS', 'BENIGN'
    message_id: str
    channel: str | None
    sender: str | None
    action: str            # lowercase action for frontend compatibility
    action_taken: str      # 'QUARANTINE', 'HOLD_FOR_REVIEW', 'DELIVER'
    confidence: float
    reason: str
    explanation: str
    signature: str | None
    timestamp: str

def format_alert(action: QuarantineAction) -> str:
    """Convert a QuarantineAction into a JSON string for WebSocket broadcast."""
    # Determine the visual alert type based on the action
    alert_type = "BENIGN"
    if action.action == ActionType.QUARANTINE:
        alert_type = "SCAM"
    elif action.action == ActionType.HOLD_FOR_REVIEW:
        alert_type = "SUSPICIOUS"
        
    # Standardize the output for the frontend
    alert = FamilyAlert(
        alert_type=action.family_alert_level or alert_type,
        message_id=action.message_id,
        channel=action.source_channel,
        sender=action.source_sender,
        action=action.action.value,
        action_taken=action.action.value.upper(),
        confidence=action.confidence,
        reason=action.reason,
        explanation=action.user_explanation or "",
        signature=action.cryptographic_signature,
        timestamp=datetime.now(timezone.utc).isoformat()
    )
    
    logger.info(f"[L5/Alert] Formatted alert for msg={action.message_id}")
    return json.dumps(asdict(alert))
