import { useEffect, useState } from 'react'
import { roomTypesApi } from '../../api/roomTypes'
import { Table, Modal, Alert } from '../../components/ui'
import { useAuth } from '../../hooks/useAuth'
import type { RoomType } from '../../types'

export default function RoomTypeList({ departmentId, compact = false }: { departmentId?: string; compact?: boolean }) {
  const { isAdmin } = useAuth()
  const [types, setTypes] = useState<RoomType[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [modal, setModal] = useState(false)
  const [editItem, setEditItem] = useState<RoomType | null>(null)
  const [deleteItem, setDeleteItem] = useState<RoomType | null>(null)
  const [name, setName] = useState('')
  const [saving, setSaving] = useState(false)

  const load = () => {
    setLoading(true)
    roomTypesApi.list(departmentId).then(r => setTypes(r.data.data || [])).catch(() => setTypes([])).finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [departmentId])

  const handleSave = async () => {
    if (!name) return
    setSaving(true)
    try {
      if (editItem) { await roomTypesApi.update(editItem._id, { roomTypeName: name, departmentId }); setMessage('Room type updated') }
      else { await roomTypesApi.create({ roomTypeName: name, departmentId }); setMessage('Room type created') }
      setModal(false); setEditItem(null); load()
    } catch { setError('Save failed') }
    finally { setSaving(false) }
  }

  const handleDelete = async () => {
    if (!deleteItem) return
    try { await roomTypesApi.delete(deleteItem._id); setMessage('Room type deactivated'); setDeleteItem(null); load() }
    catch { setError('Delete failed') }
  }

  return (
    <div>
      <Alert type="error" message={error} onDismiss={() => setError('')} />
      <Alert type="success" message={message} onDismiss={() => setMessage('')} />
      <div className="flex-between mb-16">
        <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--font-size-xl)' }}>{compact ? 'Room types in this department' : 'Room Types'}</h3>
        {isAdmin && <button className="btn btn-sm btn-primary" onClick={() => { setEditItem(null); setName(''); setModal(true) }}>+ New Type</button>}
      </div>
      {loading ? <p>Loading...</p> : (
        <Table
          columns={[
            { key: 'roomTypeName', label: 'Room Type', render: (t: RoomType) => <strong>{t.roomTypeName}</strong> },
            ...(isAdmin ? [{
              key: 'actions' as string, label: '',
              render: (t: RoomType) => (
                <div className="btn-group">
                  <button className="btn btn-sm" onClick={(e) => { e.stopPropagation(); setEditItem(t); setName(t.roomTypeName); setModal(true) }}>Edit</button>
                  <button className="btn btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteItem(t) }}>Delete</button>
                </div>
              ),
            }] : []),
          ]}
          data={types}
          keyExtractor={(t: RoomType) => t._id}
          emptyMessage="No room types"
        />
      )}

      <Modal open={modal} title={editItem ? 'Edit Room Type' : 'New Room Type'} onClose={() => { setModal(false); setEditItem(null) }}
        footer={
          <div className="btn-group">
            <button type="button" className="btn btn-sm" onClick={() => { setModal(false); setEditItem(null) }}>Cancel</button>
            <button type="submit" form="roomtype-form" className="btn btn-sm btn-primary" disabled={saving}>{saving ? 'Saving...' : 'Save'}</button>
          </div>
        }
      >
        <form id="roomtype-form" onSubmit={(e) => { e.preventDefault(); handleSave() }}>
          <div className="form-group">
            <label>Room Type</label>
            <input className="form-input" value={name} onChange={e => setName(e.target.value)} />
          </div>
        </form>
      </Modal>

      <Modal open={!!deleteItem} title="Deactivate Room Type" onClose={() => setDeleteItem(null)}
        footer={
          <div className="btn-group">
            <button className="btn btn-sm" onClick={() => setDeleteItem(null)}>Cancel</button>
            <button className="btn btn-sm btn-danger" onClick={handleDelete}>Deactivate</button>
          </div>
        }
      >
        <p>Deactivate room type <strong>{deleteItem?.roomTypeName}</strong>?</p>
      </Modal>
    </div>
  )
}
