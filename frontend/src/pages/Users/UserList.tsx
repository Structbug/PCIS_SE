import { useEffect, useState } from 'react'
import { authApi } from '../../api/auth'
import { Table, Modal, Alert } from '../../components/ui'
import { useAuth } from '../../hooks/useAuth'
import type { User } from '../../types'

export default function UserList() {
  const { isAdmin } = useAuth()
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const [deleteTarget, setDeleteTarget] = useState<User | null>(null)
  const [registerModal, setRegisterModal] = useState(false)
  const [formUsername, setFormUsername] = useState('')
  const [formEmail, setFormEmail] = useState('')
  const [formPhone, setFormPhone] = useState('')
  const [formPassword, setFormPassword] = useState('')
  const [formRole, setFormRole] = useState('User')
  const [saving, setSaving] = useState(false)

  const loadUsers = () => {
    setLoading(true)
    const p = search
      ? authApi.searchUsers(search, String(page))
      : authApi.getActiveUsers(String(page))
    p.then(r => {
      const d = r.data.data
      setUsers(d?.users || (Array.isArray(d) ? d : []))
    }).catch(() => setUsers([])).finally(() => setLoading(false))
  }

  useEffect(() => { loadUsers() }, [page, search])

  const handleSearch = (e: React.FormEvent) => { e.preventDefault(); setPage(1); loadUsers() }

  const handleRegister = async () => {
    if (!formUsername || !formEmail || !formPhone || !formPassword) { setError('All fields required'); return }
    setSaving(true)
    try {
      await authApi.register({ username: formUsername, email: formEmail, phone_number: formPhone, password: formPassword, role: formRole as User['role'] })
      setMessage('User created')
      setRegisterModal(false); loadUsers()
    } catch { setError('Registration failed') }
    finally { setSaving(false) }
  }

  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      await authApi.deleteUser(deleteTarget._id)
      setMessage('User deactivated')
      setDeleteTarget(null); loadUsers()
    } catch { setError('Delete failed') }
  }

  if (!isAdmin) return <Alert type="error" message="Only administrators can manage users." />

  return (
    <div>
      <Alert type="error" message={error} onDismiss={() => setError('')} />
      <Alert type="success" message={message} onDismiss={() => setMessage('')} />

      <div className="flex-between mb-16">
        <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--font-size-xl)' }}>Users</h3>
        <button className="btn btn-sm btn-primary" onClick={() => { setFormUsername(''); setFormEmail(''); setFormPhone(''); setFormPassword(''); setFormRole('User'); setRegisterModal(true) }}>
          + New User
        </button>
      </div>

      <div className="mb-16">
        <form className="filter-bar" onSubmit={handleSearch} style={{ marginBottom: 0 }}>
          <div className="form-group">
            <label>Search</label>
            <input className="form-input" value={search} onChange={e => setSearch(e.target.value)} placeholder="Username..." />
          </div>
          <button type="submit" className="btn btn-sm">Search</button>
        </form>
      </div>

      {loading ? <p>Loading...</p> : (
        <Table
          columns={[
            { key: 'username', label: 'Username', render: (u: User) => <strong>{u.username}</strong> },
            { key: 'email', label: 'Email' },
            { key: 'phone_number', label: 'Phone' },
            { key: 'role', label: 'Role', render: (u: User) => <span className="mono">{u.role}</span> },
            { key: 'isActive', label: 'Active', render: (u: User) => u.isActive ? 'Yes' : 'No' },
            { key: 'createdAt', label: 'Created', render: (u: User) => <span className="mono">{new Date(u.createdAt).toLocaleDateString()}</span> },
            {
              key: 'actions' as string, label: '',
              render: (u: User) => (
                <button className="btn btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteTarget(u) }}>Delete</button>
              ),
            },
          ]}
          data={users}
          keyExtractor={(u: User) => u._id}
          emptyMessage="No users"
        />
      )}

      <Modal open={registerModal} title="New User" onClose={() => setRegisterModal(false)}
        footer={
          <div className="btn-group">
            <button type="button" className="btn btn-sm" onClick={() => setRegisterModal(false)}>Cancel</button>
            <button type="submit" form="user-form" className="btn btn-sm btn-primary" disabled={saving}>{saving ? 'Creating...' : 'Create'}</button>
          </div>
        }
      >
        <form id="user-form" onSubmit={(e) => { e.preventDefault(); handleRegister() }}>
          <div className="form-group">
            <label>Username</label>
            <input className="form-input" value={formUsername} onChange={e => setFormUsername(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Email</label>
            <input className="form-input" type="email" value={formEmail} onChange={e => setFormEmail(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Phone</label>
            <input className="form-input" value={formPhone} onChange={e => setFormPhone(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Password</label>
            <input className="form-input" type="password" value={formPassword} onChange={e => setFormPassword(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Role</label>
            <select className="form-input" value={formRole} onChange={e => setFormRole(e.target.value)}>
              <option value="User">User</option>
              <option value="Admin">Admin</option>
            </select>
          </div>
        </form>
      </Modal>

      <Modal open={!!deleteTarget} title="Deactivate User" onClose={() => setDeleteTarget(null)}
        footer={
          <div className="btn-group">
            <button className="btn btn-sm" onClick={() => setDeleteTarget(null)}>Cancel</button>
            <button className="btn btn-sm btn-danger" onClick={handleDelete}>Deactivate</button>
          </div>
        }
      >
        <p>Deactivate user <strong>{deleteTarget?.username}</strong>?</p>
      </Modal>
    </div>
  )
}
