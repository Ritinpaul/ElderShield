# ElderShield 🛡️

**A real-time, multi-agent communication security platform designed to protect elderly individuals from scams, phishing, and social engineering attacks across all digital channels.**

ElderShield sits silently between the communication channel and the user — intercepting every incoming message and running it through a 6-agent AI pipeline before it ever reaches the screen. When a threat is detected, the family is alerted instantly via a live dashboard.

---

## How It Works

ElderShield operates as a **layered security pipeline**. Every incoming message — whether a WhatsApp text, SMS, email, or voice call — is processed through six sequential agents, each adding a layer of intelligence and accountability.

```
Incoming Message
      │
      ▼
[L1]  OpenClawAgent       – Intercepts and normalizes all channels
      │
      ▼
[L1.5] PhoneReputationAgent – Bayesian prior scoring from call history
      │
      ▼
[L2]  EvidenceExtractor    – Grounds classification in verbatim evidence
      + EnsembleClassifier – Votes across rule-based, Gemini, and Groq models
      │
      ▼
[L2.5] CriticAgent         – Adversarial second opinion, downgrades on DISAGREE
      │
      ▼
[L3]  QuarantineEngine     – Decides: DELIVER / HOLD FOR REVIEW / QUARANTINE
      │
      ▼
[L4]  ArmorClaw            – Governance, HMAC-SHA256 signing, audit log
      │
      ▼
[L5]  Family Dashboard     – Real-time WebSocket alerts to trusted contacts
```

---

## Features

- **Multi-Channel Monitoring** — WhatsApp, SMS, Email, and Voice calls all processed through a single unified pipeline
- **Ensemble AI Classification** — Three independent classifiers (rule-based heuristics, Google Gemini, Groq) vote on each message to minimize false positives
- **Evidence-Grounded Decisions** — The EvidenceExtractor anchors every classification in verbatim quotes from the message, eliminating AI hallucinations
- **Adversarial Verification** — The CriticAgent challenges every high-confidence decision, downgrading uncertain SCAM verdicts to SUSPICIOUS
- **Longitudinal Pattern Analysis** — SentinelAgent tracks repeat offenders across time, intensifying scrutiny on known bad actors
- **Cryptographic Audit Trail** — Every action is HMAC-SHA256 signed and written to an immutable audit log by the ArmorClaw governance layer
- **Elder-Friendly Explainability** — Blocked messages come with plain-language explanations written for non-technical users
- **Real-Time Family Alerts** — Trusted contacts receive instant WebSocket push notifications when a threat is quarantined

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend Framework | FastAPI (async) |
| AI Classification | Google Gemini API, Groq API |
| Database | SQLite (async, via aiosqlite) |
| Data Validation | Pydantic v2 |
| Inter-agent Communication | asyncio.Queue |
| Real-Time Alerts | WebSockets |
| Security | HMAC-SHA256, prompt injection detection |
| Frontend | React + Vite |

---

## Project Structure

