import { Link } from 'react-router-dom'

export default function Footer({ mid = "Ossome Hacks 3.0 · Claw & Shield Track · ArmorIQ" }) {
  return (
    <footer className="footer">
      <div className="container footer-inner">
        <div className="footer-brand">🛡️ ElderShield</div>
        {mid && <div className="footer-mid">{mid}</div>}
        <ul className="footer-links">
          <li><Link to="/">Home</Link></li>
          <li><Link to="/features">Features</Link></li>
          <li><Link to="/architecture">Architecture</Link></li>
          <li><Link to="/dashboard">Dashboard</Link></li>
          <li><Link to="/demo">Demo</Link></li>
        </ul>
      </div>
    </footer>
  )
}
