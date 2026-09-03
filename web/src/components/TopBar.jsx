import { useState } from 'react'
import BrandMark from './BrandMark.jsx'

export default function TopBar({ onLookup, loading, theme, onToggleTheme }) {
  const [number, setNumber] = useState('')
  const [hours, setHours] = useState(6)

  function submit(e) {
    e.preventDefault()
    if (number.trim()) onLookup(number.trim(), Number(hours) || 6)
  }

  return (
    <div className="topbar">
      <div className="brand">
        <BrandMark />
        Blast Radius
      </div>

      <form className="lookup-form" onSubmit={submit}>
        <input
          placeholder="Incident number, e.g. INC0010023"
          value={number}
          onChange={(e) => setNumber(e.target.value)}
        />
        <input
          className="hours"
          type="number"
          min="1"
          title="Search window (hours, each direction)"
          value={hours}
          onChange={(e) => setHours(e.target.value)}
        />
        <button className="lookup-btn" type="submit" disabled={loading || !number.trim()}>
          {loading ? 'Analyzing…' : 'Analyze'}
        </button>
      </form>

      <div className="topbar-right">
        <span className="status-pill warn">Advisory only · no auto-actions</span>
        <button className="theme-btn" onClick={onToggleTheme} title="Toggle theme">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
            <path d="M20 14.5A8.5 8.5 0 019.5 4a8.5 8.5 0 1010.5 10.5z" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>
    </div>
  )
}
