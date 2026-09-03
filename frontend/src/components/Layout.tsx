import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const NAV_ITEMS: { to: string; label: string; icon: string; end?: boolean }[] = [
  { to: '/', label: 'Übersicht', icon: '🏠', end: true },
  { to: '/envelopes', label: 'Umschläge', icon: '✉️' },
  { to: '/transactions', label: 'Buchungen', icon: '📒' },
  { to: '/accounts', label: 'Konten', icon: '🏦' },
  { to: '/recurring', label: 'Daueraufträge', icon: '🔁' },
  { to: '/debts', label: 'Schulden', icon: '📉' },
  { to: '/import', label: 'Import', icon: '📥' },
]

export function Layout() {
  const { user, logout } = useAuth()

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="dot" />
          ezbudget
        </div>
        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => (isActive ? 'active' : '')}>
              <span className="icon">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="user">{user?.username}</span>
          <button type="button" onClick={() => void logout()}>
            Abmelden
          </button>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}
