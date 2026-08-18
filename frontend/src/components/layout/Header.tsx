import { useAuth } from '../../hooks/useAuth'
import { Notifications } from './Notifications'

interface HeaderProps {
  title: string
}

export function Header({ title }: HeaderProps) {
  const { user } = useAuth()

  return (
    <header className="app-header">
      <h1 className="page-title">{title}</h1>
      <div className="header-right">
        <Notifications />
        <div className="user-info">
          <span>{user?.username}</span>
          <span className="role-badge">{user?.role}</span>
        </div>
      </div>
    </header>
  )
}
