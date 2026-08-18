import { useEffect, useState } from 'react'
import { inventoryApi } from '../../api/inventory'
import { Table, Pagination, Alert, Modal } from '../../components/ui'
import { useAuth } from '../../hooks/useAuth'
import type { ActivityLog } from '../../types'

const PAGE_SIZE = 10

export default function ActivityLogs() {
  const { isAdmin } = useAuth()
  const [logs, setLogs] = useState<ActivityLog[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const [deleteTarget, setDeleteTarget] = useState<ActivityLog | null>(null)
  const [clearModal, setClearModal] = useState(false)
  const [purgeDays, setPurgeDays] = useState('90')
  const [purgeModal, setPurgeModal] = useState(false)

  const loadLogs = () => {
    setLoading(true)
    inventoryApi.logs(String(page))
      .then(r => { setLogs(r.data.data.logs || []); setTotal(r.data.data.totalLogs || 0) })
      .catch(() => setError('Failed to load logs'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadLogs() }, [page])

  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      await inventoryApi.deleteLog(deleteTarget._id)
      setMessage('Activity log deleted')
      setDeleteTarget(null)
      loadLogs()
    } catch { setError('Delete failed') }
  }

  const handleClearAll = async () => {
    try {
      const res = await inventoryApi.clearLogs()
      setMessage(`${res.data.data.deleted} logs cleared`)
      setClearModal(false)
      loadLogs()
    } catch { setError('Clear failed') }
  }

  const handlePurge = async () => {
    const days = parseInt(purgeDays, 10)
    if (!days || days < 1) { setError('Enter a valid number of days'); return }
    try {
      const res = await inventoryApi.purgeLogs(days)
      setMessage(`${res.data.data.deleted} logs older than ${days} day(s) deleted`)
      setPurgeModal(false)
      loadLogs()
    } catch { setError('Purge failed') }
  }

  if (!isAdmin) return <Alert type="error" message="Only administrators can view activity logs." />

  return (
    <div>
      <Alert type="error" message={error} onDismiss={() => setError('')} />
      <Alert type="success" message={message} onDismiss={() => setMessage('')} />

      <div className="flex-between mb-16">
        <p className="text-muted">Retention: logs older than 90 days should be purged periodically to keep the table small.</p>
        <div className="btn-group">
          <button className="btn btn-sm" onClick={() => setPurgeModal(true)}>Purge Old Logs</button>
          <button className="btn btn-sm btn-danger" onClick={() => setClearModal(true)}>Clear All</button>
        </div>
      </div>

      {loading ? <p>Loading...</p> : (
        <>
          <Table
            columns={[
              { key: 'created_at', label: 'Timestamp', render: (l: ActivityLog) => <span className="mono">{new Date(l.created_at).toLocaleString()}</span> },
              { key: 'action', label: 'Action' },
              { key: 'entityType', label: 'Entity Type' },
              { key: 'entityName', label: 'Entity Name' },
              { key: 'performedByName', label: 'Performed By' },
              { key: 'performedByRole', label: 'Role' },
              {
                key: 'actions' as string, label: '',
                render: (l: ActivityLog) => (
                  <button className="btn btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteTarget(l) }}>Delete</button>
                ),
              },
            ]}
            data={logs}
            keyExtractor={(l: ActivityLog) => l._id}
            emptyMessage="No activity logs"
          />
          <Pagination currentPage={page} totalItems={total} pageSize={PAGE_SIZE} onPageChange={setPage} />
        </>
      )}

      <Modal open={!!deleteTarget} title="Delete Activity Log" onClose={() => setDeleteTarget(null)}
        footer={
          <div className="btn-group">
            <button className="btn btn-sm" onClick={() => setDeleteTarget(null)}>Cancel</button>
            <button className="btn btn-sm btn-danger" onClick={handleDelete}>Delete</button>
          </div>
        }
      >
        <p>Delete this activity log entry?</p>
        {deleteTarget && <p className="text-muted">{deleteTarget.action} — {deleteTarget.entityName || deleteTarget.entityType}</p>}
      </Modal>

      <Modal open={clearModal} title="Clear All Activity Logs" onClose={() => setClearModal(false)}
        footer={
          <div className="btn-group">
            <button className="btn btn-sm" onClick={() => setClearModal(false)}>Cancel</button>
            <button className="btn btn-sm btn-danger" onClick={handleClearAll}>Clear All</button>
          </div>
        }
      >
        <p>Delete <strong>all</strong> activity log entries? This cannot be undone.</p>
      </Modal>

      <Modal open={purgeModal} title="Purge Old Activity Logs" onClose={() => setPurgeModal(false)}
        footer={
          <div className="btn-group">
            <button className="btn btn-sm" onClick={() => setPurgeModal(false)}>Cancel</button>
            <button className="btn btn-sm btn-danger" onClick={handlePurge}>Purge</button>
          </div>
        }
      >
        <div className="form-group">
          <label>Delete logs older than (days)</label>
          <input className="form-input" type="number" min={1} value={purgeDays} onChange={e => setPurgeDays(e.target.value)} />
        </div>
      </Modal>
    </div>
  )
}
