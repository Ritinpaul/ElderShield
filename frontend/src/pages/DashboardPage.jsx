import { useEffect, useRef, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import { THREATS, ATTACKS, rndSig } from '../data/constants'
import '../styles/dashboard.css'

export default function DashboardPage() {
  const canvasRef = useRef(null)
  const feedRef = useRef(null)
  const profileRef = useRef(null)
  const [totalIntercepted, setTotalIntercepted] = useState(142)
  const [feedItems, setFeedItems] = useState([
    { dotClass: 'red', tagClass: 'red', tagText: 'SCAM', via: 'WhatsApp', time: '2 min ago', title: 'Deepfake Voice — Grandparent Scam', confidence: '94.0%', hash: '8f4a2c1b9e3d7f0a' },
    { dotClass: 'red', tagClass: 'red', tagText: 'SCAM', via: 'SMS', time: '8 min ago', title: 'Phishing Link — Bank Impersonation', confidence: '97.0%', hash: 'd4e5f6a7b8c9d0e1' },
    { dotClass: 'red', tagClass: 'red', tagText: '🚨 SCAM', via: 'WhatsApp', time: '14 min ago', title: 'Prompt Injection Attack Detected', confidence: '100.0%', hash: 'a1b2c3d4e5f6a7b8' },
    { dotClass: 'amber', tagClass: 'amber', tagText: 'SUSPICIOUS', via: 'Email', time: '21 min ago', title: 'Unverified Sender — Unusual Request', confidence: '82.5%', hash: 'e9c8b7a6f5d4c3b2' },
  ])

  // Area chart drawing
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const dpr = window.devicePixelRatio || 1

    function resize() {
      const rect = canvas.parentElement.getBoundingClientRect()
      canvas.width = rect.width * dpr
      canvas.height = rect.height * dpr
      canvas.style.width = rect.width + 'px'
      canvas.style.height = rect.height + 'px'
      ctx.setTransform(1, 0, 0, 1, 0, 0)
      ctx.scale(dpr, dpr)
      draw(rect.width, rect.height)
    }

    function draw(w, h) {
      ctx.clearRect(0, 0, w, h)
      const data = [28, 42, 35, 65, 48, 72, 55, 90, 68, 105, 82, 130, 95, 142]
      const max = Math.max(...data) * 1.15
      const stepX = w / (data.length - 1)
      const pad = 4

      ctx.strokeStyle = 'rgba(255,255,255,0.03)'
      ctx.lineWidth = 1
      for (let i = 0; i < 5; i++) {
        const y = pad + (h - pad * 2) * (i / 4)
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(w, y); ctx.stroke()
      }

      ctx.beginPath()
      data.forEach((d, i) => {
        const x = i * stepX
        const y = h - (d / max) * (h - pad * 2) - pad
        if (i === 0) ctx.moveTo(x, y)
        else {
          const px = (i - 1) * stepX, py = h - (data[i-1] / max) * (h - pad * 2) - pad
          const cx = (px + x) / 2
          ctx.bezierCurveTo(cx, py, cx, y, x, y)
        }
      })
      ctx.lineTo(w, h); ctx.lineTo(0, h); ctx.closePath()
      const grad = ctx.createLinearGradient(0, 0, 0, h)
      grad.addColorStop(0, 'rgba(0,255,136,0.3)')
      grad.addColorStop(1, 'rgba(0,255,136,0.01)')
      ctx.fillStyle = grad; ctx.fill()

      ctx.beginPath()
      data.forEach((d, i) => {
        const x = i * stepX
        const y = h - (d / max) * (h - pad * 2) - pad
        if (i === 0) ctx.moveTo(x, y)
        else {
          const px = (i - 1) * stepX, py = h - (data[i-1] / max) * (h - pad * 2) - pad
          const cx = (px + x) / 2
          ctx.bezierCurveTo(cx, py, cx, y, x, y)
        }
      })
      ctx.strokeStyle = '#00ff88'
      ctx.lineWidth = 3
      ctx.shadowColor = 'rgba(0,255,136,0.4)'
      ctx.shadowBlur = 10
      ctx.stroke()
      ctx.shadowBlur = 0

      const lastX = (data.length - 1) * stepX
      const lastY = h - (data[data.length - 1] / max) * (h - pad * 2) - pad
      ctx.beginPath(); ctx.arc(lastX, lastY, 5, 0, Math.PI * 2)
      ctx.fillStyle = '#fff'; ctx.fill()
      ctx.beginPath(); ctx.arc(lastX, lastY, 10, 0, Math.PI * 2)
      ctx.fillStyle = 'rgba(0,255,136,0.3)'; ctx.fill()
    }

    resize()
    window.addEventListener('resize', resize)
    return () => window.removeEventListener('resize', resize)
  }, [])

  // WebSocket connection
  useEffect(() => {
    let ws
    try {
      ws = new WebSocket("ws://127.0.0.1:8000/ws/family-alerts")

      ws.onopen = () => {
        console.log("✅ WebSocket Connected: Listening for ElderShield Intercepts...")
        if (profileRef.current) profileRef.current.style.border = "1px solid var(--accent)"
      }

      ws.onmessage = (event) => {
        const payload = JSON.parse(event.data)
        console.log("🚨 ALERT RECEIVED:", payload)
        const isRed = payload.label === 'SCAM'
        setFeedItems(prev => [{
          dotClass: isRed ? 'red' : 'amber',
          tagClass: isRed ? 'red' : 'amber',
          tagText: payload.label,
          via: `${payload.channel} (LIVE)`,
          time: 'Just now',
          title: payload.reason || 'Threat Detected',
          confidence: `${(payload.confidence * 100).toFixed(1)}%`,
          hash: payload.signature || 'pending...',
          isLive: true,
        }, ...prev])
        setTotalIntercepted(prev => prev + 1)
      }

      ws.onclose = () => {
        console.log("❌ WebSocket Disconnected")
        if (profileRef.current) profileRef.current.style.border = "1px solid red"
      }
    } catch (e) {
      console.log("WebSocket not available")
    }

    return () => { if (ws) ws.close() }
  }, [])

  const simulateNewThreat = useCallback(async () => {
    console.log("Simulating threat...")
    const payload = {
      channel: "whatsapp",
      sender: "+1234567890",
      content: "Grandma im in jail, please send money! Don't tell anyone.",
    }
    try {
      const res = await fetch("http://127.0.0.1:8000/api/intercept", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
      if (res.ok) {
        console.log("✅ Threat injected to L1 layer successfully")
      } else {
        console.error("❌ Failed to inject threat", await res.text())
      }
    } catch (err) {
      console.error("❌ API Offline - Could not reach /api/intercept", err)
      alert("Server is offline. Start FastAPI backend on port 8000.")
    }
  }, [])

  return (
    <div className="dashboard-page">
      <Sidebar />
      <main className="main-wrap">
        {/* Header */}
        <header className="header">
          <div className="search-bar">
            <span>🔍</span> Search threats, messages...
            <span className="search-cmd">⌘ + Space</span>
          </div>
          <div className="header-right">
            <span className="h-icon" title="Notifications">🔔</span>
            <span className="h-icon" title="Settings">⚙️</span>
            <div className="h-profile" ref={profileRef}>
              <div className="hp-avatar">ES</div>
              <div className="hp-info">
                <span className="hp-name">ElderShield</span>
                <span className="hp-role">@guardian</span>
              </div>
              <span className="h-icon" style={{fontSize:'0.8rem'}}>▼</span>
            </div>
          </div>
        </header>

        {/* Grid Area */}
        <div className="db-content">
          {/* 1. Threats Area Chart */}
          <div className="card card-chartmain">
            <div className="cm-header">
              <div>
                <div className="cm-title">Total Threats Intercepted</div>
                <div className="cm-val-row">
                  <div className="cm-val">1,247</div>
                  <div className="cm-pct">↑ 12.8% <span style={{fontWeight:400,color:'#666'}}>from last month</span></div>
                </div>
              </div>
              <div className="cm-filters">
                <span className="cm-filter">1 year</span>
                <span className="cm-filter active">6 month</span>
                <span className="cm-filter">3 month</span>
                <span className="cm-filter">1 month</span>
              </div>
            </div>
            <div className="chart-area">
              <canvas ref={canvasRef} className="chart-canvas"></canvas>
              <div className="chart-tooltip">
                <div className="chart-tooltip-date">02 Apr, 2026 ↗</div>
                <div className="chart-tooltip-val">142 threats</div>
              </div>
            </div>
            <div className="cm-footer">
              <div>Average daily rate: <strong style={{color:'#aaa'}}>7.2 threats/day</strong></div>
              <div className="cm-legend">
                <div className="cm-leg-item"><div className="c-dot" style={{background:'#444'}}></div> Intercepted</div>
                <div className="cm-leg-item"><div className="c-dot" style={{background:'var(--accent)'}}></div> Blocked</div>
              </div>
            </div>
          </div>

          {/* 2. Protection Status */}
          <div className="card card-protect">
            <div className="cp-top">
              <span className="card-title-sm" style={{margin:0}}>Protection Status</span>
              <span style={{fontSize:'1.2rem'}}>🛡️</span>
            </div>
            <div className="cp-shield-visual">
              <span className="cp-shield-emoji">🛡️</span>
            </div>
            <div className="cp-score-row">
              <div className="cp-score">94</div>
              <div className="cp-score-label">Protection Score</div>
            </div>
            <div className="cp-actions">
              <button className="cp-btn ghost">📋 Audit Log</button>
              <button className="cp-btn primary" onClick={simulateNewThreat}>⚡ Intercept</button>
            </div>
          </div>

          {/* 3. Trusted Promo Banner */}
          <div className="card card-promo">
            <div className="promo-rings"></div>
            <div className="promo-content">
              <h2 className="promo-title" style={{fontSize:'1.4rem', marginBottom:'8px'}}>Trusted by Families<br/>Worldwide</h2>
              <p className="promo-desc" style={{marginBottom:'12px'}}>Secure, reliable, and cryptographically guaranteed protection.</p>
              <ul style={{listStyle:'none', padding:0, margin:'12px 0 20px', display:'flex', flexDirection:'column', gap:'8px'}}>
                <li style={{display:'flex', alignItems:'center', gap:'8px', fontSize:'0.8rem', color:'#aaa', fontWeight:500}}>
                  <span style={{background:'rgba(0,255,136,0.1)', color:'var(--accent)', width:'18px', height:'18px', borderRadius:'50%', display:'flex', alignItems:'center', justifyContent:'center', fontSize:'0.55rem'}}>✓</span>
                  24/7 Deepfake Interception
                </li>
                <li style={{display:'flex', alignItems:'center', gap:'8px', fontSize:'0.8rem', color:'#aaa', fontWeight:500}}>
                  <span style={{background:'rgba(0,255,136,0.1)', color:'var(--accent)', width:'18px', height:'18px', borderRadius:'50%', display:'flex', alignItems:'center', justifyContent:'center', fontSize:'0.55rem'}}>✓</span>
                  Cryptographic Audit Logging
                </li>
                <li style={{display:'flex', alignItems:'center', gap:'8px', fontSize:'0.8rem', color:'#aaa', fontWeight:500}}>
                  <span style={{background:'rgba(0,255,136,0.1)', color:'var(--accent)', width:'18px', height:'18px', borderRadius:'50%', display:'flex', alignItems:'center', justifyContent:'center', fontSize:'0.55rem'}}>✓</span>
                  Sub-second Family Alerts
                </li>
              </ul>
              <div className="promo-avs" style={{marginBottom:'16px'}}>
                <div className="p-av" style={{background:'var(--accent)', color:'#000'}}>A</div>
                <div className="p-av" style={{background:'#4ade80', color:'#000'}}>B</div>
                <div className="p-av" style={{background:'#22c55e', color:'#000'}}>C</div>
                <div className="p-av" style={{background:'rgba(255,255,255,0.15)', color:'#ccc'}}>+5</div>
              </div>
              <Link to="/demo" className="promo-btn" style={{textDecoration:'none', display:'inline-block', padding:'10px 20px', fontSize:'0.9rem'}}>Run Demo</Link>
            </div>
          </div>

          {/* 4. Threat Distribution */}
          <div className="card card-bars">
            <div className="bc-header">
              <div>
                <div className="card-title-sm" style={{margin:0}}>Threat Distribution</div>
                <div className="bc-val">{totalIntercepted} <span className="bc-pct">↑ 8.3%</span></div>
              </div>
              <div className="bc-ctrl">
                <span className="bc-select">Sort ↕</span>
                <span className="bc-select">Week ⋁</span>
              </div>
            </div>
            <div className="bar-chart">
              <div className="bar-col-g"><span className="bc-amt">18</span><div className="b-fill" style={{height:'45%'}}></div><span className="bc-m">Mon</span></div>
              <div className="bar-col-g"><span className="bc-amt">24</span><div className="b-fill" style={{height:'60%'}}></div><span className="bc-m">Tue</span></div>
              <div className="bar-col-g"><span className="bc-amt">19</span><div className="b-fill b-warning" style={{height:'48%'}}></div><span className="bc-m">Wed</span></div>
              <div className="bar-col-g">
                <span className="bc-amt" style={{color:'var(--accent)'}}>31</span>
                <div className="b-fill b-hl" style={{height:'78%'}}></div>
                <span className="bc-m">Thu</span>
              </div>
              <div className="bar-col-g"><span className="bc-amt">22</span><div className="b-fill" style={{height:'55%'}}></div><span className="bc-m">Fri</span></div>
              <div className="bar-col-g"><span className="bc-amt">16</span><div className="b-fill b-danger" style={{height:'40%'}}></div><span className="bc-m">Sat</span></div>
            </div>
          </div>

          {/* 5. Recent Threats */}
          <div className="card card-feed">
            <div className="cf-header">
              <div className="card-title-sm" style={{margin:0}}>Recent Threats</div>
              <Link to="/audit" className="rc-view">View All</Link>
            </div>
            <div className="cf-body" ref={feedRef}>
              {feedItems.map((item, idx) => (
                <div key={idx} className="feed-item" style={item.isLive ? {animation:'slideIn 0.4s ease', background:'rgba(0,255,136,0.05)', borderLeft:'3px solid var(--accent)', paddingLeft:'12px', borderRadius:'4px'} : {}}>
                  <div className="fi-top">
                    <div className="fi-badges">
                      <div className={`fi-dot ${item.dotClass}`}></div>
                      <div className={`fi-tag ${item.tagClass}`}>{item.tagText}</div>
                      <div className="fi-via">via {item.via}</div>
                    </div>
                    <div className="fi-time">{item.time}</div>
                  </div>
                  <div className="fi-title">{item.title}</div>
                  <div className="fi-btm">
                    <div className="fi-meta">Confidence:<br/><span className="fi-val">{item.confidence}</span></div>
                    <div className="fi-hash">🔐 {item.hash}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
