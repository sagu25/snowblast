import { useState } from 'react'
import { getNarrative, ApiError } from '../api.js'

export default function AssessmentPanel({ assessment }) {
  const [narrative, setNarrative] = useState(null)
  const [narrateError, setNarrateError] = useState(null)
  const [narrating, setNarrating] = useState(false)

  async function handleNarrate() {
    setNarrating(true)
    setNarrateError(null)
    try {
      const { narrative } = await getNarrative(assessment.trigger.number)
      setNarrative(narrative)
    } catch (err) {
      setNarrateError(err instanceof ApiError ? err.message : 'Failed to narrate.')
    } finally {
      setNarrating(false)
    }
  }

  return (
    <div className="pane right">
      <div className="card-label">Assessment</div>
      <div className="sev-row">
        <span className="sev-badge">{assessment.cause}</span>
        <span className="mono" style={{ fontSize: 11, color: 'var(--text-2)' }}>{assessment.confidence}% confidence</span>
      </div>
      <div className="conf-track"><div className="conf-fill" style={{ width: `${assessment.confidence}%` }} /></div>
      <div className="summary-text">{assessment.summary}</div>

      {narrative && <div className="narrate-box">✦ {narrative}</div>}
      {narrateError && <div className="inline-error">{narrateError}</div>}
      {!narrative && (
        <button className="btn" style={{ width: '100%', marginBottom: 14 }} onClick={handleNarrate} disabled={narrating}>
          {narrating ? 'Narrating…' : '✦ Narrate in plain language'}
        </button>
      )}

      {assessment.direct.length > 0 && (
        <>
          <div className="card-label">Direct cluster</div>
          {assessment.direct.map((m) => (
            <div className="match-item" key={m.incident.number}>
              <div className="match-head"><span>{m.incident.number}</span><span className="sc">{m.score.toFixed(2)}</span></div>
              <div className="match-desc">{m.incident.short_description}</div>
              <div className="match-reasons">{m.reasons.join(' · ')}</div>
            </div>
          ))}
        </>
      )}

      {assessment.excluded.length > 0 && (
        <>
          <div className="card-label">Excluded (false positive)</div>
          {assessment.excluded.map((m) => (
            <div className="match-item excl-item" key={m.incident.number}>
              <div className="match-head"><span>{m.incident.number}</span></div>
              <div className="match-desc">{m.incident.short_description}</div>
              <div className="match-reasons">{m.reason}</div>
            </div>
          ))}
        </>
      )}

      {assessment.likely_apps.length > 0 && (
        <>
          <div className="card-label">Likely capabilities</div>
          <div className="card" style={{ padding: '10px 12px', fontSize: 11.5 }}>{assessment.likely_apps.join(', ')}</div>
        </>
      )}

      <div className="card-label">Possible impact</div>
      <div className="card">
        <div className="kv"><span className="k">Locations</span><span className="v">{assessment.possible.locations.join(', ') || '—'}</span></div>
        <div className="kv"><span className="k">Who</span><span className="v">{assessment.possible.who}</span></div>
        <div className="kv"><span className="k">Reach</span><span className="v">{assessment.possible.reach}</span></div>
        <div className="kv"><span className="k">Urgency</span><span className="v">{assessment.possible.urgency}</span></div>
      </div>
    </div>
  )
}
