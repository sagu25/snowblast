const STEPS = ['Trigger', 'Extract signals', 'Search ServiceNow', 'Form direct cluster', 'Expand likely', 'Expand possible', 'Challenge false positives', 'Analyst decision']

export default function BottomBar({ assessment }) {
  const lines = [
    'Trigger incident placed at the center of the map.',
    'Symptoms, location, timing extracted.',
    'Searched ServiceNow for incidents in the time window.',
    `Direct cluster formed: ${assessment.direct.length} incident(s).`,
    `Likely capabilities expanded: ${assessment.likely_apps.length ? assessment.likely_apps.join(', ') : 'none populated'}.`,
    `Possible impact expanded across ${assessment.possible.reach}.`,
    assessment.excluded.length ? `${assessment.excluded.length} candidate(s) excluded as false positives.` : 'No contradictory evidence found.',
    'Assessment ready for analyst review.',
  ]

  return (
    <div className="bottom">
      <div>
        <div className="card-label">How the blast radius grows</div>
        <div className="steps">
          {STEPS.map((label, i) => (
            <span className="step-chip done" key={label}>{i + 1}. {label}</span>
          ))}
        </div>
      </div>
      <div>
        <div className="card-label">Live agent narrative</div>
        <div className="log">
          {lines.map((l, i) => <div key={i}><span className="t">›</span> {l}</div>)}
        </div>
      </div>
    </div>
  )
}
