const COLORS = { Low: '#059669', Medium: '#D97706', High: '#DC2626' }

export default function RiskGauge({ riskProba = 0, riskLevel = '', size = 160 }) {
  const r    = 52
  const circ = 2 * Math.PI * r
  const arc  = 0.75
  const to   = circ * (1 - riskProba * arc)
  const col  = COLORS[riskLevel] || '#9CA3AF'
  const pct  = Math.round(riskProba * 100)

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
      {/* key forces SVG re-mount → SMIL animation restarts on each result */}
      <svg key={`${riskProba}-${riskLevel}`} width={size} height={size} viewBox="0 0 170 170">
        {/* track arc */}
        <circle cx="85" cy="85" r={r}
          fill="none" stroke="#F3F4F6" strokeWidth="10"
          strokeDasharray={`${circ * arc} ${circ * (1 - arc)}`}
          transform="rotate(135 85 85)"
        />
        {/* animated fill */}
        <circle cx="85" cy="85" r={r}
          fill="none" stroke={col} strokeWidth="9" strokeLinecap="round"
          strokeDasharray={`${circ}`} strokeDashoffset={circ}
          transform="rotate(135 85 85)"
        >
          <animate attributeName="stroke-dashoffset"
            from={circ} to={to}
            dur="1.4s" begin="0.1s" fill="freeze"
            calcMode="spline" keySplines="0.4 0 0.2 1"
          />
        </circle>
        {/* labels */}
        <text x="85" y="79" textAnchor="middle"
          fill={col} fontSize="26" fontWeight="700"
          fontFamily="JetBrains Mono, monospace">
          {pct}%
        </text>
        <text x="85" y="96" textAnchor="middle"
          fill="#9CA3AF" fontSize="9" letterSpacing="3"
          fontFamily="Inter, sans-serif">
          RISK SCORE
        </text>
        <text x="85" y="112" textAnchor="middle"
          fill={col} fontSize="12" fontWeight="600"
          fontFamily="Inter, sans-serif">
          {riskLevel?.toUpperCase()}
        </text>
      </svg>
    </div>
  )
}
