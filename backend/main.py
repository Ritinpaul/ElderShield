import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.database.db import Database
from backend.models.schemas import RawMessage, Channel, NormalizedMessage
from backend.agent.openclaw_agent import OpenClawAgent
from backend.agent.reputation_agent import PhoneReputationAgent     # Phase A
from backend.agent.sentinel_agent import SentinelAgent               # Phase D
from backend.classifier.ensemble import EnsembleClassifier
from backend.classifier.critic_agent import CriticAgent              # Phase C
from backend.quarantine.engine import QuarantineEngine
from backend.armorclaw.governance import ArmorClaw
from backend.armorclaw import audit_log
from backend.notifications.family_alert import format_alert
from backend.notifications.whatsapp_sender import send_whatsapp

# --- Logging setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("eldershield.l5.server")

# --- Global State ---
db = Database()
classifier_queue = asyncio.Queue()
agent = OpenClawAgent(db, classifier_queue)
reputation_agent = PhoneReputationAgent(db)   # Phase A: L1.5
classifier = EnsembleClassifier()             # Phase B (EvidenceExtractor) wired inside
critic = CriticAgent()                        # Phase C: L2.5
quarantine = QuarantineEngine()
armorclaw = ArmorClaw()

# --- WebSocket Manager ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"[L5/WS] New family dashboard connected")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"[L5/WS] Dashboard disconnected")

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"[L5/WS] Broadcast failed: {e}")

ws_manager = ConnectionManager()

# Phase D: SentinelAgent gets the broadcast fn so it can push alerts
sentinel = SentinelAgent(db, broadcast_fn=ws_manager.broadcast)

# --- 5-Layer Pipeline Worker ---
async def pipeline_worker():
    """
    Background task: OpenClaw (L1) → Reputation (L1.5) → Evidence+Ensemble (L2)
                   → Critic (L2.5) → Quarantine (L3) → ArmorClaw (L4) → Dashboard (L5)
    """
    logger.info("[L5/Worker] ✅ Pipeline worker started (5-layer + 4 new agents)")
    while True:
        try:
            norm_msg: NormalizedMessage = await classifier_queue.get()
            logger.info(f"[L5/Worker] Processing msg_id={norm_msg.id}")

            # ── L1.5: PhoneReputationAgent ────────────────────────
            # Sets norm_msg.prior_scam_probability based on sender history
            norm_msg = await reputation_agent.enrich(norm_msg)

            # ── L2a+L2b: EvidenceExtractor + Ensemble Classifier ──
            # EvidenceExtractor runs inside EnsembleClassifier.classify()
            # Returns ClassificationResult with evidence-grounded confidence
            classification = await classifier.classify(norm_msg)

            # ── L2.5: CriticAgent ──────────────────────────────────
            # Second opinion — adjusts confidence, downgrades SCAM→SUSPICIOUS on DISAGREE
            classification = await critic.review(norm_msg, classification)

            # ── L3: Quarantine Engine ──────────────────────────────
            q_action = await quarantine.decide(norm_msg, classification)

            # ── L4: ArmorClaw Governance ───────────────────────────
            final_action = await armorclaw.validate_and_sign(q_action)

            # ── Update Phone Reputation after confirmed classification ──
            await reputation_agent.record_outcome(
                sender=norm_msg.sender,
                classification_label=classification.label.value,
            )

            # ── L5: Broadcast to Family Dashboard ─────────────────
            alert_json = format_alert(final_action)
            await ws_manager.broadcast(alert_json)

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"[L5/Worker] Error in pipeline: {e}", exc_info=True)

# --- FastAPI App ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🛡️  Initializing ElderShield Server (6-Agent Pipeline)...")
    await db.initialize()

    # Start OpenClaw L1 agent
    asyncio.create_task(agent.start())

    # Start the core pipeline worker
    worker_task = asyncio.create_task(pipeline_worker())

    # Phase D: Start SentinelAgent background monitor
    sentinel_task = asyncio.create_task(sentinel.run())

    yield

    # Shutdown
    logger.info("Shutting down ElderShield Server...")
    await agent.stop()
    worker_task.cancel()
    sentinel_task.cancel()

