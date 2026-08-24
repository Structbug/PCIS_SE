import { useAuth } from '../../hooks/useAuth'

interface HeaderProps {
  title: string
}

export function Header({ title }: HeaderProps) {
  const { user } = useAuth()
  const initials = (user?.username || '?').split(/[\s._-]+/).filter(Boolean).slice(0, 2).map((p) => p[0]?.toUpperCase()).join('')

  return (
    <header className="app-header">
      <h1 className="page-title">{title}</h1>
      <div className="header-right">
        <div className="user-info">
          <span className="user-avatar">{initials}</span>
          <span className="user-name">{user?.username}</span>
        </div>
      </div>
    </header>
  )
}
