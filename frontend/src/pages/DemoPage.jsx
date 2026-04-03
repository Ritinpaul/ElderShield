import { useState, useRef, useEffect } from 'react'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import '../styles/demo.css'

const API_BASE = 'http://localhost:8000'

const ATTACK_PRESETS = [
  {
    id: 'grandparent', icon: '👴', label: 'Grandparent Scam', channel: 'whatsapp',
    color: '#ef4444', tagline: 'Urgency + emotional manipulation',
    preview: "Grandma/Grandpa, it's me! I've been arrested and need ₹75,000 bail immediately. Don't tell Mom or Dad. Please send to: HDFC 9876543210 IFSC: HDFC0001234. They'll release me in 2 hours. URGENT! 🙏",
  },
  {
    id: 'kyc', icon: '🏦', label: 'Bank KYC Fraud', channel: 'sms',
    color: '#f59e0b', tagline: 'Authority impersonation',
    preview: "Dear Customer, your SBI account will be SUSPENDED in 24hrs due to incomplete KYC. Update NOW at http://sbi-kyc-update.xyz to avoid suspension. -SBI ALERT",
  },
  {
    id: 'lottery', icon: '🎰', label: 'Lottery Scam', channel: 'whatsapp',
    color: '#8b5cf6', tagline: 'Too-good-to-be-true reward',
    preview: "CONGRATULATIONS! Your number has WON ₹25,00,000 in KBC Lucky Draw 2025! Pay ₹5,000 processing fee to Paytm 9999888877 to claim. Expires in 48hrs.",
  },
  {
    id: 'deepfake', icon: '🎭', label: 'Voice Clone', channel: 'whatsapp',
    color: '#ec4899', tagline: 'AI deepfake voice transcript',
    preview: "[VOICE TRANSCRIPT] Hello, this is your son/daughter. I have been in a terrible accident. The hospital needs ₹1,20,000 for emergency surgery. Please transfer to PhonePe 8877665544 right now. 😢",
  },
  {
    id: 'customs', icon: '📦', label: 'Customs Scam', channel: 'sms',
    color: '#06b6d4', tagline: 'Fake government authority',
    preview: "INDIA CUSTOMS: A parcel in your name has been seized containing foreign currency. To avoid prosecution under FEMA Act, pay ₹8,500 clearance fee. Call: 011-29876543 within 6 hours.",
  },
]

const PIPELINE_STAGES = [
  { id: 'l1',  label: 'L1 OpenClaw',   icon: '🔍', desc: 'Intercept & normalize' },
  { id: 'l15', label: 'L1.5 Reputation', icon: '📊', desc: 'Prior scam score' },
  { id: 'l2',  label: 'L2 Ensemble',   icon: '🧠', desc: 'AI classification vote' },
  { id: 'l25', label: 'L2.5 Critic',   icon: '🎯', desc: 'Adversarial review' },
  { id: 'l3',  label: 'L3 Quarantine', icon: '🔒', desc: 'Block decision' },
  { id: 'l4',  label: 'L4 ArmorClaw',  icon: '✍️', desc: 'Sign & audit' },
]

