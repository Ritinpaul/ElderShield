import { NavLink } from 'react-router-dom'

export default function Navbar() {
  return (
    <nav className="nav" id="navbar">
      <div className="container nav-inner">
        <NavLink to="/" className="nav-logo">
          <span className="nav-logo-icon">🛡️</span> ElderShield
        </NavLink>
        <ul className="nav-links">
          <li><NavLink to="/" className={({isActive}) => isActive ? 'active' : ''} end>Home</NavLink></li>
          <li><NavLink to="/features" className={({isActive}) => isActive ? 'active' : ''}>Features</NavLink></li>
          <li><NavLink to="/architecture" className={({isActive}) => isActive ? 'active' : ''}>Architecture</NavLink></li>
          <li><NavLink to="/dashboard" className={({isActive}) => isActive ? 'active' : ''}>Dashboard</NavLink></li>
          <li><NavLink to="/audit" className={({isActive}) => isActive ? 'active' : ''}>Audit Log</NavLink></li>
          <li><NavLink to="/demo" className={({isActive}) => isActive ? 'active' : ''}>Demo</NavLink></li>
        </ul>
        <div className="nav-right">
          <div className="status-pill"><span className="pulse-dot"></span> Live Protection</div>
          <NavLink to="/dashboard" className="btn btn-primary btn-sm">Open Dashboard</NavLink>
        </div>
      </div>
    </nav>
  )
}