```
ElderShield/
├── backend/
│   ├── main.py                  # FastAPI app & pipeline entrypoint
│   ├── agent/
│   │   ├── openclaw_agent.py    # L1: Channel interceptor & normalizer daemon
│   │   ├── normalizer.py        # Message normalization across channels
│   │   ├── reputation_agent.py  # L1.5: Phone reputation scoring
│   │   ├── sentinel_agent.py    # L0: Longitudinal pattern monitor
│   │   └── interceptor.py       # Low-level channel interception helpers
│   ├── classifier/
│   │   ├── ensemble.py          # Multi-model voting orchestrator
│   │   ├── rule_classifier.py   # Heuristic pattern-matching (no API required)
│   │   ├── gemini_classifier.py # Google Gemini LLM classifier
│   │   ├── groq_classifier.py   # Groq LLM classifier
│   │   ├── evidence_extractor.py# Verbatim evidence grounding
│   │   ├── critic_agent.py      # Adversarial second-opinion agent
│   │   └── prompts.py           # Structured prompt templates
│   ├── armorclaw/
│   │   ├── governance.py        # L4: Validate, sign, and enforce policy
│   │   ├── audit_log.py         # Immutable append-only audit log
│   │   ├── signer.py            # HMAC-SHA256 cryptographic signing
│   │   └── validator.py         # Prompt injection & governance checks
│   ├── quarantine/
│   │   ├── engine.py            # L3: DELIVER / HOLD / QUARANTINE decisions
│   │   └── explainer.py         # Elder-friendly plain-language explanations
│   ├── notifications/
│   │   └── family_alert.py      # WebSocket alert formatting & dispatch
│   ├── database/
│   │   └── db.py                # Async SQLite data access layer
│   ├── models/
│   │   └── schemas.py           # Pydantic data contracts for all pipeline layers
│   └── requirements.txt
├── frontend/
│   ├── index.html               # Landing page
│   ├── dashboard.html           # Real-time family monitoring dashboard
│   ├── features.html            # Feature overview
│   ├── architecture.html        # Pipeline architecture diagram
│   ├── audit.html               # Audit log viewer
│   ├── demo.html                # Interactive demo
│   ├── styles.css               # Global design system
│   └── app.js                   # Shared JavaScript utilities
├── tests/
│   ├── test_phase1.py           # L1 interception & normalization tests
│   ├── test_phase2.py           # L2 ensemble classification tests
│   ├── test_phase3.py           # L3 quarantine engine tests
│   └── test_phase4.py           # L4 governance & signing tests
├── .env.example
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- A [Google Gemini API key](https://aistudio.google.com/)
- A [Groq API key](https://console.groq.com/)

### Installation

```bash
# Clone the repository
git clone https://github.com/Ritinpaul/ElderShield.git
cd ElderShield

# Create a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# Install dependencies
pip install -r backend/requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and add your API keys
```

### Environment Variables

```env
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here
HMAC_SECRET=your_secret_signing_key_here
DATABASE_URL=eldershield.db
```

### Running the Server

```bash
uvicorn backend.main:app --reload
```

The API will be available at `http://localhost:8000`.  
Interactive API docs: `http://localhost:8000/docs`

### Running the Frontend

Run the Vite app:

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173` and proxies `/api` and `/ws` to the backend.

### Running with Docker

```bash
docker compose up --build
```

- Frontend: `http://localhost:5173`
- Backend API (via frontend proxy): `/api/*`

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/intercept` | Submit a message into the pipeline |
| `GET` | `/api/audit-log` | Retrieve the signed audit log |
| `GET` | `/api/stats` | Dashboard statistics |
| `GET` | `/api/reputation/{phone}` | Look up a phone number's reputation score |
| `WS` | `/ws/family-alerts` | Real-time WebSocket stream for family dashboard |

### Example: Intercepting a Message

```bash
curl -X POST http://localhost:8000/api/intercept \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "whatsapp",
    "sender": "+91-9876543210",
    "content": "Grandma, I am in jail, please send ₹50,000 urgently!",
    "audio_path": null
  }'
```

**Response:**
```json
{
  "status": "intercepted",
  "message_id": "a3f2c1b0-..."
}
```

The message is now flowing through the pipeline. Within milliseconds, the family dashboard WebSocket will receive a threat alert if the message is classified as SCAM or SUSPICIOUS.

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Security Design

ElderShield is built around the principle of **zero trust for incoming communications**:

- **No message is delivered without classification** — every message is intercepted at L1 before the user sees it
- **Governance is non-bypassable** — no classifier or agent can deliver a quarantined message without L4 ArmorClaw validation and signing
- **All decisions are auditable** — every action taken on every message is recorded in an immutable, HMAC-signed audit log
- **Prompt injection is actively detected** — the ArmorClaw validator checks classification inputs for adversarial injection attempts
- **AI disagreement is treated conservatively** — when the CriticAgent disagrees with a SCAM verdict, the label is automatically downgraded to SUSPICIOUS rather than silently accepted

---

## License

[MIT](LICENSE)
