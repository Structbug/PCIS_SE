import type { ReactNode } from 'react'

interface StatusTagProps {
  status: string
}

const statusClass: Record<string, string> = {
  Working: 'working',
  Repairable: 'repairable',
  'Not working': 'not-working',
}

export function StatusTag({ status }: StatusTagProps) {
  return (
    <span className={`status-tag ${statusClass[status] || ''}`}>
      {status}
    </span>
  )
}

// ─── Table ───

interface Column<T> {
  key: string
  label: string
  render?: (item: T) => ReactNode
  className?: string
}

interface TableProps<T> {
  columns: Column<T>[]
  data: T[]
  keyExtractor: (item: T) => string
  onRowClick?: (item: T) => void
  emptyMessage?: string
}

export function Table<T>({ columns, data, keyExtractor, onRowClick, emptyMessage }: TableProps<T>) {
  if (data.length === 0) {
    return (
      <div className="empty-state">
        <p>{emptyMessage || 'No records found'}</p>
      </div>
    )
  }

  return (
    <div className="table-container list-table-container">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col.key} className={col.className}>{col.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((item) => (
            <tr
              key={keyExtractor(item)}
              onClick={() => onRowClick?.(item)}
              style={onRowClick ? { cursor: 'pointer' } : undefined}
            >
              {columns.map((col) => (
                <td key={col.key} className={col.className}>
                  {col.render ? col.render(item) : String((item as Record<string, unknown>)[col.key] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

// ─── Pagination ───

interface PaginationProps {
  currentPage: number
  totalItems: number
  pageSize: number
  onPageChange: (page: number) => void
}

export function Pagination({ currentPage, totalItems, pageSize, onPageChange }: PaginationProps) {
  const totalPages = Math.ceil(totalItems / pageSize) || 1
  const pages: number[] = []
  for (let i = 1; i <= totalPages; i++) pages.push(i)

  return (
    <div className="flex-between">
      <div className="pagination">
        <button disabled={currentPage <= 1} onClick={() => onPageChange(currentPage - 1)}>Prev</button>
        {pages.slice(Math.max(0, currentPage - 4), currentPage + 3).map((p) => (
          <button key={p} className={p === currentPage ? 'active' : ''} onClick={() => onPageChange(p)}>
            {p}
          </button>
        ))}
        <button disabled={currentPage >= totalPages} onClick={() => onPageChange(currentPage + 1)}>Next</button>
        <span className="page-info">Page {currentPage} of {totalPages}</span>
      </div>
      <div className="record-footer">
        {totalItems} record{totalItems !== 1 ? 's' : ''} &middot; as of {new Date().toLocaleDateString()}
      </div>
    </div>
  )
}

// ─── Modal ───

interface ModalProps {
  open: boolean
  title: string
  children: ReactNode
  onClose: () => void
  footer?: ReactNode
}

export function Modal({ open, title, children, onClose, footer }: ModalProps) {
  if (!open) return null
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{title}</h3>
          <button className="btn btn-sm" onClick={onClose}>✕</button>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>
  )
}

// ─── Alert ───

interface AlertProps {
  type: 'error' | 'success'
  message: string
  onDismiss?: () => void
}

export function Alert({ type, message, onDismiss }: AlertProps) {
  if (!message) return null
  return (
    <div className={`alert alert-${type}`} role="alert">
      <span className="alert-icon" aria-hidden="true">{type === 'error' ? '!' : '✓'}</span>
      <span className="alert-message">{message}</span>
      {onDismiss && (
        <button className="alert-dismiss" type="button" onClick={onDismiss} aria-label="Dismiss message">×</button>
      )}
    </div>
  )
}
