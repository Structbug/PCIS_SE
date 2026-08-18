import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { Header } from './Header'

export function Layout() {
  const [collapsed, setCollapsed] = useState<boolean | null>(null)

  const pageTitles: Record<string, string> = {
    '/': 'Dashboard',
    '/items': 'Items',
    '/rooms': 'Rooms',
    '/floors': 'Floors',
    '/room-types': 'Room Types',
    '/activity-logs': 'Activity Logs',
    '/users': 'Users',
  }

  const path = window.location.pathname
  const title = Object.entries(pageTitles).find(([k]) => path.startsWith(k))?.[1] || 'Inventory'

  const layoutClass = collapsed === null ? '' : collapsed ? 'sidebar-collapsed' : 'sidebar-expanded'

  return (
    <div className={`app-layout ${layoutClass}`.trim()}>
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(c => (c === null ? true : !c))} />
      <div className="app-main">
        <Header title={title} />
        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
