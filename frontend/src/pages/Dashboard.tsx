import { useEffect, useState } from 'react'
import { inventoryApi } from '../api/inventory'
import { Table } from '../components/ui'
import { useAuth } from '../hooks/useAuth'
import type { InventoryStats, ActivityLog } from '../types'

export default function Dashboard() {
  const { isAdmin } = useAuth()
  const [stats, setStats] = useState<InventoryStats | null>(null)
  const [logs, setLogs] = useState<ActivityLog[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      inventoryApi.stats(),
      isAdmin ? inventoryApi.recentLogs().catch(() => ({ data: { data: [] } })) : Promise.resolve({ data: { data: [] } }),
    ]).then(([s, l]) => {
      setStats(s.data.data)
      setLogs(l.data.data || [])
    }).finally(() => setLoading(false))
  }, [isAdmin])

  if (loading) return <p style={{ color: 'var(--text-muted)' }}>Loading...</p>

  const items = [
    { label: 'Total Items', value: stats?.no_total_items ?? 0 },
    { label: 'Working', value: stats?.no_working ?? 0 },
    { label: 'Repairable', value: stats?.no_repairable ?? 0 },
    { label: 'Not Working', value: stats?.no_not_working ?? 0 },
  ]

  return (
    <div>
      <div className="dashboard-ledger">
        <h2>Inventory Summary</h2>
        <div className="ledger-grid">
          {items.map((item) => (
            <div key={item.label} className="ledger-item">
              <div className="value">{item.value}</div>
              <div className="label">{item.label}</div>
            </div>
          ))}
        </div>
      </div>

      {isAdmin && (
        <>
          <div className="flex-between mb-16">
            <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--font-size-xl)' }}>
              Recent Activity
            </h3>
          </div>

          <Table
            columns={[
              { key: 'created_at', label: 'Timestamp', render: (r: ActivityLog) => <span className="mono">{new Date(r.created_at).toLocaleString()}</span> },
              { key: 'action', label: 'Action' },
              { key: 'entityType', label: 'Entity' },
              { key: 'entityName', label: 'Name' },
              { key: 'performedByName', label: 'Performed By' },
            ]}
            data={logs}
            keyExtractor={(r: ActivityLog) => r._id}
            emptyMessage="No recent activity"
          />
        </>
      )}
    </div>
  )
}
