import { NavLink } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'

const commonNavItems = [
  { section: 'Inventory' },
  { to: '/', label: 'Dashboard', icon: '⌂' },
  { to: '/items', label: 'Items', icon: '⊞' },
  { to: '/rooms', label: 'Rooms', icon: '⊠' },
  { section: 'Reference' },
  { to: '/departments', label: 'Departments', icon: '⌘' },
  { to: '/categories', label: 'Categories', icon: '▤' },
]

const adminNavItems = [
  { section: 'System' },
  { to: '/activity-logs', label: 'Activity Logs', icon: '☰' },
  { to: '/users', label: 'Users', icon: '◎' },
]

export function Sidebar({ collapsed, onToggle }: { collapsed: boolean | null; onToggle: () => void }) {
  const { logout, isAdmin } = useAuth()
  const navItems = isAdmin ? [...commonNavItems, ...adminNavItems] : commonNavItems

  return (
    <aside className="app-sidebar">
      <div className="brand">
        <button
          className="brand-title"
          type="button"
          title="Pulchowk Campus Inventory System"
          onClick={() => window.location.reload()}
        >
          <img src="/tu-logo.svg" alt="Tribhuvan University Logo" className="brand-logo" />
          PCIS
        </button>
        <button className="sidebar-toggle" onClick={onToggle} aria-label="Toggle sidebar" title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}>
          <span></span>
          <span></span>
          <span></span>
        </button>
      </div>
      <nav>
        {navItems.map((item) =>
          'section' in item ? (
            <div key={item.section} className="nav-section">{item.section}</div>
          ) : 'to' in item ? (
            <NavLink key={item.to} to={item.to} end className={({ isActive }) => isActive ? 'active' : ''} data-label={item.label}>
              <span>{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </NavLink>
          ) : null
        )}
        <div className="nav-section">Session</div>
        <button onClick={logout} data-label="Logout">
          <span>↩</span>
          <span className="nav-label">Logout</span>
        </button>
      </nav>
    </aside>
  )
}
