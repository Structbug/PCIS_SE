import { useEffect, useState } from 'react'
import { floorsApi } from '../../api/floors'
import { Table, Modal, Alert } from '../../components/ui'
import { useAuth } from '../../hooks/useAuth'
import type { Floor } from '../../types'

export default function FloorList({ departmentId, compact = false }: { departmentId?: string; compact?: boolean }) {
  const { isAdmin } = useAuth()
  const [floors, setFloors] = useState<Floor[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [modal, setModal] = useState(false)
  const [editItem, setEditItem] = useState<Floor | null>(null)
  const [deleteItem, setDeleteItem] = useState<Floor | null>(null)
  const [name, setName] = useState('')
  const [saving, setSaving] = useState(false)

  const load = () => {
    setLoading(true)
    floorsApi.list(departmentId).then(r => setFloors(r.data.data || [])).catch(() => setFloors([])).finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [departmentId])

  const handleSave = async () => {
    if (!name) return
    setSaving(true)
    try {
      if (editItem) { await floorsApi.update(editItem._id, { floorName: name, departmentId }); setMessage('Floor updated') }
      else { await floorsApi.create({ floorName: name, departmentId }); setMessage('Floor created') }
      setModal(false); setEditItem(null); load()
    } catch { setError('Save failed') }
    finally { setSaving(false) }
  }

  const handleDelete = async () => {
    if (!deleteItem) return
    try { await floorsApi.delete(deleteItem._id); setMessage('Floor deactivated'); setDeleteItem(null); load() }
    catch { setError('Delete failed') }
  }

  return (
    <div>
      <Alert type="error" message={error} onDismiss={() => setError('')} />
      <Alert type="success" message={message} onDismiss={() => setMessage('')} />
      <div className="flex-between mb-16">
        <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--font-size-xl)' }}>{compact ? 'Floors in this department' : 'Floors'}</h3>
        {isAdmin && <button className="btn btn-sm btn-primary" onClick={() => { setEditItem(null); setName(''); setModal(true) }}>+ New Floor</button>}
      </div>
      {loading ? <p>Loading...</p> : (
        <Table
          columns={[
            { key: 'floorName', label: 'Floor Name', render: (f: Floor) => <strong>{f.floorName}</strong> },
            ...(isAdmin ? [{
              key: 'actions' as string, label: '',
              render: (f: Floor) => (
                <div className="btn-group">
                  <button className="btn btn-sm" onClick={(e) => { e.stopPropagation(); setEditItem(f); setName(f.floorName); setModal(true) }}>Edit</button>
                  <button className="btn btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteItem(f) }}>Delete</button>
                </div>
              ),
            }] : []),
          ]}
          data={floors}
          keyExtractor={(f: Floor) => f._id}
          emptyMessage="No floors"
        />
      )}

      <Modal open={modal} title={editItem ? 'Edit Floor' : 'New Floor'} onClose={() => { setModal(false); setEditItem(null) }}
        footer={
          <div className="btn-group">
            <button type="button" className="btn btn-sm" onClick={() => { setModal(false); setEditItem(null) }}>Cancel</button>
            <button type="submit" form="floor-form" className="btn btn-sm btn-primary" disabled={saving}>{saving ? 'Saving...' : 'Save'}</button>
          </div>
        }
      >
        <form id="floor-form" onSubmit={(e) => { e.preventDefault(); handleSave() }}>
          <div className="form-group">
            <label>Floor Name</label>
            <input className="form-input" value={name} onChange={e => setName(e.target.value)} />
          </div>
        </form>
      </Modal>

      <Modal open={!!deleteItem} title="Deactivate Floor" onClose={() => setDeleteItem(null)}
        footer={
          <div className="btn-group">
            <button className="btn btn-sm" onClick={() => setDeleteItem(null)}>Cancel</button>
            <button className="btn btn-sm btn-danger" onClick={handleDelete}>Deactivate</button>
          </div>
        }
      >
        <p>Deactivate floor <strong>{deleteItem?.floorName}</strong>?</p>
      </Modal>
    </div>
  )
}
