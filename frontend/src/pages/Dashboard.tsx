import { useEffect, useState } from 'react'
import { inventoryApi } from '../api/inventory'
import { Table } from '../components/ui'
import { BarChart, ChartLegend, DonutChart } from '../components/Charts'
import { useAuth } from '../hooks/useAuth'
import type { CategoryStat, InventoryStats, ActivityLog } from '../types'

export default function Dashboard() {
  const { isAdmin } = useAuth()
  const [stats, setStats] = useState<InventoryStats | null>(null)
  const [categoryStats, setCategoryStats] = useState<CategoryStat[]>([])
  const [logs, setLogs] = useState<ActivityLog[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      inventoryApi.stats(),
      inventoryApi.categoryStats().catch(() => ({ data: { data: [] } })),
      isAdmin ? inventoryApi.recentLogs().catch(() => ({ data: { data: [] } })) : Promise.resolve({ data: { data: [] } }),
    ]).then(([s, c, l]) => {
      setStats(s.data.data)
      setCategoryStats(c.data.data || [])
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

  const pieData = [
    { label: 'Working', value: stats?.no_working ?? 0, color: 'var(--status-working)' },
    { label: 'Repairable', value: stats?.no_repairable ?? 0, color: 'var(--status-repairable)' },
    { label: 'Not Working', value: stats?.no_not_working ?? 0, color: 'var(--status-notworking)' },
  ].filter((d) => d.value > 0)

  const barColors = ['var(--accent)', 'var(--status-working)', 'var(--status-repairable)', '#8d6e63', '#4a7da5', '#7a5aa0']
  const barData = categoryStats.slice(0, 8).map((c, i) => ({
    label: c.categoryName,
    value: c.totalItems,
    color: barColors[i % barColors.length],
  }))

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

      <div className="dashboard-charts">
        <div className="chart-card">
          <h3 className="chart-card-title">Inventory by Status</h3>
          {pieData.length ? (
            <div className="chart-card-body">
              <DonutChart data={pieData} />
              <ChartLegend items={pieData} />
            </div>
          ) : (
            <p className="text-muted">No items recorded yet.</p>
          )}
        </div>

        <div className="chart-card">
          <h3 className="chart-card-title">Items per Category</h3>
          {barData.length ? (
            <BarChart data={barData} />
          ) : (
            <p className="text-muted">No items recorded yet.</p>
          )}
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
