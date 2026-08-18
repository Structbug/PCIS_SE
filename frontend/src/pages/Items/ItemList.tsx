import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { itemsApi } from '../../api/items'
import { apiErrorMessage } from '../../api/errors'
import { floorsApi } from '../../api/floors'
import { roomsApi } from '../../api/rooms'
import { departmentsApi } from '../../api/departments'
import { categoriesApi } from '../../api/categories'
import { Alert, StatusTag, Table } from '../../components/ui'
import { useAuth } from '../../hooks/useAuth'
import { optionLabels } from '../../utils/options'
import type { Category, Department, ItemReport, Floor, Room } from '../../types'

const EMPTY_FILTERS = {
  category_id: '', department_id: '', room_id: '', floor_id: '', status: '', source: '', starting_date: '', end_date: '',
}

export default function ItemList() {
  const nav = useNavigate()
  const { isAdmin } = useAuth()
  const [items, setItems] = useState<ItemReport[]>([])
  const [page, setPage] = useState(1)
  const [cursor, setCursor] = useState<string | null>(null)
  const [cursorHistory, setCursorHistory] = useState<string[]>([])
  const [nextCursor, setNextCursor] = useState<string | null>(null)
  const [searchDraft, setSearchDraft] = useState('')
  const [submittedSearch, setSubmittedSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [floors, setFloors] = useState<Floor[]>([])
  const [departments, setDepartments] = useState<Department[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [rooms, setRooms] = useState<Array<Pick<Room, '_id' | 'roomName' | 'roomNo' | 'floorName' | 'departmentName'>>>([])
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [submittedFilters, setSubmittedFilters] = useState(EMPTY_FILTERS)
  const [sources, setSources] = useState<Array<{ sourceId: string; sourceName: string }>>([])
  const [statuses, setStatuses] = useState<Array<{ statusId: string; statusName: string }>>([])

  const floorLabels = optionLabels(floors, f => f.floorName, f => f.departmentName)
  const roomLabels = optionLabels(rooms, r => r.roomName, r => [r.floorName, r.departmentName].filter(Boolean).join(' · '))

  useEffect(() => {
    Promise.all([
      departmentsApi.list().catch(() => ({ data: { data: [] } })),
      categoriesApi.list().catch(() => ({ data: { data: [] } })),
      itemsApi.sources().catch(() => ({ data: { data: [] } })),
      itemsApi.statuses().catch(() => ({ data: { data: [] } })),
    ]).then(([d, c, s, st]) => {
      setDepartments(d.data.data || [])
      setCategories(c.data.data || [])
      setSources(s.data.data || [])
      setStatuses(st.data.data || [])
    })
  }, [])

  useEffect(() => {
    if (!filters.department_id) {
      setFloors([])
      return
    }
    floorsApi.list(filters.department_id).then(f => setFloors(f.data.data || [])).catch(() => setFloors([]))
  }, [filters.department_id])

  // This endpoint is deliberately unpaginated: a select menu must contain every room.
  useEffect(() => {
    if (!filters.floor_id || !filters.department_id) {
      setRooms([])
      return
    }
    roomsApi.listForFloor(filters.floor_id, filters.department_id)
      .then(r => setRooms(r.data.data || []))
      .catch(() => setRooms([]))
  }, [filters.floor_id, filters.department_id])

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError('')

    itemsApi.query({
      ...submittedFilters,
      search: submittedSearch || undefined,
      cursor: cursor || undefined,
      group: '1',
    }, controller.signal)
      .then(res => {
        if (!controller.signal.aborted) {
          setItems(res.data.data.items || [])
          setNextCursor(res.data.data.nextCursor || null)
        }
      })
      .catch(err => {
        if (!controller.signal.aborted) {
          setItems([])
          setNextCursor(null)
          setError(apiErrorMessage(err, 'Unable to load items. Please try again.'))
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })

    return () => controller.abort()
  }, [cursor, submittedFilters, submittedSearch])

  const resetPagination = () => {
    setPage(1)
    setCursor(null)
    setCursorHistory([])
    setNextCursor(null)
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    const search = searchDraft.trim()
    if (search.length === 1) {
      setError('Search must contain at least 2 characters.')
      return
    }
    setSubmittedSearch(search)
    setSubmittedFilters({ ...filters })
    resetPagination()
  }

  const clearSearch = () => {
    setSearchDraft('')
    setSubmittedSearch('')
    setFilters(EMPTY_FILTERS)
    setSubmittedFilters(EMPTY_FILTERS)
    setError('')
    resetPagination()
  }

  const goToNextPage = () => {
    if (!nextCursor) return
    setCursorHistory(history => [...history, cursor || ''])
    setCursor(nextCursor)
    setPage(current => current + 1)
  }

  const goToPreviousPage = () => {
    if (!cursorHistory.length) return
    const previousCursor = cursorHistory[cursorHistory.length - 1]
    setCursorHistory(history => history.slice(0, -1))
    setCursor(previousCursor || null)
    setPage(current => current - 1)
  }

  return (
    <div>
      <div className="flex-between mb-16">
        <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--font-size-xl)' }}>Items</h3>
        {isAdmin && <button className="btn btn-primary btn-sm" onClick={() => nav('/items/new')}>+ New Item</button>}
      </div>

      <div className="mb-16">
        <form className="filter-bar" onSubmit={handleSearch} style={{ marginBottom: 0 }}>
          <div className="form-group">
            <label>Search</label>
            <input className="form-input" value={searchDraft} onChange={(e) => setSearchDraft(e.target.value)} placeholder="Name or serial..." style={{ minWidth: 160 }} />
          </div>
          <div className="form-group">
            <label>Department</label>
            <select className="form-input" value={filters.department_id} onChange={(e) => setFilters(f => ({ ...f, department_id: e.target.value, floor_id: '', room_id: '' }))}>
              <option value="">All</option>
              {departments.map(d => <option key={d._id} value={d._id}>{d.departmentName}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Category</label>
            <select className="form-input" value={filters.category_id} onChange={(e) => setFilters(f => ({ ...f, category_id: e.target.value }))}>
              <option value="">All</option>
              {categories.map(c => <option key={c._id} value={c._id}>{c.categoryName}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Floor</label>
            <select className="form-input" value={filters.floor_id} disabled={!filters.department_id} onChange={(e) => setFilters(f => ({ ...f, floor_id: e.target.value, room_id: '' }))}>
              <option value="">{filters.department_id ? 'All' : 'Select department first'}</option>
              {floors.map(f => <option key={f._id} value={f._id}>{floorLabels[f._id]}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Room</label>
            <select className="form-input" value={filters.room_id} disabled={!filters.floor_id} onChange={(e) => setFilters(f => ({ ...f, room_id: e.target.value }))}>
              <option value="">{filters.floor_id ? 'All' : 'Select floor first'}</option>
              {rooms.map(r => <option key={r._id} value={r._id}>{roomLabels[r._id]}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Status</label>
            <select className="form-input" value={filters.status} onChange={(e) => setFilters(f => ({ ...f, status: e.target.value }))}>
              <option value="">All</option>
              {statuses.map(s => <option key={s.statusId} value={s.statusId}>{s.statusName}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Source</label>
            <select className="form-input" value={filters.source} onChange={(e) => setFilters(f => ({ ...f, source: e.target.value }))}>
              <option value="">All</option>
              {sources.map(s => <option key={s.sourceId} value={s.sourceId}>{s.sourceName}</option>)}
            </select>
          </div>
          <button type="submit" className="btn btn-sm">Apply</button>
          {searchDraft || Object.values(filters).some(Boolean) || submittedSearch || Object.values(submittedFilters).some(Boolean) ? (
            <button type="button" className="btn btn-sm" onClick={clearSearch}>Clear</button>
          ) : null}
        </form>
      </div>

      <Alert type="error" message={error} onDismiss={() => setError('')} />
      {loading ? (
        <p style={{ color: 'var(--text-muted)' }}>Loading...</p>
      ) : (
        <>
          <Table
            columns={[
              { key: 'itemName', label: 'Name', render: (r: ItemReport) => <strong>{r.itemName}</strong> },
              { key: 'quantity', label: 'Quantity', render: (r: ItemReport) => <strong>{r.quantity ?? 1}</strong> },
              { key: 'itemModelNumberOrMake', label: 'Model' },
              { key: 'roomName', label: 'Room' },
              { key: 'floorName', label: 'Floor' },
              { key: 'departmentName', label: 'Department' },
              { key: 'itemSource', label: 'Source' },
              { key: 'itemStatus', label: 'Status', render: (r: ItemReport) => <StatusTag status={r.itemStatus} /> },
              { key: 'categoryName', label: 'Category', render: (r: ItemReport) => <span>{r.categoryName || '—'}</span> },
            ]}
            data={items}
            keyExtractor={(r: ItemReport) => r._id}
            onRowClick={(r: ItemReport) => nav(`/items/${r._id}`)}
            emptyMessage="No items found"
          />
          <div className="flex-between">
            <div className="pagination">
              <button disabled={loading || page <= 1} onClick={goToPreviousPage}>Prev</button>
              <span className="page-info">Page {page}</span>
              <button disabled={loading || !nextCursor} onClick={goToNextPage}>Next</button>
            </div>
            <div className="record-footer">Showing up to 6 results per page</div>
          </div>
        </>
      )}
    </div>
  )
}
