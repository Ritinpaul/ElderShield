import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import GlowBackground from '../components/GlowBackground'

export default function HomePage() {
  useEffect(() => {
    // Scroll reveal
    const obs = new IntersectionObserver((entries) => {
      entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('visible') })
    }, { threshold: 0.08, rootMargin: '0px 0px -30px 0px' })
    document.querySelectorAll('.reveal').forEach(el => obs.observe(el))
    // Nav scroll
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
        {/* HERO */}
        <section className="hero">
          <div className="container">
            <div className="hero-grid">
              <div>
                <h1 className="hero-h1">Protecting Those<br/><span className="gradient">Protected Us</span></h1>
                <p className="hero-sub">Intent-Aware Autonomous Guardian against synthetic social engineering. ElderShield intercepts deepfake calls, AI-powered scams, and phishing attacks <strong>before</strong> they reach your elderly loved ones with cryptographic proof of every action.</p>
                <div className="hero-btns">
                  <Link to="/dashboard" className="btn btn-primary">📊 View Live Dashboard</Link>
                  <Link to="/demo" className="btn btn-ghost">▶️ Watch Demo</Link>
                </div>
                <div className="hero-stats">
                  <div><div className="hero-stat-val">700M+</div><div className="hero-stat-lbl">Elderly at Risk</div></div>
                  <div><div className="hero-stat-val">94%</div><div className="hero-stat-lbl">Detection Accuracy</div></div>
                  <div><div className="hero-stat-val">&lt;2s</div><div className="hero-stat-lbl">Interception Latency</div></div>
                </div>
              </div>
              <div className="hero-visual">
                {/* Floating Info Card: Right */}
                <div className="hv-float hv-float-right">
                  <div className="hv-float-head">
                    <span className="hv-float-dot" style={{background:'var(--accent)'}}></span>
                    <span className="hv-float-label">Real-Time Monitoring</span>
                  </div>
                  <div className="hv-float-title">Protection Score</div>
                  <div className="hv-float-big">94.2<span className="hv-float-pct">%</span></div>
                  <div className="hv-float-sub"><span style={{color:'var(--accent)'}}>↑ 2.4%</span> from yesterday</div>
                </div>

                {/* Floating Info Card: Left Bottom */}
                <div className="hv-float hv-float-left">
                  <div className="hv-float-head">
                    <span className="hv-float-dot" style={{background:'var(--red-400)'}}></span>
                    <span className="hv-float-label">Smart Alerts</span>
                  </div>
                  <div className="hv-float-row">
                    <div>
                      <div className="hv-float-mini-lbl">Blocked</div>
                      <div className="hv-float-mini-val" style={{color:'var(--red-400)'}}>17</div>
                    </div>
                    <div style={{width:'1px',height:'28px',background:'rgba(255,255,255,0.06)'}}></div>
                    <div>
                      <div className="hv-float-mini-lbl">Channel</div>
                      <div className="hv-float-mini-val" style={{color:'var(--accent)'}}>WhatsApp</div>
                    </div>
                  </div>
                </div>

                {/* Green Glow Orb */}
                <div className="hv-glow"></div>

                {/* PHONE */}
                <div className="hv-phone">
                  <div className="hv-phone-inner">
                    <div className="hv-island"></div>
                    <div className="hv-statusbar">
                      <span>9:41</span>
                      <span style={{display:'flex',gap:'4px',alignItems:'center'}}>
                        <svg width="14" height="10" viewBox="0 0 14 10" fill="none"><rect x="0" y="4" width="2.5" height="6" rx="0.8" fill="#888"/><rect x="3.5" y="2.5" width="2.5" height="7.5" rx="0.8" fill="#aaa"/><rect x="7" y="1" width="2.5" height="9" rx="0.8" fill="#ccc"/><rect x="10.5" y="0" width="2.5" height="10" rx="0.8" fill="#fff"/></svg>
                        <svg width="20" height="10" viewBox="0 0 20 10" fill="none"><rect x="0.5" y="0.5" width="17" height="9" rx="2" stroke="#666"/><rect x="2" y="2" width="12" height="6" rx="1" fill="var(--accent)"/><rect x="18" y="3" width="2" height="4" rx="0.5" fill="#666"/></svg>
                      </span>
                    </div>

                    <div className="hv-tabs">
                      <div className="hv-tab hv-tab-active">Overview</div>
                      <div className="hv-tab">Threats</div>
                      <div className="hv-tab">Alerts</div>
                    </div>

                    <div className="hv-stat-block">
                      <div className="hv-stat-big">142</div>
                      <div className="hv-stat-arrow">↑</div>
                      <div className="hv-stat-detail">
                        <div className="hv-stat-sub-val" style={{color:'var(--accent)'}}>+12.8%</div>
                        <div className="hv-stat-sub-lbl">Intercepted today</div>
                      </div>
                    </div>

                    <div className="hv-chart-area">
                      <svg viewBox="0 0 280 80" className="hv-chart-svg" preserveAspectRatio="none">
                        <defs>
                          <linearGradient id="heroChartGrad" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="rgba(0,255,136,0.25)"/>
                            <stop offset="100%" stopColor="rgba(0,255,136,0)"/>
                          </linearGradient>
                        </defs>
                        <path d="M0,65 C20,60 30,55 50,48 C70,41 80,50 100,38 C120,26 130,35 150,28 C170,21 180,30 200,18 C220,6 240,22 260,12 L280,8 L280,80 L0,80 Z" fill="url(#heroChartGrad)"/>
                        <path d="M0,65 C20,60 30,55 50,48 C70,41 80,50 100,38 C120,26 130,35 150,28 C170,21 180,30 200,18 C220,6 240,22 260,12 L280,8" fill="none" stroke="#00ff88" strokeWidth="2.5"/>
                        <circle cx="280" cy="8" r="3.5" fill="#00ff88"/>
                        <circle cx="280" cy="8" r="7" fill="rgba(0,255,136,0.2)"/>
                      </svg>
                      <div className="hv-chart-labels">
                        <span>9h</span>
                        <span style={{background:'rgba(0,255,136,0.15)',color:'var(--accent)',padding:'2px 8px',borderRadius:'4px',fontWeight:600}}>1D</span>
                        <span>1W</span><span>1Y</span><span>2Y</span><span>5Y</span><span>ALL</span>
                      </div>
                    </div>

                    <div className="hv-notifs">
                      <div className="hv-notif hv-notif-danger">
                        <div className="hv-notif-icon" style={{background:'rgba(239,68,68,0.15)'}}>🚨</div>
                        <div className="hv-notif-body">
                          <div className="hv-notif-title">Deepfake Voice Blocked</div>
                          <div className="hv-notif-sub">WhatsApp · 2 min ago</div>
                        </div>
                        <div className="hv-notif-badge" style={{background:'rgba(239,68,68,0.15)',color:'var(--red-400)'}}>94%</div>
                      </div>
                      <div className="hv-notif hv-notif-safe">
                        <div className="hv-notif-icon" style={{background:'rgba(16,185,129,0.15)'}}>✅</div>
                        <div className="hv-notif-body">
                          <div className="hv-notif-title">Family Message Delivered</div>
                          <div className="hv-notif-sub">WhatsApp · 5 min ago</div>
                        </div>
                        <div className="hv-notif-badge" style={{background:'rgba(16,185,129,0.15)',color:'var(--green-400)'}}>Safe</div>
                      </div>
                    </div>

                    <div className="hv-home-bar"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* STATS */}
        <section className="container" style={{padding:0}}>
          <div className="stats-row reveal">
            <div className="stat-card"><div className="stat-num" style={{color:'var(--accent)'}}>700M+</div><div className="stat-lbl">Elderly at Risk Globally</div></div>
            <div className="stat-card"><div className="stat-num" style={{color:'var(--red-400)'}}>$3.4B</div><div className="stat-lbl">Annual Scam Losses</div></div>
            <div className="stat-card"><div className="stat-num" style={{color:'var(--amber-400)'}}>900%</div><div className="stat-lbl">Deepfake Growth YoY</div></div>
            <div className="stat-card"><div className="stat-num" style={{color:'var(--text-primary)'}}>3 sec</div><div className="stat-lbl">To Clone Any Voice via AI</div></div>
          </div>
        </section>

        {/* FEATURE HIGHLIGHTS */}
        <section className="highlights">
          <div className="container">
            <div className="section-center reveal">
              <div className="section-tag">⚡ Core Capabilities</div>
              <h2 className="section-title">Six Layers of <span className="gradient">Intelligent Protection</span></h2>
              <p className="section-desc">Real-time interception, intent analysis, and cryptographic governance in a single defense system.</p>
            </div>
            <div className="highlights-grid" style={{display:'grid', gridTemplateColumns:'repeat(3, 1fr)', gap:'20px'}}>
              <div className="highlight-card reveal" style={{background:'#ccff23', color:'#000', border:'1px solid #a3cc1c', boxShadow:'0 10px 30px rgba(0,0,0,0.3)', borderRadius:'24px', padding:'32px 28px'}}>
                <div className="highlight-icon" style={{fontSize:'2.4rem', marginBottom:'16px'}}>🔍</div>
                <h3 className="highlight-title" style={{fontFamily:"'Space Grotesk',sans-serif", fontWeight:900, textTransform:'uppercase', fontSize:'1.3rem', lineHeight:1.1, marginBottom:'12px', color:'#000'}}>Real-Time Interception</h3>
                <p className="highlight-desc" style={{fontSize:'0.9rem', fontWeight:500, color:'#222', lineHeight:1.5}}>Intercepts SMS, WhatsApp, calls, and emails before users see them via the OpenClaw agent.</p>
              </div>
              <div className="highlight-card reveal" style={{background:'#9d50ff', color:'#fff', border:'1px solid #813ed6', boxShadow:'0 10px 30px rgba(0,0,0,0.3)', borderRadius:'24px', padding:'32px 28px'}}>
                <div className="highlight-icon" style={{fontSize:'2.4rem', marginBottom:'16px'}}>🧠</div>
                <h3 className="highlight-title" style={{fontFamily:"'Space Grotesk',sans-serif", fontWeight:900, textTransform:'uppercase', fontSize:'1.3rem', lineHeight:1.1, marginBottom:'12px', color:'#fff'}}>AI Intent Analysis</h3>
                <p className="highlight-desc" style={{fontSize:'0.9rem', fontWeight:500, color:'rgba(255,255,255,0.9)', lineHeight:1.5}}>Dual-LLM tracking: local Gemma 2B for privacy + GPT-4o for edge cases. 94% accuracy.</p>
              </div>
              <div className="highlight-card reveal" style={{background:'#18191a', color:'#fff', border:'1px solid rgba(255,255,255,0.06)', boxShadow:'0 10px 30px rgba(0,0,0,0.3)', borderRadius:'24px', padding:'32px 28px'}}>
                <div className="highlight-icon" style={{fontSize:'2.4rem', marginBottom:'16px'}}>🔐</div>
                <h3 className="highlight-title" style={{fontFamily:"'Space Grotesk',sans-serif", fontWeight:900, textTransform:'uppercase', fontSize:'1.3rem', lineHeight:1.1, marginBottom:'12px', color:'#fff'}}>Cryptographic Assurance</h3>
                <p className="highlight-desc" style={{fontSize:'0.9rem', fontWeight:500, color:'#aaa', lineHeight:1.5}}>HMAC-SHA256 signing per action. Immutable SQLite audit log with tamper-proof setup.</p>
              </div>
              <div className="highlight-card reveal" style={{background:'#18191a', color:'#fff', border:'1px solid #0a4050', boxShadow:'0 10px 30px rgba(0,0,0,0.3)', borderRadius:'24px', padding:'32px 28px'}}>
                <div className="highlight-icon" style={{fontSize:'2.4rem', marginBottom:'16px'}}>👨‍👩‍👧</div>
                <h3 className="highlight-title" style={{fontFamily:"'Space Grotesk',sans-serif", fontWeight:900, textTransform:'uppercase', fontSize:'1.3rem', lineHeight:1.1, marginBottom:'12px', color:'#67e8f9'}}>Family Alerts</h3>
                <p className="highlight-desc" style={{fontSize:'0.9rem', fontWeight:500, color:'#aaa', lineHeight:1.5}}>Real-time WebSocket push notifications to family dashboard with sub-second latency.</p>
              </div>
              <div className="highlight-card reveal" style={{background:'#18191a', color:'#fff', border:'1px solid #fbbf24', boxShadow:'0 10px 30px rgba(0,0,0,0.3)', borderRadius:'24px', padding:'32px 28px'}}>
                <div className="highlight-icon" style={{fontSize:'2.4rem', marginBottom:'16px'}}>🛡️</div>
                <h3 className="highlight-title" style={{fontFamily:"'Space Grotesk',sans-serif", fontWeight:900, textTransform:'uppercase', fontSize:'1.3rem', lineHeight:1.1, marginBottom:'12px', color:'#fbbf24'}}>Injection Defense</h3>
                <p className="highlight-desc" style={{fontSize:'0.9rem', fontWeight:500, color:'#aaa', lineHeight:1.5}}>ArmorClaw detects and quarantines prompt injection attacks. Agent cannot be weaponized.</p>
              </div>
              <div className="highlight-card reveal" style={{background:'#18191a', color:'#fff', border:'1px solid #ff4a4a', boxShadow:'0 10px 30px rgba(0,0,0,0.3)', borderRadius:'24px', padding:'32px 28px'}}>
                <div className="highlight-icon" style={{fontSize:'2.4rem', marginBottom:'16px'}}>👵</div>
                <h3 className="highlight-title" style={{fontFamily:"'Space Grotesk',sans-serif", fontWeight:900, textTransform:'uppercase', fontSize:'1.3rem', lineHeight:1.1, marginBottom:'12px', color:'#ff4a4a'}}>Elder-Friendly</h3>
                <p className="highlight-desc" style={{fontSize:'0.9rem', fontWeight:500, color:'#aaa', lineHeight:1.5}}>Non-alarming, simple explanations. Grandma sees reassurance, not technical jargon.</p>
              </div>
            </div>
            <div style={{textAlign:'center',marginTop:'40px'}} className="reveal">
              <Link to="/features" className="btn btn-primary" style={{marginRight:'12px'}}>Explore All Features →</Link>
              <Link to="/dashboard" className="btn btn-ghost">Open Dashboard →</Link>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="cta">
          <div className="container">
            <div className="cta-box reveal">
              <h2 className="cta-h2">Build <span className="gradient">ElderShield</span>. Win the Claw &amp; Shield Track.</h2>
              <p className="cta-p">700 million elderly people are waiting. ArmorClaw guarantees their protection — cryptographically.</p>
              <div className="cta-btns">
                <Link to="/dashboard" className="btn btn-primary">📊 Open Dashboard</Link>
                <Link to="/demo" className="btn btn-ghost">▶️ Run Demo</Link>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  )
}
