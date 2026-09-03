export default function LeftPane({ assessment }) {
  if (!assessment) {
    return (
      <div className="pane left">
        <div className="card-label">Triggering incident</div>
        <div className="card" style={{ color: 'var(--text-3)', fontSize: 12 }}>
          Look up an incident number above to begin.
        </div>
      </div>
    )
  }

  const t = assessment.trigger

  return (
    <div className="pane left">
      <div className="card-label">Triggering incident</div>
      <div className="card">
        <span className="inc-number">{t.number}</span>
        <div className="inc-title">{t.short_description}</div>
        <div style={{ marginTop: 10 }}>
          <div className="kv"><span className="k">Location</span><span className="v">{t.location || '—'}</span></div>
        </div>
      </div>
      <div className="card-label">Evidence checked</div>
      <div className="card">
        {assessment.sources_checked.map((src) => (
          <div className="src-item" key={src}><span className="src-dot" />{src}</div>
        ))}
        <div className="src-item" style={{ opacity: 0.4 }}>
          <span className="src-dot" style={{ background: 'var(--text-3)' }} />Problem records (not yet wired)
        </div>
        <div className="src-item" style={{ opacity: 0.4 }}>
          <span className="src-dot" style={{ background: 'var(--text-3)' }} />Change records (not yet wired)
        </div>
      </div>
    </div>
  )
}
