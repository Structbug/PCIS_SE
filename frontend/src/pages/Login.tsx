import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'
import { apiErrorMessage } from '../api/errors'
import { accessRequestsApi } from '../api/accessRequests'
import { Alert, Modal } from '../components/ui'

const EMPTY_FORM = { fullName: '', email: '', department: '', rollNo: '', description: '' }

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const [requestOpen, setRequestOpen] = useState(false)
  const [requestSubmitted, setRequestSubmitted] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [requestError, setRequestError] = useState('')
  const [sending, setSending] = useState(false)

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

  const openRequest = () => {
    setForm(EMPTY_FORM)
    setRequestError('')
    setRequestOpen(true)
  }

  const handleRequestSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!form.fullName.trim() || !form.email.trim() || !form.department.trim()) {
      setRequestError('Full name, email, and department are required')
      return
    }
    const email = form.email.trim().toLowerCase()
    setRequestError('')
    setSending(true)
    try {
      await accessRequestsApi.create({
        fullName: form.fullName.trim(),
        email,
        department: form.department.trim(),
        rollNo: form.rollNo.trim() || undefined,
        description: form.description.trim() || undefined,
      })
      setForm(EMPTY_FORM)
      setRequestOpen(false)
      setRequestSubmitted(true)
    } catch (err: unknown) {
      setRequestError(apiErrorMessage(err, 'Request failed. Please try again.', { 403: 'You are blocked from making requests.', 429: 'Request limit reached. You can submit up to 4 access requests per month.' }))
    } finally {
      setSending(false)
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
        <div className="login-divider"><span>or</span></div>
        <button type="button" className="btn btn-sm" onClick={openRequest} style={{ width: '100%' }}>
          Request Access
        </button>
      </div>

      <Modal open={requestOpen} title="Request Access" onClose={() => setRequestOpen(false)}
        footer={
          <div className="btn-group">
            <button className="btn btn-sm" onClick={() => setRequestOpen(false)}>Cancel</button>
            <button className="btn btn-sm btn-primary" onClick={handleRequestSubmit} disabled={sending}>{sending ? 'Submitting...' : 'Submit Request'}</button>
          </div>
        }
      >
        <p className="text-muted mb-16">Please provide your details below. An administrator will review your request and send your credentials by email.</p>
        <Alert type="error" message={requestError} onDismiss={() => setRequestError('')} />
        <form onSubmit={handleRequestSubmit}>
          <div className="form-group">
            <label>Full Name</label>
            <input className="form-input" value={form.fullName} onChange={e => setForm({ ...form, fullName: e.target.value })} required />
          </div>
          <div className="form-group">
            <label>Email</label>
            <input className="form-input" type="email" value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} required />
          </div>
          <div className="form-group">
            <label>Department</label>
            <input className="form-input" value={form.department} onChange={e => setForm({ ...form, department: e.target.value })} required />
          </div>
          <div className="form-group">
            <label>Roll No</label>
            <input className="form-input" value={form.rollNo} onChange={e => setForm({ ...form, rollNo: e.target.value })} />
          </div>
          <div className="form-group">
            <label>Why do you need access?</label>
            <textarea className="form-input" value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} />
          </div>
        </form>
      </Modal>

      <Modal open={requestSubmitted} title="Request Submitted" onClose={() => setRequestSubmitted(false)}
        footer={
          <div className="btn-group">
            <button className="btn btn-sm btn-primary" onClick={() => setRequestSubmitted(false)}>OK</button>
          </div>
        }
      >
        <div className="success-dialog">
          <span className="success-tick">
            <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
              <path d="M20 6L9 17l-5-5" />
            </svg>
          </span>
          <h3>Your request was submitted</h3>
          <p className="text-muted">An administrator will review your request and send your credentials by email.</p>
        </div>
      </Modal>
    </div>
  )
}
