import {
  ArrowsClockwise,
  Bank,
  ChartLine,
  ChartLineDown,
  Envelope,
  Funnel,
  GearSix,
  House,
  Receipt,
  SignOut,
  UploadSimple,
  Wallet,
  type Icon,
} from '@phosphor-icons/react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const NAV_ITEMS: { to: string; label: string; icon: Icon; end?: boolean }[] = [
  { to: '/', label: 'Übersicht', icon: House, end: true },
  { to: '/envelopes', label: 'Umschläge', icon: Envelope },
  { to: '/transactions', label: 'Buchungen', icon: Receipt },
  { to: '/accounts', label: 'Konten', icon: Bank },
  { to: '/recurring', label: 'Daueraufträge', icon: ArrowsClockwise },
  { to: '/debts', label: 'Schulden', icon: ChartLineDown },
  { to: '/trends', label: 'Trends', icon: ChartLine },
  { to: '/import', label: 'Import', icon: UploadSimple },
  { to: '/rules', label: 'Regeln', icon: Funnel },
  { to: '/settings', label: 'Einstellungen', icon: GearSix },
]

export function Layout() {
  const { user, logout } = useAuth()

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="brand-mark">
            <Wallet size={16} weight="bold" />
          </span>
          ezbudget
        </div>
        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) => {
            const IconComponent = item.icon
            return (
              <NavLink key={item.to} to={item.to} end={item.end} className={({ isActive }) => (isActive ? 'active' : '')}>
                <span className="icon">
                  <IconComponent size={18} weight="regular" aria-hidden="true" />
                </span>
                <span>{item.label}</span>
              </NavLink>
            )
          })}
        </nav>
        <div className="sidebar-footer">
          <span className="user">{user?.username}</span>
          <button type="button" onClick={() => void logout()}>
            <SignOut size={16} weight="regular" aria-hidden="true" />
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
