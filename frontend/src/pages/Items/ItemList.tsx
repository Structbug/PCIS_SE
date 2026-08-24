import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { itemsApi, type CSVImportPreview } from '../../api/items'
import { apiErrorMessage } from '../../api/errors'
import { floorsApi } from '../../api/floors'
import { roomsApi } from '../../api/rooms'
import { departmentsApi } from '../../api/departments'
import { categoriesApi } from '../../api/categories'
import { Alert, Modal, StatusTag, Table } from '../../components/ui'
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
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const [floors, setFloors] = useState<Floor[]>([])
  const [departments, setDepartments] = useState<Department[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [rooms, setRooms] = useState<Array<Pick<Room, '_id' | 'roomName' | 'roomNo' | 'floorName' | 'departmentName'>>>([])
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [submittedFilters, setSubmittedFilters] = useState(EMPTY_FILTERS)
  const [sources, setSources] = useState<Array<{ sourceId: string; sourceName: string }>>([])
  const [statuses, setStatuses] = useState<Array<{ statusId: string; statusName: string }>>([])
  const [importOpen, setImportOpen] = useState(false)
  const [importFile, setImportFile] = useState<File | null>(null)
  const [importPreview, setImportPreview] = useState<CSVImportPreview | null>(null)
  const [importError, setImportError] = useState('')
  const [previewingImport, setPreviewingImport] = useState(false)
  const [importing, setImporting] = useState(false)

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

  const closeImport = () => {
    setImportOpen(false)
    setImportFile(null)
    setImportPreview(null)
    setImportError('')
  }

  const downloadImportTemplate = () => {
    const template = 'department,floor,room,room_type,category,subcategory,item_name,model_or_make,source,status,cost,acquired_date,quantity,description\nComputer Science,Ground Floor,Lab 101,Lab,Electronics,Monitor,Dell Monitor,P2419H,Purchase,Working,25000,2026-01-15,4,For student lab\n'
    const url = URL.createObjectURL(new Blob([template], { type: 'text/csv;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = 'pcis-item-import-template.csv'
    link.click()
    URL.revokeObjectURL(url)
  }

  const previewImport = async () => {
    if (!importFile) {
      setImportError('Choose a CSV file first.')
      return
    }
    setPreviewingImport(true)
    setImportError('')
    try {
      const response = await itemsApi.previewCsvImport(importFile)
      setImportPreview(response.data.data)
    } catch (err: unknown) {
      setImportPreview(null)
      setImportError(apiErrorMessage(err, 'Could not preview the CSV file.'))
    } finally {
      setPreviewingImport(false)
    }
  }

  const commitImport = async () => {
    if (!importFile || !importPreview || importPreview.validRows !== importPreview.totalRows) return
    setImporting(true)
    setImportError('')
    try {
      const response = await itemsApi.commitCsvImport(importFile)
      setMessage(`${response.data.data.importedItems} item(s) imported successfully.`)
      setSubmittedFilters({ ...submittedFilters })
      closeImport()
    } catch (err: unknown) {
      setImportError(apiErrorMessage(err, 'Could not import the CSV file.'))
    } finally {
      setImporting(false)
    }
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
        {isAdmin && (
          <div className="btn-group">
            <button className="btn btn-sm" onClick={() => setImportOpen(true)}>Import CSV</button>
            <button className="btn btn-primary btn-sm" onClick={() => nav('/items/new')}>+ New Item</button>
          </div>
        )}
      </div>

      <div className="mb-16">
        <form className="filter-bar" onSubmit={handleSearch} style={{ marginBottom: 0 }}>
          <div className="filter-bar-primary">
            <div className="form-group">
              <label>Search</label>
              <input className="form-input" value={searchDraft} onChange={(e) => setSearchDraft(e.target.value)} placeholder="Name or serial..." style={{ minWidth: 160 }} />
            </div>
            <button
              type="button"
              className="btn btn-sm filter-toggle"
              onClick={() => setFiltersOpen(open => !open)}
              aria-expanded={filtersOpen}
              aria-controls="item-filter-options"
            >
              <svg aria-hidden="true" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 5h16M7 12h10m-7 7h4" />
              </svg>
              Filters
            </button>
            <button type="submit" className="btn btn-sm">Search</button>
          </div>
          {filtersOpen && (
            <div id="item-filter-options" className="filter-options">
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
              <button type="submit" className="btn btn-sm">Apply filters</button>
              {searchDraft || Object.values(filters).some(Boolean) || submittedSearch || Object.values(submittedFilters).some(Boolean) ? (
                <button type="button" className="btn btn-sm" onClick={clearSearch}>Clear</button>
              ) : null}
            </div>
          )}
        </form>
      </div>

      <Alert type="error" message={error} onDismiss={() => setError('')} />
      <Alert type="success" message={message} onDismiss={() => setMessage('')} />
      {loading ? (
        <p style={{ color: 'var(--text-muted)' }}>Loading...</p>
      ) : (
        <>
          <div className="item-list-table">
            <Table
              columns={[
                { key: 'itemName', label: 'Name', render: (r: ItemReport) => <strong>{r.itemName}</strong> },
                { key: 'quantity', label: 'Quantity', render: (r: ItemReport) => <strong>{r.quantity ?? 1}</strong> },
                { key: 'roomName', label: 'Room' },
                { key: 'floorName', label: 'Floor' },
                { key: 'departmentName', label: 'Department' },
                { key: 'itemStatus', label: 'Status', render: (r: ItemReport) => <StatusTag status={r.itemStatus} /> },
                { key: 'categoryName', label: 'Category', render: (r: ItemReport) => <span>{r.categoryName || '—'}</span> },
              ]}
              data={items}
              keyExtractor={(r: ItemReport) => r._id}
              onRowClick={(r: ItemReport) => nav(`/items/${r._id}`)}
              emptyMessage="No items found"
            />
          </div>
          <div className="item-list-pagination">
            <div className="pagination">
              <button disabled={loading || page <= 1} onClick={goToPreviousPage}>Prev</button>
              <span className="page-info">Page {page}</span>
              <button disabled={loading || !nextCursor} onClick={goToNextPage}>Next</button>
            </div>
            <div className="record-footer">Showing up to 15 results per page</div>
          </div>
        </>
      )}

      <Modal open={importOpen} title="Import Items from CSV" onClose={closeImport}
        footer={
          <div className="btn-group">
            <button className="btn btn-sm" onClick={closeImport}>Cancel</button>
            <button className="btn btn-sm" onClick={downloadImportTemplate}>Download Template</button>
            <button className="btn btn-sm btn-primary" onClick={commitImport} disabled={importing || !importPreview || importPreview.validRows !== importPreview.totalRows}>
              {importing ? 'Importing...' : 'Import Items'}
            </button>
          </div>
        }
      >
        <p className="text-muted mb-16">Upload a UTF-8 encoded CSV file and review the validation results before importing the records.</p>
        <p className="csv-import-validation-notice">You must validate the CSV file before importing.</p>
        <Alert type="error" message={importError} onDismiss={() => setImportError('')} />
        <div className="form-group">
          <label htmlFor="item-csv-file">CSV file</label>
          <input id="item-csv-file" className="form-input" type="file" accept=".csv,text/csv" onChange={(e) => {
            setImportFile(e.target.files?.[0] || null)
            setImportPreview(null)
            setImportError('')
          }} />
        </div>
        <button className="btn btn-sm" onClick={previewImport} disabled={!importFile || previewingImport}>
          {previewingImport ? 'Checking...' : 'Validate CSV'}
        </button>
        {importPreview && (
          <div className="mt-16">
            <p><strong>{importPreview.validRows}</strong> of <strong>{importPreview.totalRows}</strong> row(s) are valid and will create <strong>{importPreview.totalItems}</strong> item(s).</p>
            {importPreview.errors.length > 0 && (
              <div className="alert alert-error" style={{ cursor: 'default' }}>
                <strong>Fix these rows before importing:</strong>
                <ul style={{ margin: '8px 0 0', paddingLeft: 20 }}>
                  {importPreview.errors.map((entry, index) => <li key={`${entry.row}-${index}`}>Row {entry.row || 'total'}: {entry.message}</li>)}
                </ul>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}
