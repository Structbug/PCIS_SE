import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { itemsApi } from '../../api/items'
import { apiErrorMessage } from '../../api/errors'
import { StatusTag, Alert, Modal } from '../../components/ui'
import { useAuth } from '../../hooks/useAuth'
import { floorsApi } from '../../api/floors'
import { roomsApi } from '../../api/rooms'
import { departmentsApi } from '../../api/departments'
import type { Department, ItemReport, Floor, Room } from '../../types'

const statusMap: Record<string, string> = { '1234': 'Working', '3456': 'Repairable', '5678': 'Not working' }

export default function ItemDetail() {
  const { id } = useParams<{ id: string }>()
  const nav = useNavigate()
  const { isAdmin } = useAuth()
  const [item, setItem] = useState<ItemReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const [editMode, setEditMode] = useState<'details' | 'status' | 'room' | 'department' | null>(null)
  const [deleteModal, setDeleteModal] = useState(false)

  const [floors, setFloors] = useState<Floor[]>([])
  const [rooms, setRooms] = useState<Room[]>([])

  useEffect(() => {
    if (!id) return
    setLoading(true)
    itemsApi.get(id).then(async r => {
      setItem(r.data.data)
      // The item response includes its department, so room moves stay within it.
      await floorsApi.list(r.data.data.departmentId || undefined)
        .then(f => setFloors(f.data.data || []))
        .catch(() => setFloors([]))
    }).catch(() => setError('Item not found')).finally(() => setLoading(false))
  }, [id])

  const refreshItem = () => {
    if (!id) return
    itemsApi.get(id).then(r => {
      setItem(r.data.data)
    })
  }

  const handleDelete = async () => {
    if (!id) return
    try {
      await itemsApi.delete(id)
      setMessage('Item deactivated')
      setTimeout(() => nav('/items'), 1000)
    } catch { setError('Delete failed') }
    setDeleteModal(false)
  }

  if (loading) return <p>Loading...</p>
  if (!item) return <Alert type="error" message={error || 'Item not found'} />

  return (
    <div>
      <Alert type="error" message={error} onDismiss={() => setError('')} />
      <Alert type="success" message={message} onDismiss={() => setMessage('')} />

      <div className="flex-between mb-16">
        <h2 style={{ fontFamily: 'var(--font-heading)' }}>{item.itemName}</h2>
        <div className="btn-group">
          {isAdmin && (
            <>
              <button className="btn btn-sm" onClick={() => setEditMode('details')}>Edit Details</button>
              <button className="btn btn-sm" onClick={() => setEditMode('status')}>Change Status</button>
              <button className="btn btn-sm" onClick={() => setEditMode('room')}>Move Room</button>
              <button className="btn btn-sm" onClick={() => setEditMode('department')}>Move Department</button>
              <button className="btn btn-sm btn-danger" onClick={() => setDeleteModal(true)}>Deactivate</button>
            </>
          )}
        </div>
      </div>

      <div className="detail-card">
        <div className="field-group">
          <span className="field-label">Serial #</span>
          <span className="field-value mono">{item.itemSerialNumber || '—'}</span>
        </div>
        <div className="field-group">
          <span className="field-label">Model / Make</span>
          <span className="field-value">{item.itemModelNumberOrMake || '—'}</span>
        </div>
        <div className="field-group">
          <span className="field-label">Description</span>
          <span className="field-value">{item.itemDescription || '—'}</span>
        </div>
        <div className="field-group">
          <span className="field-label">Department</span>
          <span className="field-value">{item.departmentName || '—'}</span>
        </div>
        <div className="field-group">
          <span className="field-label">Room</span>
          <span className="field-value">{item.roomName}</span>
        </div>
        <div className="field-group">
          <span className="field-label">Floor</span>
          <span className="field-value">{item.floorName}</span>
        </div>
        <div className="field-group">
          <span className="field-label">Source</span>
          <span className="field-value">{item.itemSource}</span>
        </div>
        <div className="field-group">
          <span className="field-label">Cost</span>
          <span className="field-value mono">{item.itemCost != null ? Number(item.itemCost).toFixed(2) : '—'}</span>
        </div>
        <div className="field-group">
          <span className="field-label">Status</span>
          <span className="field-value"><StatusTag status={item.itemStatus} /></span>
        </div>
        <div className="field-group">
          <span className="field-label">Acquired</span>
          <span className="field-value">{item.itemAcquiredDate ? new Date(item.itemAcquiredDate).toLocaleDateString() : 'Not Mentioned'}</span>
        </div>
        <div className="field-group">
          <span className="field-label">Created By</span>
          <span className="field-value">{item.creatorUsername}</span>
        </div>
        <div className="field-group">
          <span className="field-label">Created</span>
          <span className="field-value mono">{new Date(item.createdAt).toLocaleString()}</span>
        </div>
        <div className="field-group">
          <span className="field-label">Updated</span>
          <span className="field-value mono">{new Date(item.updatedAt).toLocaleString()}</span>
        </div>
      </div>

      {/* Edit Details Modal */}
      <EditDetailsModal
        open={editMode === 'details'}
        item={item}
        floors={floors}
        rooms={rooms}
        onClose={() => setEditMode(null)}
        onSaved={() => { refreshItem(); setEditMode(null); setMessage('Item updated') }}
        onError={setError}
        fetchRooms={async (floorId) => { const r = await roomsApi.floorFilter(floorId, '1'); const list = r.data.data?.rooms || r.data.data || []; setRooms(list); return list }}
      />

      {/* Status Modal */}
      <Modal open={editMode === 'status'} title="Change Status" onClose={() => setEditMode(null)}>
        <p style={{ marginBottom: 12, fontSize: 'var(--font-size-sm)' }}>Select new status for <strong>{item.itemName}</strong>:</p>
        <table className="data-table">
          <tbody>
            {Object.entries(statusMap).map(([id, status]) => (
              <tr key={id} style={{ cursor: 'pointer' }} onClick={async () => {
                try {
                  await itemsApi.updateStatus(item._id, id)
                  refreshItem(); setEditMode(null); setMessage('Status updated')
                } catch { setError('Update failed') }
              }}>
                <td><StatusTag status={status} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Modal>

      {/* Room Modal */}
      <MoveRoomModal
        open={editMode === 'room'}
        item={item}
        floors={floors}
        onClose={() => setEditMode(null)}
        onSaved={() => { refreshItem(); setEditMode(null); setMessage('Room moved') }}
        onError={setError}
        fetchRooms={async (floorId) => { const r = await roomsApi.floorFilter(floorId, '1'); const list = r.data.data?.rooms || []; setRooms(list); return list }}
      />

      <MoveDepartmentModal
        open={editMode === 'department'}
        item={item}
        onClose={() => setEditMode(null)}
        onSaved={() => { refreshItem(); setEditMode(null); setMessage('Department moved') }}
      />

      {/* Delete confirm */}
      <Modal open={deleteModal} title="Deactivate Record" onClose={() => setDeleteModal(false)}
        footer={
          <div className="btn-group">
            <button className="btn btn-sm" onClick={() => setDeleteModal(false)}>Cancel</button>
            <button className="btn btn-sm btn-danger" onClick={handleDelete}>Deactivate</button>
          </div>
        }
      >
        <p>Deactivate <strong>{item.itemName}</strong>? This is a soft delete — the record will be preserved with an inactive flag.</p>
      </Modal>
    </div>
  )
}

// ─── Subcomponents ───

function EditDetailsModal({ open, item, floors, rooms: initialRooms, onClose, onSaved, onError, fetchRooms }: {
  open: boolean; item: ItemReport; floors: Floor[]; rooms: Room[]
  onClose: () => void; onSaved: () => void; onError: (msg: string) => void
  fetchRooms: (floorId: string) => Promise<Room[]>
}) {
  const [name, setName] = useState(item.itemName)
  const [desc, setDesc] = useState(item.itemDescription || '')
  const [model, setModel] = useState(item.itemModelNumberOrMake || '')
  const [source, setSource] = useState<string>(item.itemSource)
  const [cost, setCost] = useState(String(item.itemCost || ''))
  const [acquired, setAcquired] = useState(item.itemAcquiredDate?.split('T')[0] || '')
  const [floorId, setFloorId] = useState(item.itemFloor)
  const [roomId, setRoomId] = useState(item.itemRoom)
  const [status, setStatus] = useState<string>(item.itemStatus)
  const [localRooms, setLocalRooms] = useState(initialRooms)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (floorId) fetchRooms(floorId).then(setLocalRooms)
  }, [floorId])

  const handleSave = async () => {
    setSaving(true)
    try {
      await itemsApi.updateDetails(item._id, {
        item_name: name,
        item_description: desc,
        item_make_or_model_no: model,
        item_source: source,
        item_cost: cost ? Number(cost) : undefined,
        item_acquired_date: acquired || undefined,
        item_room_id: roomId,
        item_status: status,
      })
      onSaved()
    } catch (err: unknown) {
      onError(apiErrorMessage(err, 'Update failed'))
    } finally { setSaving(false) }
  }

  return (
    <Modal open={open} title="Edit Item Details" onClose={onClose}
      footer={
        <div className="btn-group">
          <button type="button" className="btn btn-sm" onClick={onClose}>Cancel</button>
          <button type="submit" form="edit-item-form" className="btn btn-sm btn-primary" disabled={saving}>{saving ? 'Saving...' : 'Save'}</button>
        </div>
      }
    >
      <form id="edit-item-form" onSubmit={(e) => { e.preventDefault(); handleSave() }}>
        <div className="form-row">
        <div className="form-group">
          <label>Name</label>
          <input className="form-input" value={name} onChange={e => setName(e.target.value)} />
        </div>
        <div className="form-group">
          <label>Model / Make</label>
          <input className="form-input" value={model} onChange={e => setModel(e.target.value)} />
        </div>
      </div>
      <div className="form-group">
        <label>Description</label>
        <textarea className="form-input" value={desc} onChange={e => setDesc(e.target.value)} />
      </div>
      <div className="form-row">
        <div className="form-group">
          <label>Source</label>
          <select className="form-input" value={source} onChange={e => setSource(e.target.value)}>
            <option value="Purchase">Purchase</option>
            <option value="Donation">Donation</option>
          </select>
        </div>
        <div className="form-group">
          <label>Cost</label>
          <input className="form-input" type="number" value={cost} onChange={e => setCost(e.target.value)} />
        </div>
      </div>
      <div className="form-row">
        <div className="form-group">
          <label>Acquired Date</label>
          <input className="form-input" type="date" value={acquired} onChange={e => setAcquired(e.target.value)} />
        </div>
        <div className="form-group">
          <label>Status</label>
          <select className="form-input" value={status} onChange={e => setStatus(e.target.value)}>
            <option value="Working">Working</option>
            <option value="Repairable">Repairable</option>
            <option value="Not working">Not working</option>
          </select>
        </div>
      </div>
      <div className="form-row">
        <div className="form-group">
          <label>Floor</label>
          <select className="form-input" value={floorId} onChange={e => { setFloorId(e.target.value); setRoomId('') }}>
            {floors.map(f => <option key={f._id} value={f._id}>{f.floorName}</option>)}
          </select>
        </div>
        <div className="form-group">
          <label>Room</label>
          <select className="form-input" value={roomId} onChange={e => setRoomId(e.target.value)}>
            <option value="">Select...</option>
            {localRooms.map(r => <option key={r._id} value={r._id}>{r.roomName}</option>)}
          </select>
        </div>
      </div>
      </form>
    </Modal>
  )
}

function MoveRoomModal({ open, item, floors, onClose, onSaved, onError, fetchRooms }: {
  open: boolean; item: ItemReport; floors: Floor[]
  onClose: () => void; onSaved: () => void; onError: (msg: string) => void
  fetchRooms: (floorId: string) => Promise<Room[]>
}) {
  const [localRooms, setLocalRooms] = useState<Room[]>([])
  const [floorId, setFloorId] = useState('')
  const [roomId, setRoomId] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (floorId) fetchRooms(floorId).then(setLocalRooms)
  }, [floorId])

  const handleSave = async () => {
    if (!roomId) return
    setSaving(true)
    try {
      await itemsApi.moveRoom(item._id, roomId)
      onSaved()
    } catch { onError('Move failed') }
    finally { setSaving(false) }
  }

  return (
    <Modal open={open} title="Move Item to Room" onClose={onClose}
      footer={
        <div className="btn-group">
          <button type="button" className="btn btn-sm" onClick={onClose}>Cancel</button>
          <button type="submit" form="move-room-form" className="btn btn-sm btn-primary" disabled={saving || !roomId}>{saving ? 'Moving...' : 'Move'}</button>
        </div>
      }
    >
      <form id="move-room-form" onSubmit={(e) => { e.preventDefault(); handleSave() }}>
        <p style={{ marginBottom: 12, fontSize: 'var(--font-size-sm)' }}>
          Current room: <strong>{item.roomName}</strong> ({item.floorName})
        </p>
        <div className="form-row">
          <div className="form-group">
            <label>Floor</label>
            <select className="form-input" value={floorId} onChange={e => setFloorId(e.target.value)}>
              <option value="">Select floor...</option>
              {floors.map(f => <option key={f._id} value={f._id}>{f.floorName}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Room</label>
            <select className="form-input" value={roomId} onChange={e => setRoomId(e.target.value)} disabled={!floorId}>
              <option value="">Select room...</option>
              {localRooms.map(r => <option key={r._id} value={r._id}>{r.roomName}</option>)}
            </select>
          </div>
        </div>
      </form>
    </Modal>
  )
}

function MoveDepartmentModal({ open, item, onClose, onSaved }: {
  open: boolean; item: ItemReport
  onClose: () => void; onSaved: () => void
}) {
  const [departments, setDepartments] = useState<Department[]>([])
  const [floors, setFloors] = useState<Floor[]>([])
  const [rooms, setRooms] = useState<Room[]>([])
  const [departmentId, setDepartmentId] = useState('')
  const [floorId, setFloorId] = useState('')
  const [roomId, setRoomId] = useState('')
  const [saving, setSaving] = useState(false)
  const [modalError, setModalError] = useState('')

  useEffect(() => {
    if (!open) return
    setDepartmentId('')
    setFloorId('')
    setRoomId('')
    setFloors([])
    setRooms([])
    setModalError('')
    departmentsApi.list().then(r => setDepartments(r.data.data || [])).catch(() => {
      setDepartments([])
      setModalError('Could not load departments')
    })
  }, [open])

  useEffect(() => {
    if (!departmentId) return
    setFloorId('')
    setRoomId('')
    setRooms([])
    setModalError('')
    floorsApi.list(departmentId).then(r => setFloors(r.data.data || [])).catch(() => {
      setFloors([])
      setModalError('No floors are available in this department.')
    })
  }, [departmentId])

  useEffect(() => {
    if (!floorId) return
    setRoomId('')
    setModalError('')
    roomsApi.floorFilter(floorId, '1').then(r => {
      setRooms(r.data.data.rooms || [])
    }).catch(() => {
      setRooms([])
      setModalError('No rooms are available on this floor.')
    })
  }, [floorId])

  const handleSave = async () => {
    if (!departmentId || !roomId) return
    setSaving(true)
    try {
      await itemsApi.moveDepartment(item._id, departmentId, roomId)
      onSaved()
    } catch (err: unknown) {
      setModalError(apiErrorMessage(err, 'Move failed'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal open={open} title="Move Item to Department" onClose={onClose}
      footer={
        <div className="btn-group">
          <button type="button" className="btn btn-sm" onClick={onClose}>Cancel</button>
          <button type="submit" form="move-department-form" className="btn btn-sm btn-primary" disabled={saving || !roomId}>
            {saving ? 'Moving...' : 'Move'}
          </button>
        </div>
      }
    >
      <Alert type="error" message={modalError} onDismiss={() => setModalError('')} />
      <form id="move-department-form" onSubmit={(e) => { e.preventDefault(); handleSave() }}>
        <p style={{ marginBottom: 12, fontSize: 'var(--font-size-sm)' }}>
          Current department: <strong>{item.departmentName || 'Unassigned'}</strong>
        </p>
        <div className="form-row">
          <div className="form-group">
            <label>Department</label>
            <select className="form-input" value={departmentId} onChange={e => setDepartmentId(e.target.value)}>
              <option value="">Select department...</option>
              {departments.map(department => <option key={department._id} value={department._id}>{department.departmentName}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Floor</label>
            <select className="form-input" value={floorId} onChange={e => setFloorId(e.target.value)} disabled={!departmentId}>
              <option value="">Select floor...</option>
              {floors.map(floor => <option key={floor._id} value={floor._id}>{floor.floorName}</option>)}
            </select>
          </div>
        </div>
        <div className="form-group">
          <label>Room</label>
          <select className="form-input" value={roomId} onChange={e => setRoomId(e.target.value)} disabled={!floorId}>
            <option value="">Select room...</option>
            {rooms.map(room => <option key={room._id} value={room._id}>{room.roomName}</option>)}
          </select>
        </div>
      </form>
    </Modal>
  )
}
