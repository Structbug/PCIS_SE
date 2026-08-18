import { useEffect, useState } from 'react'
import { departmentsApi } from '../../api/departments'
import { Alert, Modal, Table } from '../../components/ui'
import { useAuth } from '../../hooks/useAuth'
import type { Department } from '../../types'
import FloorList from '../Floors/FloorList'
import RoomTypeList from '../RoomTypes/RoomTypeList'

export default function DepartmentList() {
  const { isAdmin } = useAuth()
  const [departments, setDepartments] = useState<Department[]>([])
  const [selected, setSelected] = useState<Department | null>(null)
  const [name, setName] = useState('')
  const [editItem, setEditItem] = useState<Department | null>(null)
  const [deleteItem, setDeleteItem] = useState<Department | null>(null)
  const [modal, setModal] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const load = () => {
    setLoading(true)
    departmentsApi.list().then(r => setDepartments(r.data.data || [])
    ).catch(() => setDepartments([])).finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  const save = async () => {
    if (!name.trim()) return
    setSaving(true)
    try {
      if (editItem) {
        const response = await departmentsApi.update(editItem._id, { departmentName: name })
        setSelected(current => current?._id === editItem._id ? response.data.data : current)
        setMessage('Department updated')
      } else {
        const response = await departmentsApi.create({ departmentName: name })
        setSelected(response.data.data)
        setMessage('Department created')
      }
      setModal(false); setEditItem(null); load()
    } catch { setError('Save failed') } finally { setSaving(false) }
  }

  const remove = async () => {
    if (!deleteItem) return
    try {
      await departmentsApi.delete(deleteItem._id)
      if (selected?._id === deleteItem._id) setSelected(null)
      setMessage('Department deactivated'); setDeleteItem(null); load()
    } catch { setError('Delete failed. Remove or reassign its references first.') }
  }

  return <div>
    <Alert type="error" message={error} onDismiss={() => setError('')} />
    <Alert type="success" message={message} onDismiss={() => setMessage('')} />
    <div className="flex-between mb-16">
      <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--font-size-xl)' }}>Departments</h3>
      {isAdmin && <button className="btn btn-sm btn-primary" onClick={() => { setEditItem(null); setName(''); setModal(true) }}>+ New Department</button>}
    </div>
    {loading ? <p>Loading...</p> : <Table
      columns={[
        { key: 'departmentName', label: 'Department', render: (d: Department) => <strong>{d.departmentName}</strong> },
        ...(isAdmin ? [{ key: 'actions' as string, label: '', render: (d: Department) => <div className="btn-group">
          <button className="btn btn-sm" onClick={(e) => { e.stopPropagation(); setEditItem(d); setName(d.departmentName); setModal(true) }}>Edit</button>
          <button className="btn btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteItem(d) }}>Delete</button>
        </div> }] : []),
      ]}
      data={departments} keyExtractor={(d: Department) => d._id}
      onRowClick={(d: Department) => setSelected(d)} emptyMessage="No departments"
    />}
    {selected && <div style={{ marginTop: 28 }}>
      <h4 style={{ fontFamily: 'var(--font-heading)' }}>Department: {selected.departmentName}</h4>
      {isAdmin && <p style={{ color: 'var(--text-muted)', marginTop: 4 }}>Manage the floors and room types available to this department.</p>}
      <div className="form-row" style={{ alignItems: 'flex-start', marginTop: 16 }}>
        <div style={{ flex: 1 }}><FloorList departmentId={selected._id} compact /></div>
        <div style={{ flex: 1 }}><RoomTypeList departmentId={selected._id} compact /></div>
      </div>
    </div>}
    <Modal open={modal} title={editItem ? 'Edit Department' : 'New Department'} onClose={() => { setModal(false); setEditItem(null) }} footer={<div className="btn-group"><button type="button" className="btn btn-sm" onClick={() => setModal(false)}>Cancel</button><button type="submit" form="department-form" className="btn btn-sm btn-primary" disabled={saving}>{saving ? 'Saving...' : 'Save'}</button></div>}>
      <form id="department-form" onSubmit={(e) => { e.preventDefault(); save() }}>
        <div className="form-group"><label>Department name</label><input className="form-input" value={name} onChange={e => setName(e.target.value)} /></div>
      </form>
    </Modal>
    <Modal open={!!deleteItem} title="Deactivate Department" onClose={() => setDeleteItem(null)} footer={<div className="btn-group"><button className="btn btn-sm" onClick={() => setDeleteItem(null)}>Cancel</button><button className="btn btn-sm btn-danger" onClick={remove}>Deactivate</button></div>}>
      <p>Deactivate department <strong>{deleteItem?.departmentName}</strong>? Its existing floors and room types will remain available as legacy references.</p>
    </Modal>
  </div>
}
