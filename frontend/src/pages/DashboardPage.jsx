import { useEffect, useRef, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import '../styles/dashboard.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

const emptyStats = {
  total_intercepted: 0,
  total_blocked: 0,
  total_suspicious: 0,
  total_safe: 0,
  injection_attempts: 0,
  avg_confidence: 0,
}

function buildApiUrl(path) {
  return `${API_BASE_URL}${path}`
}

function buildWebSocketUrl(path) {
  if (API_BASE_URL) {
    const normalized = API_BASE_URL.replace(/\/$/, '')
    if (normalized.startsWith('https://')) {
      return normalized.replace('https://', 'wss://') + path
    }
    if (normalized.startsWith('http://')) {
      return normalized.replace('http://', 'ws://') + path
    }
  }

  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
  return `${protocol}://${window.location.host}${path}`
}

function formatReason(reason) {
  return (reason || 'unknown risk signal').replace(/_/g, ' ')
}

function shortSig(signature) {
  return (signature || 'pending').slice(0, 16)
}

function actionToFeed(action) {
  if (action === 'quarantine') {
    return { dotClass: 'red', tagClass: 'red', tagText: 'SCAM' }
  }
  if (action === 'hold_for_review') {
    return { dotClass: 'amber', tagClass: 'amber', tagText: 'SUSPICIOUS' }
  }
  return { dotClass: 'green', tagClass: 'green', tagText: 'BENIGN' }
}

function formatTimeAgo(timestamp) {
  const time = new Date(timestamp).getTime()
  if (!Number.isFinite(time)) return 'just now'

  const diffMs = Date.now() - time
  const minutes = Math.max(1, Math.floor(diffMs / 60000))
  if (minutes < 60) return `${minutes} min ago`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} hr ago`

  const days = Math.floor(hours / 24)
  return `${days} day${days > 1 ? 's' : ''} ago`
}

function toFeedItems(audits) {
  return audits.slice(0, 8).map((entry) => {
    const tag = actionToFeed(entry.action)
    const channel = entry.source_channel ? entry.source_channel.toUpperCase() : 'UNKNOWN'
    return {
      dotClass: tag.dotClass,
      tagClass: tag.tagClass,
      tagText: tag.tagText,
      via: channel,
      time: formatTimeAgo(entry.timestamp),
      title: formatReason(entry.reason),
      confidence: `${(Number(entry.confidence || 0) * 100).toFixed(1)}%`,
      hash: shortSig(entry.signature),
      isLive: false,
    }
  })
}

function buildTrendSeries(audits, totalIntercepted) {
  if (!audits.length) return [0, 0, 0, 0, 0, 0]

  const points = audits.slice(0, 14).reverse()
  const baseline = Math.max(0, totalIntercepted - points.length)
  return points.map((_, index) => baseline + index + 1)
}

function computeProtectionScore(stats) {
  const total = stats.total_intercepted || 0
  if (!total) return 100

  const detectionRate = (stats.total_blocked + stats.total_suspicious) / total
  const confidence = Number(stats.avg_confidence || 0)
  const raw = 60 + detectionRate * 35 + confidence * 5
  return Math.max(0, Math.min(99, Math.round(raw)))
}

export default function DashboardPage() {
  const canvasRef = useRef(null)
  const profileRef = useRef(null)

  const [stats, setStats] = useState(emptyStats)
  const [feedItems, setFeedItems] = useState([])
  const [chartSeries, setChartSeries] = useState([0, 0, 0, 0, 0, 0])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState('')

  const totalIntercepted = stats.total_intercepted || 0
  const blockedPct = totalIntercepted
    ? ((stats.total_blocked / totalIntercepted) * 100).toFixed(1)
    : '0.0'
  const protectionScore = computeProtectionScore(stats)

  const distribution = [
    { key: 'Blocked', value: stats.total_blocked || 0, className: 'b-hl' },
    { key: 'Suspicious', value: stats.total_suspicious || 0, className: 'b-warning' },
    { key: 'Delivered', value: stats.total_safe || 0, className: '' },
    { key: 'Injection', value: stats.injection_attempts || 0, className: 'b-danger' },
  ]
  const maxDistValue = Math.max(1, ...distribution.map((item) => item.value))

  const loadDashboardData = useCallback(async () => {
    try {
      const [statsRes, auditsRes] = await Promise.all([
        fetch(buildApiUrl('/api/stats')),
        fetch(buildApiUrl('/api/audit-log?limit=80')),
      ])

      if (!statsRes.ok || !auditsRes.ok) {
        throw new Error('Unable to load dashboard data')
      }

      const statsPayload = await statsRes.json()
      const auditPayload = await auditsRes.json()

      const normalizedStats = {
        ...emptyStats,
        ...statsPayload,
      }

      setStats(normalizedStats)
      setFeedItems(toFeedItems(auditPayload))
      setChartSeries(buildTrendSeries(auditPayload, normalizedStats.total_intercepted || 0))
      setLoadError('')
    } catch (error) {
      setLoadError(error.message || 'Unable to load data')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadDashboardData()
    const interval = setInterval(loadDashboardData, 15000)
    return () => clearInterval(interval)
  }, [loadDashboardData])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    const dpr = window.devicePixelRatio || 1

    function resize() {
      const rect = canvas.parentElement.getBoundingClientRect()
      canvas.width = rect.width * dpr
      canvas.height = rect.height * dpr
      canvas.style.width = `${rect.width}px`
      canvas.style.height = `${rect.height}px`
      ctx.setTransform(1, 0, 0, 1, 0, 0)
      ctx.scale(dpr, dpr)
      draw(rect.width, rect.height)
    }

    function draw(w, h) {
      const data = chartSeries
      ctx.clearRect(0, 0, w, h)

      const max = Math.max(...data) * 1.15
      const stepX = w / Math.max(1, data.length - 1)
      const pad = 4

      ctx.strokeStyle = 'rgba(255,255,255,0.03)'
      ctx.lineWidth = 1
      for (let i = 0; i < 5; i += 1) {
        const y = pad + (h - pad * 2) * (i / 4)
        ctx.beginPath()
        ctx.moveTo(0, y)
        ctx.lineTo(w, y)
        ctx.stroke()
      }

      ctx.beginPath()
      data.forEach((d, i) => {
        const x = i * stepX
        const y = h - (d / max) * (h - pad * 2) - pad
        if (i === 0) {
          ctx.moveTo(x, y)
        } else {
          const px = (i - 1) * stepX
          const py = h - (data[i - 1] / max) * (h - pad * 2) - pad
          const cx = (px + x) / 2
          ctx.bezierCurveTo(cx, py, cx, y, x, y)
        }
      })
      ctx.lineTo(w, h)
      ctx.lineTo(0, h)
      ctx.closePath()

      const grad = ctx.createLinearGradient(0, 0, 0, h)
      grad.addColorStop(0, 'rgba(0,255,136,0.3)')
      grad.addColorStop(1, 'rgba(0,255,136,0.01)')
      ctx.fillStyle = grad
      ctx.fill()

      ctx.beginPath()
      data.forEach((d, i) => {
        const x = i * stepX
        const y = h - (d / max) * (h - pad * 2) - pad
        if (i === 0) {
          ctx.moveTo(x, y)
        } else {
          const px = (i - 1) * stepX
          const py = h - (data[i - 1] / max) * (h - pad * 2) - pad
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
      ctx.beginPath()
      ctx.arc(lastX, lastY, 5, 0, Math.PI * 2)
      ctx.fillStyle = '#fff'
      ctx.fill()
      ctx.beginPath()
      ctx.arc(lastX, lastY, 10, 0, Math.PI * 2)
      ctx.fillStyle = 'rgba(0,255,136,0.3)'
      ctx.fill()
    }

    resize()
    window.addEventListener('resize', resize)
    return () => window.removeEventListener('resize', resize)
  }, [chartSeries])

  useEffect(() => {
    let ws

    try {
      ws = new WebSocket(buildWebSocketUrl('/ws/family-alerts'))

      ws.onopen = () => {
        if (profileRef.current) profileRef.current.style.border = '1px solid var(--accent)'
      }

      ws.onmessage = (event) => {
        const payload = JSON.parse(event.data)
        const isRed = payload.action === 'quarantine'
        const isAmber = payload.action === 'hold_for_review'

        setFeedItems((prev) => [
          {
            dotClass: isRed ? 'red' : isAmber ? 'amber' : 'green',
            tagClass: isRed ? 'red' : isAmber ? 'amber' : 'green',
            tagText: isRed ? 'SCAM' : isAmber ? 'SUSPICIOUS' : 'BENIGN',
            via: `${payload.channel || 'policy'} (LIVE)`,
            time: 'Just now',
            title: formatReason(payload.reason),
            confidence: `${(Number(payload.confidence || 0) * 100).toFixed(1)}%`,
            hash: shortSig(payload.signature),
            isLive: true,
          },
          ...prev,
        ].slice(0, 8))

        setStats((prev) => ({
          ...prev,
          total_intercepted: (prev.total_intercepted || 0) + 1,
          total_blocked: isRed ? (prev.total_blocked || 0) + 1 : (prev.total_blocked || 0),
          total_suspicious: isAmber ? (prev.total_suspicious || 0) + 1 : (prev.total_suspicious || 0),
          total_safe: !isRed && !isAmber ? (prev.total_safe || 0) + 1 : (prev.total_safe || 0),
        }))
      }

      ws.onclose = () => {
        if (profileRef.current) profileRef.current.style.border = '1px solid red'
      }
    } catch {
      // noop
    }

    return () => {
      if (ws) ws.close()
    }
  }, [])

  const simulateNewThreat = useCallback(async () => {
    const payload = {
      channel: 'whatsapp',
      sender: '+1234567890',
      content: "Grandma I'm in jail, please send money! Don't tell anyone.",
    }

    try {
      const res = await fetch(buildApiUrl('/api/intercept'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (!res.ok) {
        throw new Error('Threat injection failed')
      }
    } catch {
      alert('Server is offline. Start FastAPI backend on port 8000.')
    }
  }, [])

  return (
    <div className="dashboard-page">
      <Sidebar />
      <main className="main-wrap">
        {loadError && <div className="dashboard-error">{loadError}</div>}

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
              <span className="h-icon" style={{ fontSize: '0.8rem' }}>▼</span>
            </div>
          </div>
        </header>

        <div className="db-content">
          <div className="card card-chartmain">
            <div className="cm-header">
              <div>
                <div className="cm-title">Total Threats Intercepted</div>
                <div className="cm-val-row">
                  <div className="cm-val">{totalIntercepted.toLocaleString()}</div>
                  <div className="cm-pct">{blockedPct}% blocked <span style={{ fontWeight: 400, color: '#666' }}>from all intercepted</span></div>
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
                <div className="chart-tooltip-date">Realtime Trend</div>
                <div className="chart-tooltip-val">{totalIntercepted} threats</div>
              </div>
            </div>
            <div className="cm-footer">
              <div>Average confidence: <strong style={{ color: '#aaa' }}>{(Number(stats.avg_confidence || 0) * 100).toFixed(1)}%</strong></div>
              <div className="cm-legend">
                <div className="cm-leg-item"><div className="c-dot" style={{ background: '#444' }}></div> Intercepted</div>
                <div className="cm-leg-item"><div className="c-dot" style={{ background: 'var(--accent)' }}></div> Blocked</div>
              </div>
            </div>
          </div>

          <div className="card card-protect">
            <div className="cp-top">
              <span className="card-title-sm" style={{ margin: 0 }}>Protection Status</span>
              <span style={{ fontSize: '1.2rem' }}>🛡️</span>
            </div>
            <div className="cp-shield-visual">
              <span className="cp-shield-emoji">🛡️</span>
            </div>
            <div className="cp-score-row">
              <div className="cp-score">{protectionScore}</div>
              <div className="cp-score-label">Protection Score</div>
            </div>
            <div className="cp-actions">
              <Link to="/audit" className="cp-btn ghost" style={{ textAlign: 'center', textDecoration: 'none' }}>📋 Audit Log</Link>
              <button className="cp-btn primary" onClick={simulateNewThreat}>⚡ Intercept</button>
            </div>
          </div>

          <div className="card card-promo">
            <div className="promo-rings"></div>
            <div className="promo-content">
              <h2 className="promo-title" style={{ fontSize: '1.4rem', marginBottom: '8px' }}>Trusted by Families<br />Worldwide</h2>
              <p className="promo-desc" style={{ marginBottom: '12px' }}>Secure, reliable, and cryptographically guaranteed protection.</p>
              <ul style={{ listStyle: 'none', padding: 0, margin: '12px 0 20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <li style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: '#aaa', fontWeight: 500 }}>
                  <span style={{ background: 'rgba(0,255,136,0.1)', color: 'var(--accent)', width: '18px', height: '18px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.55rem' }}>✓</span>
                  24/7 Deepfake Interception
                </li>
                <li style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: '#aaa', fontWeight: 500 }}>
                  <span style={{ background: 'rgba(0,255,136,0.1)', color: 'var(--accent)', width: '18px', height: '18px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.55rem' }}>✓</span>
                  Cryptographic Audit Logging
                </li>
                <li style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: '#aaa', fontWeight: 500 }}>
                  <span style={{ background: 'rgba(0,255,136,0.1)', color: 'var(--accent)', width: '18px', height: '18px', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.55rem' }}>✓</span>
                  Sub-second Family Alerts
                </li>
              </ul>
              <Link to="/demo" className="promo-btn" style={{ textDecoration: 'none', display: 'inline-block', padding: '10px 20px', fontSize: '0.9rem' }}>Run Demo</Link>
            </div>
          </div>

          <div className="card card-bars">
            <div className="bc-header">
              <div>
                <div className="card-title-sm" style={{ margin: 0 }}>Threat Distribution</div>
                <div className="bc-val">{totalIntercepted} <span className="bc-pct">live</span></div>
              </div>
              <div className="bc-ctrl">
                <span className="bc-select">DB Source</span>
                <span className="bc-select">Audit</span>
              </div>
            </div>
            <div className="bar-chart">
              {distribution.map((item) => (
                <div key={item.key} className="bar-col-g">
                  <span className="bc-amt">{item.value}</span>
                  <div
                    className={`b-fill ${item.className}`}
                    style={{ height: `${Math.max(4, (item.value / maxDistValue) * 100)}%` }}
                  ></div>
                  <span className="bc-m">{item.key}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="card card-feed">
            <div className="cf-header">
              <div className="card-title-sm" style={{ margin: 0 }}>Recent Threats</div>
              <Link to="/audit" className="rc-view">View All</Link>
            </div>
            <div className="cf-body">
              {!loading && feedItems.length === 0 && (
                <div className="feed-empty">No audit data yet. Trigger an intercept to start recording events.</div>
              )}
              {feedItems.map((item, idx) => (
                <div key={`${item.hash}-${idx}`} className="feed-item" style={item.isLive ? { animation: 'slideIn 0.4s ease', background: 'rgba(0,255,136,0.05)', borderLeft: '3px solid var(--accent)', paddingLeft: '12px', borderRadius: '4px' } : {}}>
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
                    <div className="fi-meta">Confidence:<br /><span className="fi-val">{item.confidence}</span></div>
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
