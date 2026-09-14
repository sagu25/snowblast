const CX = 280
const CY = 280
const R = 165

export default function CiGraphView({ graph, onSelect }) {
  const others = graph.nodes.filter((n) => n.id !== graph.root)
  const positions = { [graph.root]: [CX, CY] }
  others.forEach((n, i) => {
    const angle = (i / Math.max(others.length, 1)) * Math.PI * 2 - Math.PI / 2
    positions[n.id] = [CX + R * Math.sin(angle), CY - R * Math.cos(angle)]
  })

  return (
    <div className="ci-graph-wrap">
      <div className="legend">
        <span><i style={{ background: 'var(--accent)' }} />Selected CI</span>
        <span><i style={{ background: 'var(--cyan)' }} />Related CI</span>
      </div>
      <svg viewBox="0 0 560 560">
        {graph.edges.map((e, i) => {
          const [x1, y1] = positions[e.source] || [CX, CY]
          const [x2, y2] = positions[e.target] || [CX, CY]
          const mx = (x1 + x2) / 2
          const my = (y1 + y2) / 2
          return (
            <g key={i}>
              <line className="ci-edge" x1={x1} y1={y1} x2={x2} y2={y2} />
              <text className="ci-edge-label" x={mx} y={my - 4}>{e.label}</text>
            </g>
          )
        })}

        {graph.nodes.map((n) => {
          const [x, y] = positions[n.id]
          const r = n.root ? 16 : 11
          return (
            <g
              key={n.id}
              className={'ci-node' + (n.root ? ' root' : '')}
              onClick={() => onSelect(n.id)}
              style={{ cursor: n.root ? 'default' : 'pointer' }}
            >
              <circle cx={x} cy={y} r={r + 4} fill="none" stroke={n.root ? 'var(--accent)' : 'var(--cyan)'} strokeWidth="1" opacity="0.35" />
              <circle cx={x} cy={y} r={r} />
              <text className="lbl" x={x} y={y + r + 14}>{n.label}</text>
              {n.type && <text className="cls" x={x} y={y + r + 25}>{n.type}</text>}
            </g>
          )
        })}
      </svg>
    </div>
  )
}
