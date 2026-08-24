import { useState } from 'react'
import type { ReactNode } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../../hooks/useAuth'
import { Modal } from '../ui'

type SidebarIconName = 'dashboard' | 'items' | 'rooms' | 'departments' | 'categories' | 'activity' | 'users' | 'logout'

const commonNavItems = [
  { section: 'Inventory' },
  { to: '/', label: 'Dashboard', icon: 'dashboard' as SidebarIconName },
  { to: '/items', label: 'Items', icon: 'items' as SidebarIconName },
  { to: '/rooms', label: 'Rooms', icon: 'rooms' as SidebarIconName },
  { section: 'Reference' },
  { to: '/departments', label: 'Departments', icon: 'departments' as SidebarIconName },
  { to: '/categories', label: 'Categories', icon: 'categories' as SidebarIconName },
]

const adminNavItems = [
  { section: 'System' },
  { to: '/activity-logs', label: 'Activity Logs', icon: 'activity' as SidebarIconName },
  { to: '/users', label: 'Users', icon: 'users' as SidebarIconName },
]

function SidebarIcon({ name }: { name: SidebarIconName }) {
  const paths: Record<SidebarIconName, ReactNode> = {
    dashboard: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="5" rx="1" /><rect x="14" y="12" width="7" height="9" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /></>,
    items: <><path d="M4 7.5 12 3l8 4.5v9L12 21l-8-4.5z" /><path d="M4 7.5 12 12l8-4.5M12 12v9" /></>,
    rooms: <><path d="M5 21V4a1 1 0 0 1 1-1h12a1 1 0 0 1 1 1v17" /><path d="M3 21h18M15 12h.01" /></>,
    departments: <><path d="M4 21V6l8-3 8 3v15M9 21v-5h6v5" /><path d="M8 9h.01M12 9h.01M16 9h.01M8 13h.01M12 13h.01M16 13h.01" /></>,
    categories: <><path d="m20 13.5-6.5 6.5a2 2 0 0 1-2.8 0L3 12.3V4h8.3l8.7 8.7a.57.57 0 0 1 0 .8Z" /><circle cx="7.5" cy="8.5" r="1" /></>,
    activity: <><path d="M9 3h6l1 2h3a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h3z" /><path d="M8 11h8M8 15h8" /></>,
    users: <><circle cx="9" cy="8" r="3" /><path d="M3 21v-1a5 5 0 0 1 10 0v1M16 11a3 3 0 1 0-1.2-5.75M16 21v-1a5 5 0 0 0-2.5-4.33" /></>,
    logout: <><path d="m10 17 5-5-5-5M15 12H3M21 19V5" /></>,
  }

  return (
    <svg className="nav-icon" aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      {paths[name]}
    </svg>
  )
}

export function Sidebar({ collapsed, onToggle }: { collapsed: boolean | null; onToggle: () => void }) {
  const { logout, isAdmin, user } = useAuth()
  const navigate = useNavigate()
  const [logoutModal, setLogoutModal] = useState(false)
  const navItems = isAdmin ? [...commonNavItems, ...adminNavItems] : commonNavItems

  const handleLogout = async () => {
    setLogoutModal(false)
    await logout()
  }

  return (
    <aside className="app-sidebar">
      <div className="brand">
        <button
          className="brand-title"
          type="button"
          title="Pulchowk Campus Inventory System"
          onClick={() => navigate('/')}
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
              <SidebarIcon name={item.icon} />
              <span className="nav-label">{item.label}</span>
            </NavLink>
          ) : null
        )}
      </nav>
      <div className="sidebar-footer">
        <div className="sidebar-user">
          <span className="sidebar-user-name">{user?.username}</span>
          <span className="sidebar-user-email">{user?.email}</span>
        </div>
        <button className="logout-button" onClick={() => setLogoutModal(true)} data-label="Logout">
          <SidebarIcon name="logout" />
          <span className="nav-label">Logout</span>
        </button>
      </div>

      <Modal open={logoutModal} title="Log Out" onClose={() => setLogoutModal(false)}
        footer={
          <div className="btn-group">
            <button className="btn btn-sm" onClick={() => setLogoutModal(false)}>Cancel</button>
            <button className="btn btn-sm btn-danger" onClick={handleLogout}>Log Out</button>
          </div>
        }
      >
        <div className="logout-confirmation">
          <p className="logout-question">Are you sure you want to log out?</p>
          {user && <p className="logout-session">Signed in as <strong>{user.username}</strong> · {user.role}</p>}
        </div>
      </Modal>
    </aside>
  )
}