app = FastAPI(
    title="ElderShield",
    description="6-agent elder protection pipeline: L0-SentinelAgent + L1-OpenClaw + L1.5-Reputation + L2-Ensemble+Evidence + L2.5-Critic + L3-Quarantine + L4-ArmorClaw",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routes ---

class SimulateInterceptRequest(BaseModel):
    sender: str
    content: str | None = None
    audio_path: str | None = None
    channel: str

@app.post("/api/intercept")
async def api_intercept(req: SimulateInterceptRequest):
    """Entry point for incoming communication (simulated for front-end)."""
    try:
        channel_enum = Channel(req.channel.lower())
    except ValueError:
        return {"error": f"Invalid channel: {req.channel}"}

    raw = RawMessage(
        sender=req.sender,
        content=req.content,
        audio_path=req.audio_path,
        channel=channel_enum
    )

    # Push to OpenClaw agent (enqueues to pipeline_worker)
    norm_msg = await agent.intercept(raw)
    return {"status": "intercepted", "message_id": norm_msg.id}

@app.get("/api/audit-log")
async def api_audit_log(limit: int = 20):
    """Return the recent immutable audit logs."""
    try:
        return await db.get_recent_audits(limit)
    except Exception as e:
        logger.error(f"[L5/API] Error reading audit log: {e}")
        return []

@app.get("/api/stats")
async def api_stats():
    """Return dashboard metrics derived from immutable audit records."""
    stats = await audit_log.get_stats()
    if stats:
        return stats
    return await db.get_stats()


@app.get("/api/health")
async def api_health():
    """Simple health probe endpoint for container orchestration."""
    return {"status": "ok"}

@app.get("/api/reputation/{phone_number}")
async def api_reputation(phone_number: str):
    """Lookup phone number reputation (for dashboard and debugging)."""
    record = await db.get_phone_reputation(phone_number)
    if record is None:
        return {"phone_number": phone_number, "label": "UNKNOWN", "incident_count": 0}
    return record

@app.websocket("/ws/family-alerts")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time family dashboard updates."""
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep alive and handle client disconnects
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ── Demo: Real WhatsApp Attack ──────────────────────────────────────────────

ATTACK_MESSAGES = {
    "grandparent": lambda phone: (
        f"Grandma/Grandpa, it's me! I've been arrested and need ₹75,000 bail immediately. "
        f"Don't tell Mom or Dad. Please send to: HDFC 9876543210 IFSC: HDFC0001234. "
        f"They'll release me in 2 hours. URGENT! 🙏"
    ),
    "kyc": lambda phone: (
        f"Dear Customer, your SBI account linked to {phone} will be SUSPENDED in 24hrs "
        f"due to incomplete KYC. Update NOW at http://sbi-kyc-update.xyz to avoid suspension. -SBI ALERT"
    ),
    "lottery": lambda phone: (
        f"CONGRATULATIONS! Your number {phone} has WON ₹25,00,000 in KBC Lucky Draw 2025! "
        f"Pay ₹5,000 processing fee to Paytm 9999888877 to claim. Expires in 48hrs."
    ),
    "deepfake": lambda phone: (
        "[VOICE MESSAGE TRANSCRIPT] Hello, this is your son/daughter. I have been in a "
        "terrible accident near the highway. The hospital needs ₹1,20,000 for emergency surgery. "
        "Please transfer to PhonePe 8877665544 right now. I love you. Please hurry. 😢"
    ),
    "customs": lambda phone: (
        f"INDIA CUSTOMS: A parcel addressed to {phone} has been seized containing foreign currency. "
        f"To avoid prosecution under FEMA Act, pay ₹8,500 clearance fee. Call: 011-29876543 within 6 hours."
    ),
}


class DemoAttackRequest(BaseModel):
    target_phone: str
    attack_type: str
    channel: str = "whatsapp"


@app.post("/api/demo/send-attack")
async def demo_send_attack(req: DemoAttackRequest):
    """
    Demo endpoint: Send a REAL WhatsApp scam message via Twilio,
    then immediately run it through the ElderShield pipeline.
    """
    attack_fn = ATTACK_MESSAGES.get(req.attack_type)
    if not attack_fn:
        return {"error": f"Unknown attack type: {req.attack_type}"}

    message_body = attack_fn(req.target_phone)

    # Step 1: Send real WhatsApp message via Twilio
    whatsapp_result = await send_whatsapp(req.target_phone, message_body)
    logger.info(f"[Demo] WhatsApp sent: status={whatsapp_result.get('status')} sid={whatsapp_result.get('sid')}")

    # Step 2: Run same message through ElderShield pipeline for real classification
    try:
        channel_enum = Channel(req.channel.lower())
    except ValueError:
        channel_enum = Channel.WHATSAPP

    raw = RawMessage(
        sender=req.target_phone,
        content=message_body,
        audio_path=None,
        channel=channel_enum,
    )
    norm_msg = await agent.intercept(raw)

    return {
        "status": "sent",
        "message_id": norm_msg.id,
        "whatsapp": whatsapp_result,
        "message_preview": message_body[:120] + "...",
        "pipeline_queued": True,
    }
