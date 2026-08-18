import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { itemsApi } from '../../api/items'
import { apiErrorMessage } from '../../api/errors'
import { floorsApi } from '../../api/floors'
import { roomsApi } from '../../api/rooms'
import { departmentsApi } from '../../api/departments'
import { categoriesApi } from '../../api/categories'
import { Alert } from '../../components/ui'
import { useAuth } from '../../hooks/useAuth'
import type { Category, Department, Floor, Room } from '../../types'

export default function ItemCreate() {
  const nav = useNavigate()
  const { isAdmin } = useAuth()

  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')
  const [model, setModel] = useState('')
  const [serial, setSerial] = useState('')
  const [source, setSource] = useState('Purchase')
  const [quantity, setQuantity] = useState('1')
  const [acquired, setAcquired] = useState('')
  const [status, setStatus] = useState('Working')
  const [floorId, setFloorId] = useState('')
  const [departmentId, setDepartmentId] = useState('')
  const [roomId, setRoomId] = useState('')
  const [categoryId, setCategoryId] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const [floors, setFloors] = useState<Floor[]>([])
  const [departments, setDepartments] = useState<Department[]>([])
  const [rooms, setRooms] = useState<Room[]>([])
  const [categories, setCategories] = useState<Category[]>([])

  useEffect(() => {
    departmentsApi.list().then(d => setDepartments(d.data.data || [])).catch(() => setDepartments([]))
  }, [])

  useEffect(() => {
    categoriesApi.list().then(c => setCategories(c.data.data || [])).catch(() => setCategories([]))
  }, [])

  useEffect(() => {
    floorsApi.list(departmentId).then(f => setFloors(f.data.data || [])).catch(() => setFloors([]))
  }, [departmentId])

  useEffect(() => {
    if (floorId) roomsApi.floorFilter(floorId, '1').then(r => setRooms(r.data.data?.rooms || [])).catch(() => setRooms([]))
    else setRooms([])
  }, [floorId])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!name || !floorId || !roomId) {
      setError('Name, Floor, and Room are required')
      return
    }
    const count = parseInt(quantity, 10)
    if (!count || count < 1 || count > 100) {
      setError('Quantity must be between 1 and 100')
      return
    }
    setSaving(true)
    setError('')
    try {
      const res = await itemsApi.create({
        itemName: name, itemDescription: desc, itemModelNumberOrMake: model,
        itemSerialNumber: serial, itemSource: source,
        itemAcquiredDate: acquired || undefined, itemStatus: status,
        itemFloor: floorId, itemRoom: roomId,
        itemCategory: categoryId || undefined,
        item_create_count: count,
      })
      if (count === 1) {
        nav(`/items/${res.data.data[0]._id}`)
      } else {
        nav('/items')
      }
    } catch (err: unknown) {
      setError(apiErrorMessage(err, 'Create failed'))
    } finally { setSaving(false) }
  }

  if (!isAdmin) return <Alert type="error" message="Only administrators can create items." />

  return (
    <div>
      <h2 style={{ fontFamily: 'var(--font-heading)', marginBottom: 16 }}>New Item Record</h2>
      <Alert type="error" message={error} onDismiss={() => setError('')} />
      <form onSubmit={handleSubmit} style={{ maxWidth: 600 }}>
        <div className="form-row">
          <div className="form-group">
            <label>Department *</label>
            <select className="form-input" value={departmentId} onChange={e => { setDepartmentId(e.target.value); setFloorId(''); setRoomId('') }} required>
              <option value="">Select department...</option>
              {departments.map(d => <option key={d._id} value={d._id}>{d.departmentName}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Category</label>
            <select className="form-input" value={categoryId} onChange={e => setCategoryId(e.target.value)}>
              <option value="">Select category...</option>
              {categories.map(c => <option key={c._id} value={c._id}>{c.categoryName}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Item Name *</label>
            <input className="form-input" value={name} onChange={e => setName(e.target.value)} required />
          </div>
        </div>
        <div className="form-row">
          <div className="form-group">
            <label>Serial Number</label>
            <input className="form-input" value={serial} onChange={e => setSerial(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Model / Make</label>
            <input className="form-input" value={model} onChange={e => setModel(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Source *</label>
            <select className="form-input" value={source} onChange={e => setSource(e.target.value)}>
              <option value="Purchase">Purchase</option>
              <option value="Donation">Donation</option>
            </select>
          </div>
        </div>
        <div className="form-row">
          <div className="form-group">
            <label>Quantity *</label>
            <input className="form-input" type="number" min={1} max={100} value={quantity} onChange={e => setQuantity(e.target.value)} />
          </div>
          <div className="form-group">
            <label>Acquired Date</label>
            <input className="form-input" type="date" value={acquired} onChange={e => setAcquired(e.target.value)} />
          </div>
        </div>
        <div className="form-group">
          <label>Description</label>
          <textarea className="form-input" value={desc} onChange={e => setDesc(e.target.value)} />
        </div>
        <div className="form-row">
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
            <label>Floor *</label>
            <select className="form-input" value={floorId} onChange={e => { setFloorId(e.target.value); setRoomId('') }} required disabled={!departmentId}>
              <option value="">Select floor...</option>
              {floors.map(f => <option key={f._id} value={f._id}>{f.floorName}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Room *</label>
            <select className="form-input" value={roomId} onChange={e => setRoomId(e.target.value)} required disabled={!floorId}>
              <option value="">Select room...</option>
              {rooms.map(r => <option key={r._id} value={r._id}>{r.roomName}</option>)}
            </select>
          </div>
        </div>
        <div className="btn-group mt-16">
          <button type="submit" className="btn btn-primary" disabled={saving}>{saving ? 'Creating...' : 'Create Item'}</button>
          <button type="button" className="btn" onClick={() => nav('/items')}>Cancel</button>
        </div>
      </form>
    </div>
  )
}
