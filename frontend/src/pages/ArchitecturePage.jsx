import { useEffect } from 'react'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import '../styles/architecture.css'

export default function ArchitecturePage() {
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
      <Navbar />
      <main className="page">
        <div className="container">
          <div className="page-header" style={{textAlign:'center', paddingTop:'40px'}}>
            <h1 className="section-title">Defense-in-Depth <span style={{color:'#ccff23'}}>Pipeline</span></h1>
            <p className="section-desc" style={{margin:'0 auto'}}>5 sequential layers of strict governance and AI inference.</p>
          </div>

          <div className="arch-casino-wrap">
            {/* 5-Layer Pipeline */}
            <div className="ac-pipeline reveal">
              {/* L1 */}
              <div className="ac-card ac-dark">
                <div className="ac-num">L1</div>
                <div className="ac-icon">🔍</div>
                <h3 className="ac-name">OpenClaw Agent</h3>
                <p className="ac-desc">Background daemon. Seamlessly intercepts SMS, WhatsApp, &amp; Voice streams.</p>
              </div>
              <div className="ac-arrow">→</div>
              {/* L2 */}
              <div className="ac-card ac-lime">
                <div className="ac-num">L2</div>
                <div className="ac-icon">🧠</div>
                <h3 className="ac-name">Intent<br/>Analysis</h3>
                <p className="ac-desc">Dual-LLM (Gemma 2B + GPT-4o) evaluates payload semantics. 94% accuracy.</p>
              </div>
              <div className="ac-arrow">→</div>
              {/* L3 */}
              <div className="ac-card ac-dark">
                <div className="ac-num">L3</div>
                <div className="ac-icon">🚫</div>
                <h3 className="ac-name">Quarantine<br/>Engine</h3>
                <p className="ac-desc">SCAM → Block.<br/>SUSPICIOUS → Hold.<br/>BENIGN → Deliver safely.</p>
              </div>
              <div className="ac-arrow">→</div>
              {/* L4 */}
              <div className="ac-card ac-purple">
                <div className="ac-num">L4</div>
                <div className="ac-icon">🔐</div>
                <h3 className="ac-name">ArmorClaw<br/>Governance</h3>
                <p className="ac-desc">Action scoped verification. Cryptographic signing. Fail-closed.</p>
              </div>
              <div className="ac-arrow">→</div>
              {/* L5 */}
              <div className="ac-card ac-dark">
                <div className="ac-num">L5</div>
                <div className="ac-icon">📊</div>
                <h3 className="ac-name">Family<br/>Dashboard</h3>
                <p className="ac-desc">Real-time WebSocket alerts to authorized family members instantly.</p>
              </div>
            </div>

            {/* Trust Contract */}
            <div className="ac-bento reveal">
              <div className="ac-bento-card">
                <div className="ac-bento-title ac-can-title">✅ AGENT CAN</div>
                <ul className="ac-list">
                  <li><span>✅</span> Read incoming messages for content analysis</li>
                  <li><span>✅</span> Classify messages with confidence scores</li>
                  <li><span>✅</span> Quarantine or hold suspicious content</li>
                  <li><span>✅</span> Alert family members via WebSocket push</li>
                  <li><span>✅</span> Display elder-friendly explanations</li>
                </ul>
              </div>
              <div className="ac-bento-card">
                <div className="ac-bento-title ac-cannot-title">❌ AGENT CANNOT</div>
                <ul className="ac-list">
                  <li><span>❌</span> Modify messages before quarantine</li>
                  <li><span>❌</span> Exfiltrate user data to external endpoints</li>
                  <li><span>❌</span> Change its own enforcement policies</li>
                  <li><span>❌</span> Perform silent actions without logging</li>
                  <li><span>❌</span> Respond to prompt injection commands</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </>
  )
}
