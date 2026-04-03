import { NavLink } from 'react-router-dom'

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <NavLink to="/" className="sb-logo">🛡️</NavLink>
      <nav className="sb-nav">
        <NavLink to="/dashboard" className={({isActive}) => `sb-item${isActive ? ' active' : ''}`} title="Dashboard">⌂</NavLink>
        <NavLink to="/features" className={({isActive}) => `sb-item${isActive ? ' active' : ''}`} title="Features">💳</NavLink>
        <NavLink to="/architecture" className={({isActive}) => `sb-item${isActive ? ' active' : ''}`} title="Architecture">💼</NavLink>
        <NavLink to="/audit" className={({isActive}) => `sb-item${isActive ? ' active' : ''}`} title="Audit Log">✉</NavLink>
        <NavLink to="/demo" className={({isActive}) => `sb-item${isActive ? ' active' : ''}`} title="Demo">▶</NavLink>
      </nav>
    </aside>
  )
}
