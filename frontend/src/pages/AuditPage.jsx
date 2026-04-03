import { useEffect, useMemo, useState } from 'react'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import GlowBackground from '../components/GlowBackground'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

function buildApiUrl(path) {
  return `${API_BASE_URL}${path}`
}

function reasonLabel(reason) {
  return (reason || 'unknown signal').replace(/_/g, ' ')
}

function sigShort(signature) {
  return `${(signature || '').slice(0, 14)}...`
}

export default function AuditPage() {
  const [audits, setAudits] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    const obs = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) entry.target.classList.add('visible')
      })
    }, { threshold: 0.08, rootMargin: '0px 0px -30px 0px' })

    document.querySelectorAll('.reveal').forEach((el) => obs.observe(el))

    const nav = document.getElementById('navbar')
    const onScroll = () => nav && nav.classList.toggle('scrolled', window.scrollY > 50)
    window.addEventListener('scroll', onScroll)

    return () => {
      obs.disconnect()
      window.removeEventListener('scroll', onScroll)
    }
  }, [])

  useEffect(() => {
    let active = true

    async function loadAudits() {
      try {
        const res = await fetch(buildApiUrl('/api/audit-log?limit=100'))
        if (!res.ok) {
          throw new Error('Unable to load audit data')
        }

        const payload = await res.json()
        if (active) {
          setAudits(payload)
          setError('')
        }
      } catch (loadErr) {
        if (active) {
          setError(loadErr.message || 'Unable to load audit data')
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    loadAudits()
    const interval = setInterval(loadAudits, 15000)

    return () => {
      active = false
      clearInterval(interval)
    }
  }, [])

  const injectionCount = useMemo(
    () => audits.filter((entry) => Boolean(entry.injection_detected)).length,
    [audits],
  )

  return (
    <>
      <GlowBackground />
      <Navbar />
      <main className="page">
        <div className="container">
          <div className="page-header">
            <div className="page-header-row">
              <div>
                <h1 className="page-title">🔐 Cryptographic <span className="accent">Audit Log</span></h1>
                <p className="page-desc">Every action. Every decision. Signed with HMAC-SHA256. SQLite immutable triggers prevent modification or deletion.</p>
              </div>
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                <span className="badge badge-live"><span className="pulse-dot"></span> Immutable</span>
                <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>{audits.length} entries</span>
              </div>
            </div>
          </div>

          {error && (
            <div className="card" style={{ marginBottom: '18px', borderColor: 'rgba(239,68,68,0.35)' }}>
              <div className="card-body" style={{ color: 'var(--red-400)', fontWeight: 600 }}>{error}</div>
            </div>
          )}

          <div className="card reveal">
            <div className="card-header">
              <div className="card-title">📋 Audit Log — Append Only</div>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>UPDATE/DELETE operations blocked by SQLite triggers</span>
            </div>
            <div className="audit-wrap">
              <table className="audit-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Message ID</th>
                    <th>Action</th>
                    <th>Confidence</th>
                    <th>Reason</th>
                    <th>HMAC Signature</th>
                    <th>Injection</th>
                    <th>Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  {!loading && audits.length === 0 && (
                    <tr>
                      <td colSpan={8} style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '22px' }}>
                        No audit entries yet. Run an intercept to populate immutable logs.
                      </td>
                    </tr>
                  )}
                  {audits.map((entry) => {
                    const action = entry.action
                    const cls = action === 'quarantine' ? 'quarantine' : action === 'hold_for_review' ? 'hold' : 'deliver'
                    const label = action === 'quarantine' ? '🚫 QUARANTINE' : action === 'hold_for_review' ? '⏸ HOLD' : '✅ DELIVER'
                    const hasInjection = Boolean(entry.injection_detected)
                    const ts = new Date(entry.timestamp).toLocaleString('en-IN', { hour12: false })

                    return (
                      <tr key={`${entry.id}-${entry.message_id}`}>
                        <td style={{ color: 'var(--text-muted)', fontWeight: 600 }}>#{entry.id}</td>
                        <td><code style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--accent)' }}>{entry.message_id}</code></td>
                        <td><span className={`audit-action ${cls}`}>{label}</span></td>
                        <td style={{ fontWeight: 600 }}>{(Number(entry.confidence || 0) * 100).toFixed(1)}%</td>
                        <td style={{ color: 'var(--text-secondary)' }}>{reasonLabel(entry.reason)}</td>
                        <td><span className="audit-sig">{sigShort(entry.signature)}</span></td>
                        <td><span className={`audit-inj ${hasInjection ? 'yes' : 'no'}`}>{hasInjection ? '🚨 YES' : '✅ Clean'}</span></td>
                        <td style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{ts}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '22px', paddingTop: '32px' }} className="reveal">
            <div className="card" style={{ borderColor: 'rgba(0,255,136,0.12)' }}>
              <div className="card-body">
                <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '12px', color: 'var(--accent)' }}>🔐 How Signatures Work</h3>
                <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: '12px' }}>Each audit entry is signed using HMAC-SHA256 with the ArmorClaw secret key. The payload includes message ID, action, confidence, reason, and timestamp. Any tampering invalidates the signature instantly.</p>
                <code style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--green-400)', display: 'block', padding: '12px', background: 'rgba(0,0,0,0.3)', borderRadius: '8px', wordBreak: 'break-all' }}>{'HMAC-SHA256(key, JSON.stringify({message_id, action, confidence, reason, timestamp}))'}</code>
              </div>
            </div>
            <div className="card" style={{ borderColor: 'rgba(239,68,68,0.12)' }}>
              <div className="card-body">
                <h3 style={{ fontSize: '1rem', fontWeight: 700, marginBottom: '12px', color: 'var(--red-400)' }}>🚨 Immutability Guarantee</h3>
                <p style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: '12px' }}>SQLite triggers prevent any UPDATE or DELETE operations on the audit table. Once an entry is written, it exists permanently. Prompt injection detections seen in this view: <strong style={{ color: 'var(--text-primary)' }}>{injectionCount}</strong>.</p>
                <code style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--red-400)', display: 'block', padding: '12px', background: 'rgba(0,0,0,0.3)', borderRadius: '8px' }}>CREATE TRIGGER prevent_audit_update<br />BEFORE UPDATE ON audit_log<br />BEGIN SELECT RAISE(ABORT, 'ArmorClaw: audit log is immutable'); END</code>
              </div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </>
  )
}
