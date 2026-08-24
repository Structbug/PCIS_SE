import { useEffect, useState } from 'react'
import { roomsApi } from '../../api/rooms'
import { floorsApi } from '../../api/floors'
import { roomTypesApi } from '../../api/roomTypes'
import { departmentsApi } from '../../api/departments'
import { Table, Modal, Alert, Pagination } from '../../components/ui'
import { useAuth } from '../../hooks/useAuth'
import { optionLabels } from '../../utils/options'
import type { Department, Room, Floor, RoomType } from '../../types'

const PAGE_SIZE = 10

export default function RoomList() {
  const { isAdmin } = useAuth()
  const [rooms, setRooms] = useState<Room[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [floorFilter, setFloorFilter] = useState('')
  const [departmentFilter, setDepartmentFilter] = useState('')

  const [departments, setDepartments] = useState<Department[]>([])
  const [floors, setFloors] = useState<Floor[]>([])
  const [roomTypes, setRoomTypes] = useState<RoomType[]>([])

  const floorLabels = optionLabels(floors, f => f.floorName, f => f.departmentName)
  const roomTypeLabels = optionLabels(roomTypes, t => t.roomTypeName, t => t.departmentName)

  const [createModal, setCreateModal] = useState(false)
  const [editRoom, setEditRoom] = useState<Room | null>(null)
  const [deleteRoom, setDeleteRoom] = useState<Room | null>(null)

  const [formName, setFormName] = useState('')
  const [formNo, setFormNo] = useState('')
  const [formFloor, setFormFloor] = useState('')
  const [formType, setFormType] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    departmentsApi.list().then(d => setDepartments(d.data.data || [])).catch(() => setDepartments([]))
  }, [])

  useEffect(() => {
    if (!departmentFilter) {
      setFloors([])
      setRoomTypes([])
      return
    }
    Promise.all([floorsApi.list(departmentFilter), roomTypesApi.list(departmentFilter)]).then(([f, t]) => {
      setFloors(f.data.data || [])
      setRoomTypes(t.data.data || [])
    }).catch(() => { setFloors([]); setRoomTypes([]) })
  }, [departmentFilter])

  const loadRooms = () => {
    setLoading(true)
    const p = search
      ? roomsApi.search(search, String(page), departmentFilter)
      : floorFilter
        ? roomsApi.floorFilter(floorFilter, String(page), departmentFilter)
        : Promise.resolve({ data: { data: [] as Room[], message: '' } }).then(() =>
            roomsApi.floorFilter('0', String(page), departmentFilter)
          )
    p.then(r => setRooms(r.data.data?.rooms || [])).catch(() => setRooms([])).finally(() => setLoading(false))
  }

  useEffect(() => { loadRooms() }, [page, floorFilter, departmentFilter])

  const handleSearch = (e: React.FormEvent) => { e.preventDefault(); setPage(1); loadRooms() }

  const openCreate = () => { setFormName(''); setFormNo(''); setFormFloor(''); setFormType(''); setCreateModal(true) }

  const handleSave = async () => {
    if (!formName || !departmentFilter || !formFloor || !formType) { setError('Department, room name, floor, and type are required'); return }
    setSaving(true)
    try {
      if (editRoom) {
        await roomsApi.update(editRoom._id, { room_name: formName, room_no: formNo, room_floor_id: formFloor, room_type_id: formType })
        setMessage('Room updated')
      } else {
        await roomsApi.create({ room_name: formName, room_no: formNo, room_floor_id: formFloor, room_type_id: formType })
        setMessage('Room created')
      }
      setCreateModal(false); setEditRoom(null); loadRooms()
    } catch { setError('Save failed') }
    finally { setSaving(false) }
  }

  const handleDelete = async () => {
    if (!deleteRoom) return
    try {
      await roomsApi.delete(deleteRoom._id)
      setMessage('Room deactivated')
      setDeleteRoom(null); loadRooms()
    } catch { setError('Delete failed') }
  }

  return (
    <div>
      <Alert type="error" message={error} onDismiss={() => setError('')} />
      <Alert type="success" message={message} onDismiss={() => setMessage('')} />

      <div className="flex-between mb-16">
        <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--font-size-xl)' }}>Rooms</h3>
        {isAdmin && <button className="btn btn-primary btn-sm" onClick={openCreate}>+ New Room</button>}
      </div>

      <div className="mb-16">
        <form className="filter-bar" onSubmit={handleSearch} style={{ marginBottom: 0 }}>
          <div className="filter-bar-primary">
            <div className="form-group">
              <label>Search</label>
              <input className="form-input" value={search} onChange={e => setSearch(e.target.value)} placeholder="Room name..." />
            </div>
            <button
              type="button"
              className="btn btn-sm filter-toggle"
              onClick={() => setFiltersOpen(open => !open)}
              aria-expanded={filtersOpen}
              aria-controls="room-filter-options"
            >
              <svg aria-hidden="true" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 5h16M7 12h10m-7 7h4" />
              </svg>
              Filters
            </button>
            <button type="submit" className="btn btn-sm">Search</button>
          </div>
          {filtersOpen && (
            <div id="room-filter-options" className="filter-options">
              <div className="form-group">
                <label>Department</label>
                <select className="form-input" value={departmentFilter} onChange={e => { setDepartmentFilter(e.target.value); setFloorFilter(''); setPage(1) }}>
                  <option value="">All</option>
                  {departments.map(d => <option key={d._id} value={d._id}>{d.departmentName}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label>Floor</label>
                <select className="form-input" value={floorFilter} disabled={!departmentFilter} onChange={e => { setFloorFilter(e.target.value); setPage(1) }}>
                  <option value="">{departmentFilter ? 'All' : 'Select department first'}</option>
                  {floors.map(f => <option key={f._id} value={f._id}>{floorLabels[f._id]}</option>)}
                </select>
              </div>
              <button type="submit" className="btn btn-sm">Apply filters</button>
            </div>
          )}
        </form>
      </div>

      {loading ? <p>Loading...</p> : (
        <>
          <Table
            columns={[
              { key: 'roomName', label: 'Name', render: (r: Room) => <strong>{r.roomName}</strong> },
              { key: 'roomNo', label: 'Room No' },
              { key: 'departmentName', label: 'Department' },
              { key: 'roomFloorName', label: 'Floor' },
              { key: 'roomTypeName', label: 'Type' },
              ...(isAdmin ? [{
                key: 'actions' as string, label: 'Actions',
                render: (r: Room) => (
                  <div className="btn-group">
                    <button className="btn btn-sm" onClick={(e) => { e.stopPropagation(); setEditRoom(r); setFormName(r.roomName); setFormNo(r.roomNo || ''); setDepartmentFilter(r.departmentId || ''); setFormFloor(r.roomFloorId); setFormType(r.roomTypeId); setCreateModal(true) }}>Edit</button>
                    <button className="btn btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteRoom(r) }}>Delete</button>
                  </div>
                ),
              }] : []),
            ]}
            data={rooms}
            keyExtractor={(r: Room) => r._id}
            emptyMessage="No rooms found"
          />
          <Pagination currentPage={page} totalItems={rooms.length < PAGE_SIZE ? (page - 1) * PAGE_SIZE + rooms.length : page * PAGE_SIZE + 1} pageSize={PAGE_SIZE} onPageChange={setPage} />
        </>
      )}

      <Modal open={createModal} title={editRoom ? 'Edit Room' : 'New Room'} onClose={() => { setCreateModal(false); setEditRoom(null) }}
        footer={
          <div className="btn-group">
            <button type="button" className="btn btn-sm" onClick={() => { setCreateModal(false); setEditRoom(null) }}>Cancel</button>
            <button type="submit" form="room-form" className="btn btn-sm btn-primary" disabled={saving}>{saving ? 'Saving...' : 'Save'}</button>
          </div>
        }
      >
        <form id="room-form" onSubmit={(e) => { e.preventDefault(); handleSave() }}>
          <div className="form-group">
            <label>Department *</label>
            <select className="form-input" value={departmentFilter} onChange={e => { setDepartmentFilter(e.target.value); setFormFloor(''); setFormType('') }}>
              <option value="">Select department...</option>
              {departments.map(d => <option key={d._id} value={d._id}>{d.departmentName}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Room Name</label>
            <input className="form-input" value={formName} onChange={e => setFormName(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Room No</label>
            <input className="form-input" value={formNo} onChange={e => setFormNo(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Floor</label>
            <select className="form-input" value={formFloor} onChange={e => setFormFloor(e.target.value)}>
              <option value="">Select...</option>
              {floors.map(f => <option key={f._id} value={f._id}>{floorLabels[f._id]}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Room Type</label>
            <select className="form-input" value={formType} onChange={e => setFormType(e.target.value)}>
              <option value="">Select...</option>
              {roomTypes.map(t => <option key={t._id} value={t._id}>{roomTypeLabels[t._id]}</option>)}
            </select>
          </div>
        </form>
      </Modal>

      <Modal open={!!deleteRoom} title="Deactivate Room" onClose={() => setDeleteRoom(null)}
        footer={
          <div className="btn-group">
            <button className="btn btn-sm" onClick={() => setDeleteRoom(null)}>Cancel</button>
            <button className="btn btn-sm btn-danger" onClick={handleDelete}>Deactivate</button>
          </div>
        }
      >
        <p>Deactivate room <strong>{deleteRoom?.roomName}</strong>?</p>
      </Modal>
    </div>
  )
}
