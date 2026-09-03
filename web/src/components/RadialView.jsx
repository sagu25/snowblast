const CX = 320
const CY = 280

function polar(r, angle) {
  return [CX + r * Math.sin(angle), CY - r * Math.cos(angle)]
}

function Node({ x, y, r, color, label, sub, excluded }) {
  return (
    <g className="gnode">
      <circle className="dot" cx={x} cy={y} r={r} fill={color} opacity={excluded ? 0.5 : 1} />
      {excluded && (
        <>
          <line className="excl-x" x1={x - r * 0.7} y1={y - r * 0.7} x2={x + r * 0.7} y2={y + r * 0.7} />
          <line className="excl-x" x1={x - r * 0.7} y1={y + r * 0.7} x2={x + r * 0.7} y2={y - r * 0.7} />
        </>
      )}
      <text className="lbl" x={x} y={y + r + 12}>{label}</text>
      {sub && <text className="sub" x={x} y={y + r + 22}>{sub}</text>}
    </g>
  )
}

export default function RadialView({ assessment }) {
  const { direct, excluded, likely_apps: likelyApps, possible, trigger } = assessment
  const directR = 70
  const likelyR = 130
  const possibleR = 190

  const directTotal = Math.max(direct.length + excluded.length, 1)
  const possibleItems = [...possible.locations, possible.who]

  return (
    <div className="radial-wrap">
      <div className="legend">
        <span><i style={{ background: 'var(--accent-2)' }} />Direct</span>
        <span><i style={{ background: 'var(--amber)' }} />Likely</span>
        <span><i style={{ background: 'var(--blue)' }} />Possible</span>
      </div>
      <svg viewBox="0 0 640 560" style={{ maxWidth: '100%', height: 'auto' }}>
        <circle cx={CX} cy={CY} r={possibleR} fill="none" stroke="var(--blue)" strokeWidth="1.3" opacity="0.5" />
        <circle cx={CX} cy={CY} r={likelyR} fill="none" stroke="var(--amber)" strokeWidth="1.3" opacity="0.5" />
        <circle cx={CX} cy={CY} r={directR} fill="none" stroke="var(--accent-2)" strokeWidth="1.6" opacity="0.7" />

        {['DIRECT', 'LIKELY', 'POSSIBLE'].map((label, i) => {
          const r = [directR, likelyR, possibleR][i]
          return (
            <text key={label} x={CX} y={CY - r - 6} textAnchor="middle" fontFamily="ui-monospace, monospace" fontSize="9" fill="var(--text-3)" letterSpacing="1">
              {label}
            </text>
          )
        })}

        <circle className="pulse" cx={CX} cy={CY} r={8} fill="none" stroke="var(--accent)" strokeWidth="2" />
        <Node x={CX} y={CY} r={14} color="var(--accent)" label={trigger.number} />

        {direct.map((m, i) => {
          const angle = (i / directTotal) * Math.PI * 1.4 - Math.PI * 0.7
          const [x, y] = polar(directR, angle)
          return <Node key={m.incident.number} x={x} y={y} r={10} color="var(--accent-2)" label={m.incident.number} sub={m.incident.short_description.slice(0, 22) + '…'} />
        })}
        {excluded.map((m, i) => {
          const angle = ((direct.length + i) / directTotal) * Math.PI * 1.4 - Math.PI * 0.7
          const [x, y] = polar(directR, angle)
          return <Node key={m.incident.number} x={x} y={y} r={8} color="var(--text-3)" label={m.incident.number} sub="excluded" excluded />
        })}

        {likelyApps.map((app, i) => {
          const angle = (i / Math.max(likelyApps.length, 1)) * Math.PI * 1.2 - Math.PI * 0.6
          const [x, y] = polar(likelyR, angle)
          return <Node key={app} x={x} y={y} r={8} color="var(--amber)" label={app} />
        })}

        {possibleItems.map((item, i) => {
          const angle = (i / possibleItems.length) * Math.PI * 2 - Math.PI / 2
          const [x, y] = polar(possibleR, angle)
          return <Node key={item + i} x={x} y={y} r={7} color="var(--blue)" label={item} />
        })}
      </svg>
    </div>
  )
}
