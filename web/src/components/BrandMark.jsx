export default function BrandMark({ size = 24 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 26 26">
      <circle cx="13" cy="13" r="11" stroke="var(--border)" strokeWidth="1" fill="none" />
      <circle cx="13" cy="13" r="6.5" stroke="var(--accent-wash)" strokeWidth="1.3" fill="none" />
      <circle className="bp" cx="13" cy="13" r="2.4" fill="none" stroke="var(--accent)" strokeWidth="1.6" />
      <circle cx="13" cy="13" r="2.2" fill="var(--accent)" />
    </svg>
  )
}
