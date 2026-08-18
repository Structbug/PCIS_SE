import { useEffect, useRef, useState, type FormEvent } from 'react'
import { accessRequestsApi } from '../../api/accessRequests'
import { apiErrorMessage } from '../../api/errors'
import { useAuth } from '../../hooks/useAuth'
import type { AccessRequest, BlockedRequester } from '../../types'

const POLL_INTERVAL_MS = 30000

export function Notifications() {
  const { isAdmin } = useAuth()
  const [open, setOpen] = useState(false)
  const [requests, setRequests] = useState<AccessRequest[]>([])
  const [pendingCount, setPendingCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [blocked, setBlocked] = useState<BlockedRequester[]>([])
  const [blockedOpen, setBlockedOpen] = useState(false)
  const [blockInput, setBlockInput] = useState('')
  const rootRef = useRef<HTMLDivElement>(null)

  const loadBlocked = () => {
    accessRequestsApi.listBlocked()
      .then(r => setBlocked(r.data.data.blockedRequesters || []))
      .catch(() => setBlocked([]))
  }

  const load = () => {
    accessRequestsApi.list()
      .then(r => {
        setRequests(r.data.data.requests || [])
        setPendingCount(r.data.data.pendingCount || 0)
      })
      .catch(() => {
        setRequests([])
        setPendingCount(0)
      })
      .finally(() => setLoading(false))
    loadBlocked()
  }

  useEffect(() => {
    if (!isAdmin) return
    load()
    const interval = setInterval(load, POLL_INTERVAL_MS)
    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAdmin])

  useEffect(() => {
    if (!open) return
    const onClickOutside = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    document.addEventListener('mousedown', onClickOutside)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onClickOutside)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  if (!isAdmin) return null

  const setStatus = async (req: AccessRequest, status: AccessRequest['status']) => {
    try {
      await accessRequestsApi.setStatus(req._id, status)
      load()
    } catch {
      setError('Update failed')
    }
  }

  const dismiss = async (req: AccessRequest) => {
    try {
      await accessRequestsApi.remove(req._id)
      load()
    } catch {
      setError('Remove failed')
    }
  }

  const blockRequester = async (email: string) => {
    try {
      await accessRequestsApi.block(email)
      load()
    } catch (err: unknown) {
      setError(apiErrorMessage(err, 'Block failed'))
    }
  }

  const unblockRequester = async (req: BlockedRequester) => {
    try {
      await accessRequestsApi.unblock(req._id)
      load()
    } catch (err: unknown) {
      setError(apiErrorMessage(err, 'Unblock failed'))
    }
  }

  const submitBlock = async (e: FormEvent) => {
    e.preventDefault()
    if (!blockInput.trim()) return
    setError('')
    await blockRequester(blockInput.trim())
    setBlockInput('')
  }

  return (
    <div className="notifications" ref={rootRef}>
      <button
        className={`notif-bell${open ? ' active' : ''}`}
        onClick={() => setOpen(o => !o)}
        aria-label="Access requests"
        title="Access requests"
      >
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
          <path d="M13.73 21a2 2 0 0 1-3.46 0" />
        </svg>
        {pendingCount > 0 && <span className="notif-badge">{pendingCount}</span>}
      </button>

      {open && (
        <div className="notif-panel">
          <div className="notif-header">
            <strong>Access Requests</strong>
            <button className="btn btn-sm" onClick={() => { setOpen(false); setError('') }}>Close</button>
          </div>
          {error && <AlertInline message={error} />}
          {loading ? (
            <p className="notif-empty">Loading...</p>
          ) : requests.length === 0 ? (
            <p className="notif-empty">No access requests yet.</p>
          ) : (
            <ul className="notif-list">
              {requests.map(req => (
                <li key={req._id} className="notif-item">
                  <div className="notif-item-top">
                    <strong>{req.fullName}</strong>
                    <span className={`status-tag ${req.status.toLowerCase()}`}>{req.status}</span>
                  </div>
                  <div className="notif-meta">
                    <span>{req.department}</span>
                    {req.rollNo && <span>· {req.rollNo}</span>}
                  </div>
                  <a className="notif-email" href={`mailto:${req.email}`}>{req.email}</a>
                  {req.description && <p className="notif-desc">{req.description}</p>}
                  <div className="notif-item-foot">
                    <span className="mono">{new Date(req.createdAt).toLocaleString()}</span>
                    <div className="btn-group">
                      {req.status !== 'Approved' && (
                        <button className="btn btn-sm" onClick={() => setStatus(req, 'Approved')}>Approve</button>
                      )}
                      {req.status !== 'Denied' && (
                        <button className="btn btn-sm" onClick={() => setStatus(req, 'Denied')}>Deny</button>
                      )}
                      <button className="btn btn-sm" onClick={() => blockRequester(req.email)}>Block</button>
                      <button className="btn btn-sm btn-danger" onClick={() => dismiss(req)}>Remove</button>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}

          <div className="notif-blocked">
            <button className="btn btn-sm notif-blocked-toggle" onClick={() => setBlockedOpen(o => !o)}>
              {blockedOpen ? 'Hide' : 'Manage'} blocked requesters ({blocked.length})
            </button>
            {blockedOpen && (
              <div className="notif-blocked-body">
                <form className="notif-blocked-form" onSubmit={submitBlock}>
                  <input
                    className="form-input"
                    value={blockInput}
                    onChange={e => setBlockInput(e.target.value)}
                    placeholder="email@example.com"
                    aria-label="Email to block"
                  />
                  <button type="submit" className="btn btn-sm btn-primary">Block</button>
                </form>
                {blocked.length === 0 ? (
                  <p className="notif-empty">No blocked requesters.</p>
                ) : (
                  <ul className="notif-list">
                    {blocked.map(b => (
                      <li key={b._id} className="notif-item">
                        <div className="notif-item-top">
                          <span className="notif-email">{b.email}</span>
                          <button className="btn btn-sm" onClick={() => unblockRequester(b)}>Unblock</button>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function AlertInline({ message }: { message: string }) {
  return <div className="alert alert-error">{message}</div>
}