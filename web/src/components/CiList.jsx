import { useState, useEffect } from 'react'
import { listCis, ApiError } from '../api.js'

export default function CiList({ selectedId, onSelect }) {
  const [search, setSearch] = useState('')
  const [items, setItems] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    const timer = setTimeout(() => {
      listCis(search)
        .then((data) => { if (!cancelled) setItems(data.items) })
        .catch((err) => { if (!cancelled) setError(err instanceof ApiError ? err : new Error('Unexpected error')) })
        .finally(() => { if (!cancelled) setLoading(false) })
    }, search ? 300 : 0)
    return () => { cancelled = true; clearTimeout(timer) }
  }, [search])

  return (
    <div className="ci-list">
      <div className="card-label">All configuration items</div>
      <input
        className="ci-search"
        placeholder="Search cmdb_ci by name…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      {loading && <div className="ci-list-status">Loading…</div>}

      {!loading && error && (
        <div className="ci-list-status error">
          {error.code === 'servicenow_not_configured' ? 'ServiceNow not configured yet' : 'Could not load configuration items'}
        </div>
      )}

      {!loading && !error && items && items.length === 0 && (
        <div className="ci-list-status">No configuration items found{search ? ` matching "${search}"` : ''}.</div>
      )}

      {!loading && !error && items && items.map((item) => (
        <button
          key={item.id}
          className={'ci-list-item' + (item.id === selectedId ? ' active' : '')}
          onClick={() => onSelect(item.id)}
          title={item.id === selectedId ? "Currently viewing this CI's relationships" : `View relationships for ${item.label}`}
        >
          <span className="ci-list-dot" style={{ background: item.id === selectedId ? 'var(--accent)' : 'var(--cyan)' }} />
          <span className="ci-list-text">
            <span className="ci-list-label">{item.label}</span>
            {item.type && <span className="ci-list-type">{item.type}</span>}
          </span>
          {item.id === selectedId && <span className="ci-list-tag">viewing</span>}
        </button>
      ))}
    </div>
  )
}
