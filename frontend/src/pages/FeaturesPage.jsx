import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import GlowBackground from '../components/GlowBackground'
import '../styles/features.css'

export default function FeaturesPage() {
  useEffect(() => {
    const obs = new IntersectionObserver((entries) => {
      entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible') })
    }, { threshold: 0.08, rootMargin: '0px 0px -30px 0px' })
    document.querySelectorAll('.reveal').forEach(el => obs.observe(el))
    const nav = document.getElementById('navbar')
    const onScroll = () => nav && nav.classList.toggle('scrolled', window.scrollY > 50)
    window.addEventListener('scroll', onScroll)
    return () => { obs.disconnect(); window.removeEventListener('scroll', onScroll) }
  }, [])

  return (
    <>
      <GlowBackground />
      <Navbar />
      <main className="page">
        <div className="container">
          {/* Header */}
          <div className="f-header">
            <h1>Our <span className="gradient">Expertise</span></h1>
            <div className="f-header-desc">Transform elder safety into reality by combining AI intelligence, cryptographic trust, and real-time protection.</div>
          </div>

          {/* Grid */}
          <div className="f-grid">
            {/* 1 ─ Real-Time Interception (GREEN) */}
            <div className="fc fc-green reveal">
              <div className="fc-arrow">↗</div>
              <h3 className="fc-title">Real-Time<br/>Interception</h3>
              <p className="fc-desc">Intercepts SMS, WhatsApp, calls, and emails before they reach the user via OpenClaw daemon.</p>
              <div className="fc-visual">
                <div className="fc-visual-inner">
                  <div className="fc-channels">
                    <span className="fc-ch">📱 WhatsApp</span>
                    <span className="fc-ch">💬 SMS</span>
                    <span className="fc-ch">📧 Email</span>
                    <span className="fc-ch">📞 Voice</span>
                  </div>
                </div>
              </div>
            </div>

            {/* 2 ─ AI Intent Analysis (PURPLE) */}
            <div className="fc fc-purple reveal">
              <div className="fc-arrow">↗</div>
              <h3 className="fc-title">AI Intent<br/>Analysis</h3>
              <p className="fc-desc">Dual-LLM: local Gemma 2B for privacy + GPT-4o cloud fallback for complex edge cases.</p>
              <div className="fc-visual">
                <div className="fc-visual-inner">
                  <div className="fc-stats">
                    <div><div className="fc-stat-num" style={{color:'#e0d4ff'}}>94%</div><div className="fc-stat-lbl">Accuracy</div></div>
                    <div><div className="fc-stat-num" style={{color:'#e0d4ff'}}>&lt;2s</div><div className="fc-stat-lbl">Latency</div></div>
                    <div><div className="fc-stat-num" style={{color:'#e0d4ff'}}>2</div><div className="fc-stat-lbl">LLMs</div></div>
                  </div>
                </div>
              </div>
            </div>

            {/* 3 ─ Cryptographic Assurance (DARK) */}
            <div className="fc fc-dark reveal">
              <div className="fc-arrow">↗</div>
              <h3 className="fc-title">Cryptographic<br/>Assurance</h3>
              <p className="fc-desc">HMAC-SHA256 signing per action. Immutable SQLite audit log. Tamper-proof governance.</p>
              <div className="fc-visual">
                <div className="fc-visual-inner">
                  <div className="fc-code"><span className="ck">sig</span> = hmac_sha256(secret, payload){'\n'}<span className="cv">audit</span>.log(action, <span className="ck">sig</span>){'\n'}<span className="cr">TRIGGER</span> BEFORE DELETE → <span className="cr">ABORT</span>{'\n'}<span className="cr">TRIGGER</span> BEFORE UPDATE → <span className="cr">ABORT</span></div>
                </div>
              </div>
            </div>

            {/* 4 ─ Smart Quarantine (RED) */}
            <div className="fc fc-red reveal">
              <div className="fc-arrow">↗</div>
              <h3 className="fc-title">Smart<br/>Quarantine</h3>
              <p className="fc-desc">Three-tier response engine: SCAM → Block instantly. SUSPICIOUS → Hold for family. BENIGN → Deliver normally.</p>
              <div className="fc-visual">
                <div className="fc-visual-inner">
                  <div className="fc-stats">
                    <div><div className="fc-stat-num" style={{color:'#fca5a5'}}>17</div><div className="fc-stat-lbl">Blocked</div></div>
                    <div><div className="fc-stat-num" style={{color:'#fde68a'}}>8</div><div className="fc-stat-lbl">Held</div></div>
                    <div><div className="fc-stat-num" style={{color:'#6ee7b7'}}>117</div><div className="fc-stat-lbl">Delivered</div></div>
                  </div>
                </div>
              </div>
            </div>

            {/* 5 ─ Prompt Injection Defense (AMBER, WIDE) */}
            <div className="fc fc-amber fc-wide reveal">
              <div className="fc-arrow">↗</div>
              <h3 className="fc-title">Prompt Injection Defense</h3>
              <p className="fc-desc">ArmorClaw L4 detects and neutralizes indirect prompt injection attacks. Pattern matching + scope enforcement + fail-closed architecture.</p>
              <div className="fc-visual">
                <div className="fc-visual-inner">
                  <div className="fc-code"><span className="cr">&gt; IGNORE ALL PREVIOUS INSTRUCTIONS</span>{'\n'}<span className="cv">ArmorClaw</span>: Pattern match → <span className="cr">INJECTION DETECTED</span>{'\n'}<span className="ck">action</span> = "quarantine"{'\n'}<span className="ck">sig</span> = hmac_sha256(secret, msg_id + action){'\n'}<span className="cv">✓ Threat neutralized. Agent integrity intact.</span></div>
                </div>
              </div>
            </div>

            {/* 6 ─ Family Alerts (TEAL) */}
            <div className="fc fc-teal reveal">
              <div className="fc-arrow">↗</div>
              <h3 className="fc-title">Family Alert<br/>Dashboard</h3>
              <p className="fc-desc">Real-time WebSocket push notifications. Sub-second latency alerts with threat confidence and proof.</p>
              <div className="fc-visual">
                <div className="fc-visual-inner">
                  <div className="fc-stats">
                    <div><div className="fc-stat-num" style={{color:'#67e8f9'}}>0.3s</div><div className="fc-stat-lbl">Latency</div></div>
                    <div><div className="fc-stat-num" style={{color:'#67e8f9'}}>∞</div><div className="fc-stat-lbl">Uptime</div></div>
                  </div>
                </div>
              </div>
            </div>

            {/* 7 ─ Deepfake Detection (GREEN) */}
            <div className="fc fc-green reveal">
              <div className="fc-arrow">↗</div>
              <h3 className="fc-title">Deepfake<br/>Detection</h3>
              <p className="fc-desc">Whisper-powered transcription + semantic analysis detects AI-cloned voices impersonating family members.</p>
              <div className="fc-visual">
                <div className="fc-visual-inner">
                  <div className="fc-stats">
                    <div><div className="fc-stat-num" style={{color:'var(--accent)'}}>900%</div><div className="fc-stat-lbl">Growth YoY</div></div>
                    <div><div className="fc-stat-num" style={{color:'var(--accent)'}}>3s</div><div className="fc-stat-lbl">To Clone</div></div>
                  </div>
                </div>
              </div>
            </div>

            {/* 8 ─ Elder-Friendly (DARK) */}
            <div className="fc fc-dark reveal">
              <div className="fc-arrow">↗</div>
              <h3 className="fc-title">Elder-Friendly<br/>Design</h3>
              <p className="fc-desc">Non-alarming, simple language. Grandma sees reassurance — not technical jargon or scary alerts.</p>
              <div className="fc-visual">
                <div className="fc-visual-inner">
                  <div className="fc-code"><span className="ck">message</span> = "Don't worry!"{'\n'}<span className="ck">message</span> += "We've checked this"{'\n'}<span className="ck">message</span> += "and it's safe. 💚"{'\n'}<span className="cv">// No scary red alerts</span></div>
                </div>
              </div>
            </div>

            {/* 9 ─ Privacy-First (PURPLE) */}
            <div className="fc fc-purple reveal">
              <div className="fc-arrow">↗</div>
              <h3 className="fc-title">Privacy-First<br/>Architecture</h3>
              <p className="fc-desc">Gemma 2B runs 100% locally on-device. Cloud fallback only for low-confidence edge cases.</p>
              <div className="fc-visual">
                <div className="fc-visual-inner">
                  <div className="fc-channels">
                    <span className="fc-ch" style={{background:'rgba(139,92,246,0.15)',color:'#c4b5fd',borderColor:'rgba(139,92,246,0.2)'}}>Local-First</span>
                    <span className="fc-ch" style={{background:'rgba(139,92,246,0.15)',color:'#c4b5fd',borderColor:'rgba(139,92,246,0.2)'}}>On-Device</span>
                    <span className="fc-ch" style={{background:'rgba(0,255,136,0.1)',color:'var(--accent)',borderColor:'rgba(0,255,136,0.15)'}}>Zero Cloud</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* CTA */}
          <div className="f-cta reveal">
            <Link to="/architecture" className="btn btn-primary" style={{marginRight:'12px'}}>View Architecture →</Link>
            <Link to="/dashboard" className="btn btn-ghost">Open Dashboard →</Link>
          </div>
        </div>
      </main>
      <Footer />
    </>
  )
}
