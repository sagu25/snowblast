export default function StatsRow({ assessment }) {
  const connected = assessment.direct.length + assessment.excluded.length
  const locations = assessment.possible.locations.length

  return (
    <div className="stats-row">
      <div className="stat-card">
        <div className="stat-label">Connected incidents</div>
        <div className="stat-value">{connected}</div>
        <div className="stat-sub">potential cluster</div>
      </div>
      <div className="stat-card">
        <div className="stat-label">Capabilities</div>
        <div className="stat-value">{assessment.likely_apps.length}</div>
        <div className="stat-sub">likely impact</div>
      </div>
      <div className="stat-card">
        <div className="stat-label">Locations</div>
        <div className="stat-value">{locations}</div>
        <div className="stat-sub">reported reach</div>
      </div>
      <div className="stat-card">
        <div className="stat-label">People / customers</div>
        <div className="stat-value wide">{assessment.possible.who}</div>
        <div className="stat-sub">impact category</div>
      </div>
      <div className="stat-card">
        <div className="stat-label">False positives</div>
        <div className="stat-value">{assessment.excluded.length}</div>
        <div className="stat-sub">excluded</div>
      </div>
      <div className="stat-card">
        <div className="stat-label">Confidence</div>
        <div className="stat-value good">{assessment.confidence}%</div>
        <div className="stat-sub">human validation</div>
      </div>
    </div>
  )
}
