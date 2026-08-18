import { useEffect, useState } from 'react'
import { categoriesApi } from '../../api/categories'
import { Alert, Modal, Table } from '../../components/ui'
import { useAuth } from '../../hooks/useAuth'
import type { Category } from '../../types'

export default function CategoryList() {
  const { isAdmin } = useAuth()
  const [categories, setCategories] = useState<Category[]>([])
  const [name, setName] = useState('')
  const [editItem, setEditItem] = useState<Category | null>(null)
  const [deleteItem, setDeleteItem] = useState<Category | null>(null)
  const [modal, setModal] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const load = () => {
    setLoading(true)
    categoriesApi.list().then(r => setCategories(r.data.data || [])
    ).catch(() => setCategories([])).finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  const save = async () => {
    if (!name.trim()) return
    setSaving(true)
    try {
      if (editItem) {
        await categoriesApi.update(editItem._id, { categoryName: name })
        setMessage('Category updated')
      } else {
        await categoriesApi.create({ categoryName: name })
        setMessage('Category created')
      }
      setModal(false); setEditItem(null); load()
    } catch { setError('Save failed') } finally { setSaving(false) }
  }

  const remove = async () => {
    if (!deleteItem) return
    try {
      await categoriesApi.delete(deleteItem._id)
      setMessage('Category deactivated'); setDeleteItem(null); load()
    } catch { setError('Delete failed. Remove or reassign its references first.') }
  }

  return <div>
    <Alert type="error" message={error} onDismiss={() => setError('')} />
    <Alert type="success" message={message} onDismiss={() => setMessage('')} />
    <div className="flex-between mb-16">
      <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: 'var(--font-size-xl)' }}>Categories</h3>
      {isAdmin && <button className="btn btn-sm btn-primary" onClick={() => { setEditItem(null); setName(''); setModal(true) }}>+ New Category</button>}
    </div>
    {loading ? <p>Loading...</p> : <Table
      columns={[
        { key: 'categoryName', label: 'Category', render: (c: Category) => <strong>{c.categoryName}</strong> },
        ...(isAdmin ? [{ key: 'actions' as string, label: '', render: (c: Category) => <div className="btn-group">
          <button className="btn btn-sm" onClick={(e) => { e.stopPropagation(); setEditItem(c); setName(c.categoryName); setModal(true) }}>Edit</button>
          <button className="btn btn-sm btn-danger" onClick={(e) => { e.stopPropagation(); setDeleteItem(c) }}>Delete</button>
        </div> }] : []),
      ]}
      data={categories} keyExtractor={(c: Category) => c._id} emptyMessage="No categories"
    />}
    <Modal open={modal} title={editItem ? 'Edit Category' : 'New Category'} onClose={() => { setModal(false); setEditItem(null) }} footer={<div className="btn-group"><button type="button" className="btn btn-sm" onClick={() => setModal(false)}>Cancel</button><button type="submit" form="category-form" className="btn btn-sm btn-primary" disabled={saving}>{saving ? 'Saving...' : 'Save'}</button></div>}>
      <form id="category-form" onSubmit={(e) => { e.preventDefault(); save() }}>
        <div className="form-group"><label>Category name</label><input className="form-input" value={name} onChange={e => setName(e.target.value)} /></div>
      </form>
    </Modal>
    <Modal open={!!deleteItem} title="Deactivate Category" onClose={() => setDeleteItem(null)} footer={<div className="btn-group"><button className="btn btn-sm" onClick={() => setDeleteItem(null)}>Cancel</button><button className="btn btn-sm btn-danger" onClick={remove}>Deactivate</button></div>}>
      <p>Deactivate category <strong>{deleteItem?.categoryName}</strong>?</p>
    </Modal>
  </div>
}