import { useEffect } from 'react'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import GlowBackground from '../components/GlowBackground'
import { AUDITS } from '../data/constants'

export default function AuditPage() {
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
          <div className="page-header">
            <div className="page-header-row">
              <div>
                <h1 className="page-title">🔐 Cryptographic <span className="accent">Audit Log</span></h1>
                <p className="page-desc">Every action. Every decision. Signed with HMAC-SHA256. SQLite immutable triggers prevent modification or deletion.</p>
              </div>
              <div style={{display:'flex',gap:'10px',alignItems:'center'}}>
                <span className="badge badge-live"><span className="pulse-dot"></span> Immutable</span>
                <span style={{fontSize:'0.76rem',color:'var(--text-muted)'}}>{AUDITS.length} entries</span>
              </div>
            </div>
          </div>

          <div className="card reveal">
            <div className="card-header">
              <div className="card-title">📋 Audit Log — Append Only</div>
              <span style={{fontSize:'0.72rem',color:'var(--text-muted)'}}>UPDATE/DELETE operations blocked by SQLite triggers</span>
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
                  {AUDITS.map(a => {
                    const cls = a.act === "quarantine" ? "quarantine" : a.act === "hold" ? "hold" : "deliver"
                    const lbl = a.act === "quarantine" ? "🚫 QUARANTINE" : a.act === "hold" ? "⏸ HOLD" : "✅ DELIVER"
                    const ic = a.inj ? "yes" : "no"
                    const il = a.inj ? "🚨 YES" : "✅ Clean"
                    const ts = new Date(a.ts).toLocaleString("en-IN", { hour12: false })
                    return (
                      <tr key={a.id}>
                        <td style={{color:'var(--text-muted)',fontWeight:600}}>#{a.id}</td>
                        <td><code style={{fontFamily:'var(--font-mono)',fontSize:'0.72rem',color:'var(--accent)'}}>{a.mid}</code></td>
                        <td><span className={`audit-action ${cls}`}>{lbl}</span></td>
                        <td style={{fontWeight:600}}>{(a.conf*100).toFixed(1)}%</td>
                        <td style={{color:'var(--text-secondary)'}}>{a.reason.replace(/_/g," ")}</td>
                        <td><span className="audit-sig">{a.sig}...</span></td>
                        <td><span className={`audit-inj ${ic}`}>{il}</span></td>
                        <td style={{fontSize:'0.72rem',color:'var(--text-muted)'}}>{ts}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>

          {/* Signature Info */}
          <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'22px',paddingTop:'32px'}} className="reveal">
            <div className="card" style={{borderColor:'rgba(0,255,136,0.12)'}}>
              <div className="card-body">
                <h3 style={{fontSize:'1rem',fontWeight:700,marginBottom:'12px',color:'var(--accent)'}}>🔐 How Signatures Work</h3>
                <p style={{fontSize:'0.84rem',color:'var(--text-secondary)',lineHeight:1.7,marginBottom:'12px'}}>Each audit entry is signed using HMAC-SHA256 with the ArmorClaw secret key. The payload includes message ID, action, confidence, reason, and timestamp — making it impossible to alter any field without invalidating the signature.</p>
                <code style={{fontFamily:'var(--font-mono)',fontSize:'0.72rem',color:'var(--green-400)',display:'block',padding:'12px',background:'rgba(0,0,0,0.3)',borderRadius:'8px',wordBreak:'break-all'}}>{'HMAC-SHA256(key, JSON.stringify({message_id, action, confidence, reason, timestamp}))'}</code>
              </div>
            </div>
            <div className="card" style={{borderColor:'rgba(239,68,68,0.12)'}}>
              <div className="card-body">
                <h3 style={{fontSize:'1rem',fontWeight:700,marginBottom:'12px',color:'var(--red-400)'}}>🚨 Immutability Guarantee</h3>
                <p style={{fontSize:'0.84rem',color:'var(--text-secondary)',lineHeight:1.7,marginBottom:'12px'}}>SQLite triggers prevent any UPDATE or DELETE operations on the audit table. Once an entry is written, it exists permanently — providing complete accountability.</p>
                <code style={{fontFamily:'var(--font-mono)',fontSize:'0.72rem',color:'var(--red-400)',display:'block',padding:'12px',background:'rgba(0,0,0,0.3)',borderRadius:'8px'}}>CREATE TRIGGER prevent_audit_update<br/>BEFORE UPDATE ON audit_log<br/>BEGIN SELECT RAISE(ABORT, 'ArmorClaw: audit log is immutable'); END</code>
              </div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </>
  )
}
