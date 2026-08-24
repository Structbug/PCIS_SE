import { useEffect, useState } from 'react'
import { inventoryApi } from '../../api/inventory'
import { Table, Pagination, Alert } from '../../components/ui'
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

  const loadLogs = () => {
    setLoading(true)
    inventoryApi.logs(String(page))
      .then(r => { setLogs(r.data.data.logs || []); setTotal(r.data.data.totalLogs || 0) })
      .catch(() => setError('Failed to load logs'))
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadLogs() }, [page])

  if (!isAdmin) return <Alert type="error" message="Only administrators can view activity logs." />

  return (
    <div>
      <Alert type="error" message={error} onDismiss={() => setError('')} />

      <div className="flex-between mb-16">
        <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--font-size-xl)' }}>
          Activity Logs
        </h3>
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
            ]}
            data={logs}
            keyExtractor={(l: ActivityLog) => l._id}
            emptyMessage="No activity logs"
          />
          <Pagination currentPage={page} totalItems={total} pageSize={PAGE_SIZE} onPageChange={setPage} />
        </>
      )}
    </div>
  )
}