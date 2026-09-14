const CX = 320
const CY = 280
const LEFT = -Math.PI / 2 // angle pointing left, where the DIRECT/LIKELY/POSSIBLE axis labels sit
const LABEL_GAP = Math.PI * 0.34 // keep nodes clear of the axis label text
// distinct fallback angles per ring so a lone direct incident, lone
// capability, and lone possible-impact item don't all stack on one ray
const LONE_DIRECT = LEFT + Math.PI
const LONE_LIKELY = LEFT + Math.PI - Math.PI * 0.3
const LONE_POSSIBLE = LEFT + Math.PI + Math.PI * 0.3

function polar(r, angle) {
  return [CX + r * Math.sin(angle), CY - r * Math.cos(angle)]
}

// Spread n items across the circle, skipping the wedge on the left where
// the ring labels sit on the horizontal axis line, so node labels never
// collide with "DIRECT" / "LIKELY" / "POSSIBLE". `loneAngle` lets each ring
// send its single-item case somewhere different, so e.g. one direct
// incident and one likely capability don't both land on the same ray and
// crowd each other's labels.
function angleFor(i, total, loneAngle = LEFT + Math.PI) {
  if (total <= 1) return loneAngle
  const start = LEFT + LABEL_GAP / 2
  const span = Math.PI * 2 - LABEL_GAP
  return start + (i / (total - 1)) * span
}

function Spoke({ x, y, color, delay }) {
  const pathId = `spoke-${x.toFixed(1)}-${y.toFixed(1)}`
  return (
    <g>
      <path id={pathId} d={`M${CX},${CY} L${x},${y}`} className="spoke-line" />
      <circle r="3" fill={color} className="spoke-pulse">
        <animateMotion dur="2.4s" begin={`${delay}s`} repeatCount="indefinite" rotate="auto">
          <mpath href={`#${pathId}`} xlinkHref={`#${pathId}`} />
        </animateMotion>
        <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;0.1;0.85;1" dur="2.4s" begin={`${delay}s`} repeatCount="indefinite" />
      </circle>
    </g>
  )
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
      <text className="lbl" x={x} y={y + r + 15}>{label}</text>
      {sub && <text className="sub" x={x} y={y + r + 27}>{sub}</text>}
    </g>
  )
}

export default function RadialView({ assessment }) {
  const { direct, excluded, likely_apps: likelyApps, possible, trigger } = assessment
  const directR = 85
  const likelyR = 150
  const possibleR = 215

  const directAll = [...direct, ...excluded]
  const possibleItems = [possible.who, ...possible.locations, possible.reach].filter(Boolean)

  const spokes = []
  let delayCounter = 0
  const nextDelay = () => {
    const d = (delayCounter % 8) * 0.3
    delayCounter += 1
    return d
  }

  directAll.forEach((m, i) => {
    const [x, y] = polar(directR, angleFor(i, Math.max(directAll.length, 1), LONE_DIRECT))
    spokes.push(<Spoke key={'s-' + m.incident.number} x={x} y={y} color="var(--bad)" delay={nextDelay()} />)
  })
  likelyApps.forEach((app, i) => {
    const [x, y] = polar(likelyR, angleFor(i, Math.max(likelyApps.length, 1), LONE_LIKELY))
    spokes.push(<Spoke key={'s-' + app} x={x} y={y} color="var(--amber)" delay={nextDelay()} />)
  })
  possibleItems.forEach((item, i) => {
    const [x, y] = polar(possibleR, angleFor(i, possibleItems.length, LONE_POSSIBLE))
    spokes.push(<Spoke key={'s-' + item + i} x={x} y={y} color="var(--blue)" delay={nextDelay()} />)
  })

  return (
    <div className="radial-wrap">
      <div className="legend">
        <span><i style={{ background: 'var(--bad)' }} />Direct</span>
        <span><i style={{ background: 'var(--amber)' }} />Likely</span>
        <span><i style={{ background: 'var(--blue)' }} />Possible</span>
      </div>
      <svg viewBox="0 0 640 560">
        <circle className="ring-breathe" cx={CX} cy={CY} r={possibleR} fill="none" stroke="var(--blue)" strokeWidth="1.4" opacity="0.45" />
        <circle className="ring-breathe" style={{ animationDelay: '0.6s' }} cx={CX} cy={CY} r={likelyR} fill="none" stroke="var(--amber)" strokeWidth="1.4" opacity="0.45" />
        <circle className="ring-breathe" style={{ animationDelay: '1.2s' }} cx={CX} cy={CY} r={directR} fill="none" stroke="var(--bad)" strokeWidth="1.6" opacity="0.55" />

        <line className="axis-line" x1={CX - possibleR} y1={CY} x2={CX + possibleR} y2={CY} />

        {spokes}

        {['DIRECT', 'LIKELY', 'POSSIBLE'].map((label, i) => {
          const r = [directR, likelyR, possibleR][i]
          return (
            <text key={label} className="ring-label" x={CX - r} y={CY - 10}>
              {label}
            </text>
          )
        })}

        <circle className="pulse" cx={CX} cy={CY} r={9} fill="none" stroke="var(--cyan)" strokeWidth="2" />
        <circle cx={CX} cy={CY} r={17} fill="none" stroke="var(--cyan)" strokeWidth="1" opacity="0.4" />
        <Node x={CX} y={CY} r={16} color="var(--cyan)" label={trigger.number} sub="CURRENT" />

        {directAll.map((m, i) => {
          const angle = angleFor(i, Math.max(directAll.length, 1), LONE_DIRECT)
          const [x, y] = polar(directR, angle)
          const isExcluded = m.reason !== undefined
          return (
            <Node
              key={m.incident.number}
              x={x}
              y={y}
              r={12}
              color="var(--bad)"
              label={m.incident.number}
              sub={isExcluded ? 'excluded' : m.incident.short_description.slice(0, 20) + '…'}
              excluded={isExcluded}
            />
          )
        })}

        {likelyApps.map((app, i) => {
          const angle = angleFor(i, Math.max(likelyApps.length, 1), LONE_LIKELY)
          const [x, y] = polar(likelyR, angle)
          return <Node key={app} x={x} y={y} r={11} color="var(--amber)" label={app} sub="capability" />
        })}

        {possibleItems.map((item, i) => {
          const angle = angleFor(i, possibleItems.length, LONE_POSSIBLE)
          const [x, y] = polar(possibleR, angle)
          return <Node key={item + i} x={x} y={y} r={10} color="var(--blue)" label={item} />
        })}
      </svg>
    </div>
  )
}
