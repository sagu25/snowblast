const CX = 320
const CY = 280

function polar(r, angle) {
  return [CX + r * Math.sin(angle), CY - r * Math.cos(angle)]
}

// Spread n items across a near-full circle, starting at the top and
// leaving a small gap on the lower-left where the ring labels sit on
// the horizontal axis line.
function angleFor(i, total) {
  const gap = Math.PI * 0.22
  const span = Math.PI * 2 - gap
  const start = -Math.PI / 2 - span / 2
  return total <= 1 ? -Math.PI / 2 : start + (i / (total - 1)) * span
}

function Node({ x, y, r, color, label, sub, excluded }) {
  return (
    <g className="gnode">
      <circle cx={x} cy={y} r={r + 4} fill="none" stroke={color} strokeWidth="1" opacity={excluded ? 0.15 : 0.35} />
      <circle className="dot" cx={x} cy={y} r={r} fill={color} opacity={excluded ? 0.4 : 1} />
      {excluded && (
        <>
          <line className="excl-x" x1={x - r * 0.7} y1={y - r * 0.7} x2={x + r * 0.7} y2={y + r * 0.7} />
          <line className="excl-x" x1={x - r * 0.7} y1={y + r * 0.7} x2={x + r * 0.7} y2={y - r * 0.7} />
        </>
      )}
      <text className="lbl" x={x} y={y + r + 13}>{label}</text>
      {sub && <text className="sub" x={x} y={y + r + 23}>{sub}</text>}
    </g>
  )
}

export default function RadialView({ assessment }) {
  const { direct, excluded, likely_apps: likelyApps, possible, trigger } = assessment
  const directR = 80
  const likelyR = 145
  const possibleR = 210

  const directAll = [...direct, ...excluded]
  const possibleItems = [possible.who, ...possible.locations, possible.reach].filter(Boolean)

  return (
    <div className="radial-wrap">
      <div className="legend">
        <span><i style={{ background: 'var(--bad)' }} />Direct</span>
        <span><i style={{ background: 'var(--amber)' }} />Likely</span>
        <span><i style={{ background: 'var(--blue)' }} />Possible</span>
      </div>
      <svg viewBox="0 0 640 560" style={{ maxWidth: '100%', height: 'auto' }}>
        <circle cx={CX} cy={CY} r={possibleR} fill="none" stroke="var(--blue)" strokeWidth="1.2" opacity="0.45" />
        <circle cx={CX} cy={CY} r={likelyR} fill="none" stroke="var(--amber)" strokeWidth="1.2" opacity="0.45" />
        <circle cx={CX} cy={CY} r={directR} fill="none" stroke="var(--bad)" strokeWidth="1.4" opacity="0.55" />

        <line className="axis-line" x1={CX - possibleR} y1={CY} x2={CX + possibleR} y2={CY} />

        {['DIRECT', 'LIKELY', 'POSSIBLE'].map((label, i) => {
          const r = [directR, likelyR, possibleR][i]
          return (
            <text key={label} className="ring-label" x={CX - r + 2} y={CY - 8}>
              {label}
            </text>
          )
        })}

        <circle className="pulse" cx={CX} cy={CY} r={8} fill="none" stroke="var(--cyan)" strokeWidth="2" />
        <circle cx={CX} cy={CY} r={16} fill="none" stroke="var(--cyan)" strokeWidth="1" opacity="0.4" />
        <Node x={CX} y={CY} r={14} color="var(--cyan)" label={trigger.number} sub="CURRENT" />

        {directAll.map((m, i) => {
          const angle = angleFor(i, Math.max(directAll.length, 1))
          const [x, y] = polar(directR, angle)
          const isExcluded = m.reason !== undefined
          return (
            <Node
              key={m.incident.number}
              x={x}
              y={y}
              r={10}
              color="var(--bad)"
              label={m.incident.number}
              sub={isExcluded ? 'excluded' : m.incident.short_description.slice(0, 20) + '…'}
              excluded={isExcluded}
            />
          )
        })}

        {likelyApps.map((app, i) => {
          const angle = angleFor(i, Math.max(likelyApps.length, 1))
          const [x, y] = polar(likelyR, angle)
          return <Node key={app} x={x} y={y} r={9} color="var(--amber)" label={app} sub="capability" />
        })}

        {possibleItems.map((item, i) => {
          const angle = angleFor(i, possibleItems.length)
          const [x, y] = polar(possibleR, angle)
          return <Node key={item + i} x={x} y={y} r={8} color="var(--blue)" label={item} />
        })}
      </svg>
    </div>
  )
}
