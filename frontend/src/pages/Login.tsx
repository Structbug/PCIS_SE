import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { apiErrorMessage } from '../api/errors'
import { Alert } from '../components/ui'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      navigate('/')
    } catch (err: unknown) {
      // Never surface the backend message: it could leak account state
      // (username enumeration, H-07 / H-12). Map statuses to safe copy.
      setError(apiErrorMessage(err, 'Invalid username or password', {
        400: 'Invalid username or password',
        429: 'Too many attempts. Please try again later.',
      }))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <img src="/tu-logo.svg" alt="Tribhuvan University Logo" className="login-logo" />
        <h1>Pulchowk Campus Inventory System</h1>
        <p className="subtitle">Sign in to continue</p>
        <Alert type="error" message={error} onDismiss={() => setError('')} />
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="username">Username</label>
            <input id="username" className="form-input" value={username} onChange={(e) => setUsername(e.target.value)} autoFocus required />
          </div>
          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input id="password" type="password" className="form-input" value={password} onChange={(e) => setPassword(e.target.value)} required />
          </div>
          <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: '100%', marginTop: 8 }}>
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
