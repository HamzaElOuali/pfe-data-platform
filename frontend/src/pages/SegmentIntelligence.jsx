import { useEffect, useState } from 'react'
import {
  PieChart, Pie, Cell,
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from 'recharts'
import { getSegmentStats } from '../api'

const SEG_ORDER  = ['VIP', 'Loyal', 'At Risk', 'Lost']
const SEG_COLORS = { VIP: '#059669', Loyal: '#0089CF', 'At Risk': '#D97706', Lost: '#DC2626' }

/* ── Count-up hook ───────────────────────────────────────────── */
function useCountUp(target, duration = 1100, delay = 0) {
  const [value, setValue] = useState(0)
  useEffect(() => {
    if (!target) return
    let raf
    let startTs = null
    const tick = (ts) => {
      if (!startTs) startTs = ts + delay
      if (ts < startTs) { raf = requestAnimationFrame(tick); return }
      const elapsed = ts - startTs
      const p = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - p, 3)
      setValue(Math.round(target * eased))
      if (p < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, duration, delay])
  return value
}

/* ── Animated progress bar ───────────────────────────────────── */
function AnimBar({ pct, color }) {
  const [width, setWidth] = useState(0)
  useEffect(() => {
    const t = setTimeout(() => setWidth(pct), 80)
    return () => clearTimeout(t)
  }, [pct])
  return (
    <div className="prog-track mt3">
      <div className="prog-fill" style={{ width: `${width}%`, background: color }} />
    </div>
  )
}

/* ── Individual KPI card ─────────────────────────────────────── */
function SegCard({ seg, count, total, col, delay }) {
  const animated = useCountUp(count, 1100, delay)
  const pct = total ? (count / total * 100) : 0
  return (
    <div className="card seg-card-anim" style={{
      borderTop: `3px solid ${col}`,
      animationDelay: `${delay}ms`,
    }}>
      <div className="section-label" style={{ marginTop: 0 }}>{seg}</div>
      <div className="kpi-num" style={{ color: col, fontSize: 30 }}>
        {animated.toLocaleString()}
      </div>
      <div style={{ fontSize: 12, color: 'var(--text3)', fontFamily: 'JetBrains Mono, monospace', marginTop: 4 }}>
        {pct.toFixed(1)}%
      </div>
      <AnimBar pct={pct} color={col} />
    </div>
  )
}

/* ── Custom donut label ──────────────────────────────────────── */
function DonutLabel({ cx, cy, midAngle, outerRadius, name, percent }) {
  if (percent < 0.04) return null
  const RAD = Math.PI / 180
  const r = outerRadius + 22
  const x = cx + r * Math.cos(-midAngle * RAD)
  const y = cy + r * Math.sin(-midAngle * RAD)
  return (
    <text x={x} y={y} textAnchor={x > cx ? 'start' : 'end'}
      fill="var(--text2)" fontSize={12} fontFamily="Inter, sans-serif">
      {name} {(percent * 100).toFixed(0)}%
    </text>
  )
}

/* ── Main page ───────────────────────────────────────────────── */
export default function SegmentIntelligence() {
  const [data,     setData]     = useState(null)
  const [error,    setError]    = useState(null)
  const [loading,  setLoading]  = useState(true)
  const [chartKey, setChartKey] = useState(0)

  useEffect(() => {
    getSegmentStats()
      .then(d => { setData(d); setChartKey(k => k + 1) })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  const total = data
    ? Object.values(data.distribution || {}).reduce((s, v) => s + v, 0)
    : 0

  return (
    <div>
      <div className="mb6">
        <h1>Segment Intelligence</h1>
        <p className="ts tm mt3">Real-time distribution from scored predictions</p>
      </div>

      {loading && (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 64 }}>
          <div className="spin" style={{ width: 32, height: 32 }} />
        </div>
      )}

      {error && (
        <div className="card empty-state">
          <div className="empty-icon">◈</div>
          <h3 style={{ color: 'var(--text2)', fontWeight: 500, marginBottom: 8 }}>
            No Prediction Data
          </h3>
          <p style={{ color: 'var(--text3)', fontSize: 13, marginBottom: 16 }}>
            Run the batch scoring DAG in Airflow to populate segment data.
          </p>
          <div className="err-card" style={{ textAlign: 'left' }}>{error}</div>
        </div>
      )}

      {data && !loading && (
        <>
          {/* ── KPI row — staggered entry + count-up + animated bar ── */}
          <div className="g4 mb6">
            {SEG_ORDER.map((seg, i) => (
              <SegCard
                key={seg}
                seg={seg}
                count={data.distribution?.[seg] || 0}
                total={total}
                col={SEG_COLORS[seg]}
                delay={i * 120}
              />
            ))}
          </div>

          {/* ── Charts — fade-in + Recharts built-in draw animation ── */}
          <div className="g2">
            <div className="card seg-chart-anim" style={{ animationDelay: '500ms' }}>
              <h3 style={{ marginBottom: 20 }}>Segment Distribution</h3>
              <ResponsiveContainer width="100%" height={280}>
                <PieChart key={chartKey}>
                  <Pie
                    data={SEG_ORDER.map(seg => ({
                      name: seg,
                      value: data.distribution?.[seg] || 0,
                    }))}
                    cx="50%" cy="50%"
                    innerRadius={68} outerRadius={108}
                    paddingAngle={3} dataKey="value"
                    isAnimationActive={true}
                    animationBegin={100}
                    animationDuration={1200}
                    animationEasing="ease-out"
                    labelLine={{ stroke: 'var(--border)' }}
                    label={<DonutLabel />}
                  >
                    {SEG_ORDER.map(seg => (
                      <Cell key={seg} fill={SEG_COLORS[seg] || '#9CA3AF'} />
                    ))}
                  </Pie>
                  <Tooltip formatter={v => v.toLocaleString()} />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="card seg-chart-anim" style={{ animationDelay: '650ms' }}>
              <h3 style={{ marginBottom: 20 }}>Segment Counts</h3>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart
                  key={chartKey}
                  data={SEG_ORDER.map(seg => ({ name: seg, count: data.distribution?.[seg] || 0 }))}
                  layout="vertical"
                  margin={{ left: 8, right: 40, top: 4, bottom: 4 }}
                >
                  <XAxis type="number"
                    tick={{ fontSize: 11, fill: '#9CA3AF' }}
                    axisLine={false} tickLine={false}
                  />
                  <YAxis type="category" dataKey="name" width={72}
                    tick={{ fontSize: 13, fill: '#4B5563' }}
                    axisLine={false} tickLine={false}
                  />
                  <Tooltip formatter={v => v.toLocaleString()} />
                  <Bar dataKey="count" radius={[0, 6, 6, 0]}
                    isAnimationActive={true}
                    animationBegin={200}
                    animationDuration={1000}
                    animationEasing="ease-out"
                  >
                    {SEG_ORDER.map(seg => <Cell key={seg} fill={SEG_COLORS[seg]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* ── Recent predictions table ── */}
          {data.recent_predictions?.length > 0 && (
            <div className="card mt4 seg-chart-anim" style={{ animationDelay: '800ms' }}>
              <h3 style={{ marginBottom: 16 }}>Recent Predictions</h3>
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid var(--border)' }}>
                      {Object.keys(data.recent_predictions[0]).map(k => (
                        <th key={k} style={{
                          padding: '8px 12px', textAlign: 'left',
                          fontSize: 10, fontWeight: 700, letterSpacing: '.1em',
                          textTransform: 'uppercase', color: 'var(--text3)',
                        }}>{k}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {data.recent_predictions.map((row, i) => (
                      <tr key={i} style={{
                        borderBottom: '1px solid var(--border)',
                        background: i % 2 === 0 ? 'var(--surf2)' : 'var(--surface)',
                      }}>
                        {Object.values(row).map((v, j) => (
                          <td key={j} style={{
                            padding: '8px 12px',
                            fontFamily: 'JetBrains Mono, monospace',
                            fontSize: 12, color: 'var(--text)',
                          }}>{v ?? '—'}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
