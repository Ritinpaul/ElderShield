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
    """Return standard dashboard metrics."""
    return await db.get_stats()

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
