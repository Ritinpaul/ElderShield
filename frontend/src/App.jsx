import { Routes, Route, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import HomePage from './pages/HomePage'
import FeaturesPage from './pages/FeaturesPage'
import ArchitecturePage from './pages/ArchitecturePage'
import DashboardPage from './pages/DashboardPage'
import AuditPage from './pages/AuditPage'
import DemoPage from './pages/DemoPage'

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => { window.scrollTo(0, 0) }, [pathname])
  return null
}

export default function App() {
  return (
    <>
      <ScrollToTop />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/features" element={<FeaturesPage />} />
        <Route path="/architecture" element={<ArchitecturePage />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/audit" element={<AuditPage />} />
        <Route path="/demo" element={<DemoPage />} />
      </Routes>
    </>
  )
}