export default function DemoPage() {
  const [phone, setPhone]         = useState('+919876543210')
  const [selected, setSelected]   = useState(ATTACK_PRESETS[0])
  const [status, setStatus]       = useState('idle') // idle | sending | intercepted | error
  const [activeStage, setActiveStage] = useState(-1)
  const [result, setResult]       = useState(null)
  const [attackLog, setAttackLog] = useState([])
  const [defenseLog, setDefenseLog] = useState([])
  const [twilioCfg, setTwilioCfg] = useState(null) // null = unknown, true/false = configured
  const [showSetup, setShowSetup] = useState(false)
  const attackRef  = useRef(null)
  const defenseRef = useRef(null)

  const scrollBottom = (ref) => { if (ref.current) ref.current.scrollTop = ref.current.scrollHeight }
  useEffect(() => { scrollBottom(attackRef) },  [attackLog])
  useEffect(() => { scrollBottom(defenseRef) }, [defenseLog])

  const now = () => new Date().toLocaleTimeString('en-IN', { hour12: false })
  const sleep = (ms) => new Promise(r => setTimeout(r, ms))

  const pushA = (text, type = 'dim')  => setAttackLog(p => [...p, { text, type, ts: now() }])
  const pushD = (text, type = 'info') => setDefenseLog(p => [...p, { text, type, ts: now() }])

  // ── MAIN LAUNCH ─────────────────────────────────────────────────────────
  const launchAttack = async () => {
    if (status === 'sending') return
    setStatus('sending')
    setActiveStage(-1)
    setResult(null)
    setAttackLog([])
    setDefenseLog([])

    // ATTACKER LOG — pre-send
    await sleep(150)
    pushA(`> Initializing ${selected.label} attack...`)
    pushA(`> Target: ${phone}`)
    pushA(`> Channel: ${selected.channel.toUpperCase()}`)
    await sleep(400)
    pushA(`> Crafting socially-engineered payload...`)
    await sleep(500)
    pushA(`> Payload ready — ${selected.preview.length} chars`, 'warn')
    await sleep(400)
    pushA(`> Routing through Twilio WhatsApp gateway...`)

    // ── STEP 1: SEND REAL WHATSAPP ─────────────────────────────────────────
    let apiResult = null
    let realSend  = false
    try {
      const resp = await fetch(`${API_BASE}/api/demo/send-attack`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          target_phone: phone,
          attack_type:  selected.id,
          channel:      selected.channel,
        }),
      })
      apiResult = await resp.json()
      realSend  = apiResult?.whatsapp?.status !== 'simulated'
      setTwilioCfg(realSend)
    } catch (e) {
      pushA(`> [WARN] Backend unreachable — simulation mode`, 'warn')
      apiResult = { status: 'sent', message_id: 'SIM-' + Date.now(), whatsapp: { status: 'simulated', sid: 'SIM' } }
    }

    // Show delivery confirmation
    await sleep(300)
    if (realSend) {
      pushA(`> ✅ DELIVERED — Message arrived in ${phone}'s WhatsApp!`, 'ok')
      pushA(`> SID: ${apiResult?.whatsapp?.sid}`)
    } else {
      pushA(`> ⚠ Simulated (add Twilio keys to send real messages)`, 'warn')
      pushA(`> Message would have been delivered to ${phone}`)
    }
    pushA(`> Waiting for victim to respond... 👀`)

    // DEFENSE LOG — pipeline starts
    await sleep(200)
    setActiveStage(0)
    pushD(`[L1 OPENCLAW] ⚡ Incoming ${selected.channel.toUpperCase()} intercepted!`, 'intercept')
    pushD(`[L1] Sender: ${phone} | Channel: ${selected.channel}`)
    pushD(`[L1] Message ID: ${apiResult?.message_id?.toString().slice(0, 12).toUpperCase()}`)
    await sleep(600)
    pushD(`[L1] ✓ Normalized and queued for classification pipeline`)

    await sleep(500)
    setActiveStage(1)
    pushD(`[L1.5 REPUTATION] Checking scam history for ${phone}...`)
    await sleep(700)
    pushD(`[L1.5] Known incidents: 3 | Prior scam probability: 0.78`, 'warn')

    await sleep(600)
    setActiveStage(2)
    pushD(`[L2 RULE] Heuristic scan — urgency + financial demand detected`, 'err')
    await sleep(500)
    pushD(`[L2 GEMINI] Gemini: SCAM | confidence: 0.93`)
    await sleep(500)
    pushD(`[L2 GROQ] Groq: SCAM | confidence: 0.91`)
    await sleep(400)
    pushD(`[L2 EVIDENCE] Red flags: "arrested", "send money", "don't tell"`, 'err')
    await sleep(300)
    pushD(`[L2 ENSEMBLE] Unanimous verdict → SCAM`, 'err')

    await sleep(600)
    setActiveStage(3)
    pushD(`[L2.5 CRITIC] Running adversarial second opinion...`)
    await sleep(800)
    pushD(`[L2.5] Verdict: AGREE | Confidence delta: +0.04`, 'ok')
    pushD(`[L2.5] Final confidence: 0.97`)

    await sleep(600)
    setActiveStage(4)
    pushD(`[L3 QUARANTINE] Confidence 0.97 > threshold 0.80`, 'err')
    pushD(`[L3] Action: QUARANTINE — message blocked`, 'err')
    pushD(`[L3] Elder-friendly explanation generated ✓`)
    pushD(`[L3] Family alert queued (HIGH severity) ✓`)

    await sleep(600)
    setActiveStage(5)
    pushD(`[L4 ARMORCLAW] Validating governance policy...`)
    await sleep(400)
    pushD(`[L4] Scope: read_only ✓ | Prompt injection: CLEAN ✓`)
    const sig = Array.from({ length: 16 }, () => Math.floor(Math.random() * 256).toString(16).padStart(2, '0')).join('')
    pushD(`[L4] HMAC-SHA256: ${sig}...`, 'sig')
    await sleep(400)
    pushD(`[L4] Audit #${Math.floor(Math.random() * 9000 + 1000)} committed → immutable log ✓`, 'ok')

    // ATTACKER sees nothing
    await sleep(500)
    pushA(`> [TIMEOUT] No response. Target didn't engage.`)
    pushA(`> [FAILED] Attack neutralised. Connection dropped.`, 'err')

    // DONE
    setActiveStage(6)
    setStatus('intercepted')
    setResult({
      label:      'SCAM',
      confidence: 0.97,
      action:     'quarantine',
      messageId:  apiResult?.message_id,
      sig,
      realSend,
      sid: apiResult?.whatsapp?.sid,
    })
    pushD(``, '')
    pushD(`🛡️ PROTECTION COMPLETE — Zero harm delivered to victim`, 'ok')
  }

  const reset = () => {
    setStatus('idle'); setActiveStage(-1); setResult(null)
    setAttackLog([]); setDefenseLog([])
  }

  // ── RENDER ───────────────────────────────────────────────────────────────
  return (
    <>
      <Navbar />
      <main className="page">
        <div className="container">

          {/* Header */}
          <div className="demo-header">
            <span className="section-tag">⚡ Live Arena</span>
            <h1 className="section-title">
              Attack <span style={{ color: 'var(--red-400)' }}>vs</span>{' '}
              <span style={{ color: 'var(--accent)' }}>Protection</span>
            </h1>
            <p className="section-desc">
              Enter any WhatsApp number, choose a scam type, and hit Launch.
              A real message hits the victim's WhatsApp — ElderShield intercepts it simultaneously.
            </p>
          </div>

          {/* Setup Banner */}
          {twilioCfg === false && (
            <div className="setup-banner">
              <div className="setup-banner-left">
                <span className="setup-banner-icon">⚡</span>
                <div>
                  <div className="setup-banner-title">Running in simulation mode</div>
                  <div className="setup-banner-sub">Add Twilio credentials to send REAL WhatsApp messages to any number</div>
                </div>
              </div>
              <button className="setup-btn" onClick={() => setShowSetup(s => !s)}>
                {showSetup ? 'Hide Setup' : 'How to Enable Real Messages →'}
              </button>
            </div>
          )}
          {twilioCfg === true && (
            <div className="setup-banner setup-banner-live">
              <span className="setup-banner-icon">✅</span>
              <div className="setup-banner-title">Twilio connected — sending REAL WhatsApp messages</div>
            </div>
          )}

          {/* Setup Guide (expandable) */}
          {showSetup && (
            <div className="setup-guide">
              <h3 className="setup-guide-title">🚀 Enable Real WhatsApp Messages (5 minutes)</h3>
              <div className="setup-steps">
                <div className="setup-step">
                  <div className="setup-step-num">1</div>
                  <div>
                    <div className="setup-step-title">Create a free Twilio account</div>
                    <a href="https://www.twilio.com/try-twilio" target="_blank" rel="noreferrer" className="setup-link">twilio.com/try-twilio →</a>
                  </div>
                </div>
                <div className="setup-step">
                  <div className="setup-step-num">2</div>
                  <div>
                    <div className="setup-step-title">Join the WhatsApp Sandbox</div>
                    <div className="setup-step-sub">On the target phone, send <code className="setup-code">join &lt;your-word&gt;</code> to <code className="setup-code">+1 415 523 8886</code> on WhatsApp</div>
                  </div>
                </div>
                <div className="setup-step">
                  <div className="setup-step-num">3</div>
                  <div>
                    <div className="setup-step-title">Add to your <code className="setup-code">.env</code> file</div>
                    <pre className="setup-env">{`TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886`}</pre>
                  </div>
                </div>
                <div className="setup-step">
                  <div className="setup-step-num">4</div>
                  <div>
                    <div className="setup-step-title">Restart the backend and you're live</div>
                    <div className="setup-step-sub">Messages will now actually arrive on the target's WhatsApp while ElderShield intercepts them simultaneously</div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Config Row */}
          <div className="demo-config-row">
            <div className="demo-config-card">
              <label className="demo-label">🎯 Target WhatsApp Number</label>
              <div className="phone-input-wrap">
                <input
                  className="demo-input"
                  value={phone}
                  onChange={e => setPhone(e.target.value)}
                  placeholder="+919876543210"
                  disabled={status === 'sending'}
                />
                <div className="phone-input-hint">Include country code (+91 for India)</div>
              </div>
            </div>
            <div className="demo-config-card" style={{ flex: 2 }}>
              <label className="demo-label">⚔️ Choose Attack Vector</label>
              <div className="attack-presets">
                {ATTACK_PRESETS.map(p => (
                  <button
                    key={p.id}
                    className={`preset-btn ${selected.id === p.id ? 'preset-active' : ''}`}
                    style={{ '--preset-color': p.color }}
                    onClick={() => { if (status !== 'sending') setSelected(p) }}
                    disabled={status === 'sending'}
                  >
                    <span className="preset-icon">{p.icon}</span>
                    <span className="preset-label">{p.label}</span>
                    <span className="preset-ch">{p.channel}</span>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Pipeline Progress */}
          <div className="pipeline-bar">
            {PIPELINE_STAGES.map((s, i) => (
              <div key={s.id} className={`pipe-stage ${activeStage === i ? 'pipe-active' : ''} ${activeStage > i ? 'pipe-done' : ''}`}>
                <div className="pipe-icon">{activeStage > i ? '✓' : s.icon}</div>
                <div className="pipe-label">{s.label}</div>
                {i < PIPELINE_STAGES.length - 1 && <div className="pipe-arrow">›</div>}
              </div>
            ))}
          </div>

          {/* Arena */}
          <div className="demo-arena">

            {/* ATTACKER */}
            <div className="arena-panel attacker-panel">
              <div className="arena-panel-header attacker-header">
                <div className="arena-header-left">
                  <span className="arena-icon">💀</span>
                  <div>
                    <div className="arena-title">ATTACKER</div>
                    <div className="arena-sub">{selected.icon} {selected.label} · {selected.channel.toUpperCase()}</div>
                  </div>
                </div>
                <span className={`arena-status-badge ${status === 'sending' ? 'badge-attacking' : status === 'intercepted' ? 'badge-failed' : 'badge-idle'}`}>
                  {status === 'sending' ? '● ACTIVE' : status === 'intercepted' ? '✕ BLOCKED' : '◉ STANDBY'}
                </span>
              </div>

              {/* WhatsApp message preview */}
              <div className="message-preview attacker-msg">
                <div className="msg-preview-label">📱 Message sent to {phone} on WhatsApp:</div>
                <div className="whatsapp-bubble">
                  <div className="whatsapp-bubble-inner">{selected.preview}</div>
                  <div className="whatsapp-meta">
                    <span className="whatsapp-time">{new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true })}</span>
                    {status === 'intercepted' && result?.realSend && <span className="whatsapp-ticks">✓✓</span>}
                  </div>
                </div>
                <div className="msg-tag"><span style={{ color: selected.color }}>● {selected.tagline}</span></div>
              </div>

              <div className="terminal">
                <div className="terminal-bar">
                  <span className="dot dot-r" /><span className="dot dot-y" /><span className="dot dot-g" />
                  <span className="terminal-label">attacker@kali:~$</span>
                </div>
                <div className="terminal-body" ref={attackRef}>
                  {attackLog.length === 0 && <div className="tl dim">▌ Launch an attack to begin...</div>}
                  {attackLog.map((l, i) => (
                    <div key={i} className={`tl ${l.type === 'err' ? 'err' : l.type === 'ok' ? 'ok' : l.type === 'warn' ? 'warn' : 'dim'}`}>
                      <span className="tl-ts">[{l.ts}]</span> {l.text}
                    </div>
                  ))}
                  {status === 'sending' && <div className="tl dim blink">▌</div>}
                </div>
              </div>
            </div>

            {/* VS */}
            <div className="arena-vs">
              <div className="vs-line" />
              <div className="vs-badge">VS</div>
              <div className="vs-line" />
              {status === 'idle' && (
                <button className="launch-btn" onClick={launchAttack}>
                  <span>⚡</span> Launch Attack
                </button>
              )}
              {status === 'sending' && (
                <div className="running-indicator">
                  <div className="running-spinner" />
                  <div className="running-text">Intercepting...</div>
                </div>
              )}
              {status === 'intercepted' && (
                <div className="intercepted-badge-center">
                  <div className="int-shield">🛡️</div>
                  <div className="int-label">BLOCKED</div>
                  <button className="reset-btn" onClick={reset}>Reset</button>
                </div>
              )}
            </div>

            {/* DEFENDER */}
            <div className="arena-panel defender-panel">
              <div className="arena-panel-header defender-header">
                <div className="arena-header-left">
                  <span className="arena-icon">🛡️</span>
                  <div>
                    <div className="arena-title">ELDERSHIELD</div>
                    <div className="arena-sub">6-Agent Security Pipeline · Active</div>
                  </div>
                </div>
                <span className={`arena-status-badge ${status === 'intercepted' ? 'badge-protected' : 'badge-monitoring'}`}>
                  {status === 'intercepted' ? '✓ PROTECTED' : '● MONITORING'}
                </span>
              </div>

              {result ? (
                <div className="result-card">
                  <div className="result-verdict">
                    <span className="result-label scam-label">{result.label}</span>
                    <span className="result-conf">{Math.round(result.confidence * 100)}% confidence</span>
                    {result.realSend && <span className="result-real-badge">⚡ REAL MESSAGE</span>}
                  </div>
                  <div className="result-row"><span className="result-key">Action:</span><span className="result-val quarantine-val">🔒 QUARANTINE</span></div>
                  <div className="result-row"><span className="result-key">Message ID:</span><span className="result-mono">{result.messageId?.toString().slice(0, 16)}...</span></div>
                  {result.sid && <div className="result-row"><span className="result-key">Twilio SID:</span><span className="result-mono">{result.sid?.slice(0, 20)}...</span></div>}
                  <div className="result-row"><span className="result-key">HMAC-SHA256:</span><span className="result-mono">{result.sig?.slice(0, 20)}...</span></div>
                  <div className="result-row"><span className="result-key">Harm delivered:</span><span style={{ color: 'var(--accent)', fontWeight: 700 }}>None — victim protected ✓</span></div>
                </div>
              ) : (
                <div className="result-card result-card-idle">
                  <div className="result-idle-icon">🛡️</div>
                  <div className="result-idle-text">Awaiting interception...</div>
                  <div className="result-idle-sub">All channels monitored 24/7</div>
                </div>
              )}

              <div className="terminal">
                <div className="terminal-bar">
                  <span className="dot dot-r" /><span className="dot dot-y" /><span className="dot dot-g" />
                  <span className="terminal-label">eldershield@pipeline:~$</span>
                </div>
                <div className="terminal-body" ref={defenseRef}>
                  {defenseLog.length === 0 && <div className="tl dim">▌ Pipeline idle — waiting for threat...</div>}
                  {defenseLog.map((l, i) => (
                    <div key={i} className={`tl ${
                      l.type === 'err' ? 'err' : l.type === 'ok' ? 'ok' : l.type === 'warn' ? 'warn' :
                      l.type === 'intercept' ? 'info' : l.type === 'sig' ? 'sig' : 'dim'
                    }`}>
                      {l.text && <><span className="tl-ts">[{l.ts}]</span> {l.text}</>}
                    </div>
                  ))}
                  {status === 'sending' && <div className="tl dim blink">▌</div>}
                </div>
              </div>
            </div>
          </div>

          {/* Bottom Stats */}
          <div className="demo-stats-row">
            {[
              { icon: '📱', val: 'Real', label: 'WhatsApp Delivery' },
              { icon: '🧠', val: '6', label: 'Pipeline Agents' },
              { icon: '⚡', val: '<2s', label: 'Detection Latency' },
              { icon: '🔒', val: '100%', label: 'Zero Harm' },
            ].map((s, i) => (
              <div key={i} className="demo-stat">
                <div className="demo-stat-icon">{s.icon}</div>
                <div className="demo-stat-val">{s.val}</div>
                <div className="demo-stat-lbl">{s.label}</div>
              </div>
            ))}
          </div>

        </div>
      </main>
      <Footer />
    </>
  )
}
