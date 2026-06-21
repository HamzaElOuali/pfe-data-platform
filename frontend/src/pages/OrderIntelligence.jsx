import { useState, useEffect, useRef } from 'react'
import { predict, getRecommendations } from '../api'
import RiskGauge from '../components/RiskGauge'

const MONTHS = ['January','February','March','April','May','June',
                'July','August','September','October','November','December']
const DAYS   = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']

const SEG_COLORS = { VIP: '#059669', Loyal: '#0089CF', 'At Risk': '#D97706', Lost: '#DC2626' }

const SEG_DESCS = {
  VIP:
    'High-value customer with a proven purchase history. Eligible for priority courier upgrades and exclusive loyalty benefits.',
  Loyal:
    'Consistent buyer with positive engagement signals. Strong candidate for cross-sell campaigns and reward-tier advancement.',
  'At Risk':
    'Satisfaction indicators are trending negative with elevated churn probability. Immediate personalized outreach is critical.',
  Lost:
    'Low engagement and declining order value detected. A targeted reactivation offer within 30 days is strongly advised.',
}

function getActions(delay, riskLevel, segment) {
  const a = []
  if (riskLevel === 'High' || delay > 20) {
    a.push({ u: 'urgent', t: 'Escalate to logistics — immediate SLA review required' })
    a.push({ u: 'urgent', t: 'Proactive customer notification with compensation voucher' })
  } else if (riskLevel === 'Medium' || delay > 12) {
    a.push({ u: 'warn', t: 'Monitor shipment — flag for CS if delay exceeds 15 days' })
    a.push({ u: 'warn', t: 'Prepare satisfaction recovery message sequence' })
  } else {
    a.push({ u: 'ok', t: 'Standard fulfillment — no escalation required' })
  }
  if (segment === 'At Risk') a.push({ u: 'urgent', t: 'Trigger retention campaign — active churn signal detected' })
  else if (segment === 'Lost') a.push({ u: 'warn',   t: 'Evaluate win-back campaign (30-day cooling window)' })
  else if (segment === 'VIP')  a.push({ u: 'ok',     t: 'Apply VIP tier — priority courier upgrade available' })
  return a
}

function urgencyFromContext(riskLevel, segment) {
  if (riskLevel === 'High' || segment === 'At Risk' || segment === 'Lost') return 'urgent'
  if (riskLevel === 'Medium') return 'warn'
  return 'ok'
}

/* Smooth count-up from 0 to target, resets whenever target changes */
function useCountUp(target, duration = 1100) {
  const [displayed, setDisplayed] = useState(0)
  const frameRef = useRef(null)
  useEffect(() => {
    if (target == null) { setDisplayed(0); return }
    if (frameRef.current) cancelAnimationFrame(frameRef.current)
    const start = performance.now()
    const tick = (now) => {
      const t = Math.min((now - start) / duration, 1)
      const eased = 1 - (1 - t) ** 3          // ease-out cubic
      setDisplayed(target * eased)
      if (t < 1) frameRef.current = requestAnimationFrame(tick)
      else setDisplayed(target)
    }
    frameRef.current = requestAnimationFrame(tick)
    return () => { if (frameRef.current) cancelAnimationFrame(frameRef.current) }
  }, [target, duration])
  return displayed
}

export default function OrderIntelligence() {
  const [form, setForm] = useState({
    distance_km: 450, total_freight: 25,
    order_month: 6,   order_day_of_week: 2,
    review_score: 4,  total_items_price: 185, nb_items: 2,
  })
  const [result,    setResult]    = useState(null)
  const [error,     setError]     = useState(null)
  const [loading,   setLoading]   = useState(false)
  const [aiRecs,    setAiRecs]    = useState(null)
  const [aiSource,  setAiSource]  = useState(null)   // "ai" | "fallback" | null
  const [aiLoading, setAiLoading] = useState(false)
  const [resultKey, setResultKey] = useState(0)       // flip to restart all card animations

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true); setError(null); setAiRecs(null); setAiSource(null)
    try {
      const mlResult = await predict(form)
      setResult(mlResult)
      setResultKey(k => k + 1)

      setAiLoading(true)
      getRecommendations({
        predicted_delay_days: mlResult.predicted_delay_days,
        risk_proba:           mlResult.risk_proba,
        segment:              mlResult.segment,
        distance_km:          form.distance_km,
        total_items_price:    form.total_items_price,
        review_score:         form.review_score,
        order_month:          form.order_month,
      })
        .then(data => {
          setAiRecs(data.recommendations)
          setAiSource(data.source ?? 'fallback')
        })
        .catch(() => { setAiRecs(null); setAiSource(null) })
        .finally(() => setAiLoading(false))

    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const delay = result?.predicted_delay_days
  const rp    = result?.risk_proba
  const rl    = result?.risk_level
  const seg   = result?.segment
  const conf  = result?.confidence_score
  const ts    = result?.scored_at?.slice(0, 19)

  const animDelay = useCountUp(delay ?? null, 1100)
  const animConf  = useCountUp(conf  != null ? conf * 100 : null, 900)

  const delayColor = !delay ? 'var(--text)' : delay < 10 ? '#059669' : delay < 20 ? '#D97706' : '#DC2626'
  const delayPct   = Math.min(((delay || 0) / 30) * 100, 100)
  const fbColor    = form.review_score <= 2 ? '#DC2626' : form.review_score <= 3 ? '#D97706' : '#059669'

  const staticActions = result ? getActions(delay, rl, seg) : []
  const aiUrgency     = urgencyFromContext(rl, seg)
  const showAiBadge   = aiRecs && !aiLoading && aiSource === 'ai'

  return (
    <div>
      <div className="mb6">
        <h1>Order Intelligence</h1>
        <p className="ts tm mt3">ML cascade scoring pipeline · Delivery · Risk · Segment</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '360px 1fr', gap: 24, alignItems: 'start' }}>

        {/* ── Input form ──────────────────────────────────────── */}
        <div className="card">
          <div className="card-accent" />
          <form onSubmit={handleSubmit}>

            <div className="section-label">Logistics</div>

            <div className="form-group">
              <label className="form-label">Distance (km)</label>
              <div className="range-row">
                <input type="range" className="form-range" min="0" max="3000" step="10"
                  value={form.distance_km} onChange={e => set('distance_km', +e.target.value)} />
                <span className="range-val">{form.distance_km} km</span>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Freight cost (BRL)</label>
              <input type="number" className="form-input" min="0" max="2000" step="1"
                value={form.total_freight} onChange={e => set('total_freight', +e.target.value)} />
            </div>

            <div className="g2">
              <div className="form-group">
                <label className="form-label">Month</label>
                <select className="form-select" value={form.order_month}
                  onChange={e => set('order_month', +e.target.value)}>
                  {MONTHS.map((m, i) => <option key={m} value={i + 1}>{m}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Day of week</label>
                <select className="form-select" value={form.order_day_of_week}
                  onChange={e => set('order_day_of_week', +e.target.value)}>
                  {DAYS.map((d, i) => <option key={d} value={i}>{d}</option>)}
                </select>
              </div>
            </div>

            <div className="section-label">Order Details</div>

            <div className="form-group">
              <label className="form-label">Total price (BRL)</label>
              <input type="number" className="form-input" min="0" max="15000" step="5"
                value={form.total_items_price} onChange={e => set('total_items_price', +e.target.value)} />
            </div>

            <div className="form-group">
              <label className="form-label">Number of items</label>
              <div className="range-row">
                <input type="range" className="form-range" min="1" max="20"
                  value={form.nb_items} onChange={e => set('nb_items', +e.target.value)} />
                <span className="range-val">{form.nb_items} item{form.nb_items > 1 ? 's' : ''}</span>
              </div>
            </div>

            <div className="section-label">Customer Feedback</div>

            <div className="form-group">
              <label className="form-label">Review score</label>
              <div className="range-row">
                <input type="range" className="form-range" min="1" max="5" step="0.5"
                  value={form.review_score} onChange={e => set('review_score', +e.target.value)} />
                <span className="range-val" style={{ color: fbColor }}>
                  {form.review_score} ★
                </span>
              </div>
            </div>

            <button type="submit" className="btn btn-primary btn-full" disabled={loading}
              style={{ marginTop: 12 }}>
              {loading
                ? <><div className="spin" style={{ width: 16, height: 16 }} /> Scoring…</>
                : 'Run Intelligence Pipeline'
              }
            </button>
          </form>
        </div>

        {/* ── Results ─────────────────────────────────────────── */}
        <div>
          {error && <div className="err-card mb4"><strong>Pipeline Error:</strong> {error}</div>}

          {result ? (
            /* key=resultKey remounts this subtree → all CSS animations restart */
            <div key={resultKey} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

              {/* Metrics row */}
              <div className="g3">

                {/* ── Delivery Forecast ── */}
                <div className="card card-enter" style={{ '--enter-delay': '0s' }}>
                  <div style={{
                    height: 3, background: delayColor, borderRadius: '12px 12px 0 0',
                    margin: '-24px -24px 20px',
                  }} />
                  <div className="section-label" style={{ marginTop: 0, marginBottom: 10 }}>
                    Delivery Forecast
                  </div>
                  <div className="kpi-num kpi-enter" style={{ color: delayColor }}>
                    {animDelay.toFixed(1)}<span className="kpi-unit">days</span>
                  </div>
                  <div className="prog-track" style={{ marginTop: 10 }}>
                    <div className="prog-fill" style={{ width: `${delayPct}%`, background: delayColor }} />
                  </div>
                  <div className="mt3" style={{
                    fontSize: 11, color: 'var(--text3)',
                    fontFamily: 'JetBrains Mono, monospace',
                  }}>
                    confidence {animConf.toFixed(0)}%
                  </div>
                </div>

                {/* ── Risk Gauge ── */}
                <div className="card card-enter" style={{
                  '--enter-delay': '0.1s',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <RiskGauge riskProba={rp} riskLevel={rl} size={152} />
                </div>

                {/* ── Customer Segment ── */}
                <div className="card card-enter" style={{
                  '--enter-delay': '0.2s',
                  textAlign: 'center',
                  borderTop: `3px solid ${SEG_COLORS[seg] || 'var(--border)'}`,
                }}>
                  <div className="section-label" style={{ marginTop: 0 }}>Customer Segment</div>
                  <div className="seg-name-enter" style={{
                    fontSize: 22, fontWeight: 700, marginBottom: 10,
                    color: SEG_COLORS[seg],
                  }}>
                    {seg}
                  </div>
                  <div style={{
                    fontSize: 12, color: 'var(--text2)', lineHeight: 1.75,
                    textAlign: 'left',
                  }}>
                    {SEG_DESCS[seg]}
                  </div>
                </div>
              </div>

              {/* ── Recommended Actions ── */}
              <div className="card card-enter" style={{ '--enter-delay': '0.28s' }}>
                <div className="card-accent" />

                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
                  <h3 style={{ margin: 0 }}>Recommended Actions</h3>
                  {showAiBadge && (
                    <span style={{
                      fontSize: 10, fontWeight: 700, letterSpacing: '.08em',
                      textTransform: 'uppercase',
                      padding: '2px 8px', borderRadius: 20,
                      background: 'linear-gradient(90deg, #6D28D9 0%, #0089CF 100%)',
                      color: '#fff',
                    }}>
                      ✦ AI-powered
                    </span>
                  )}
                </div>

                {aiLoading && (
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    padding: '12px 14px', borderRadius: 8,
                    background: 'var(--surf2)', border: '1px solid var(--border)',
                    marginBottom: 6,
                  }}>
                    <div className="spin" style={{ width: 14, height: 14, flexShrink: 0 }} />
                    <span style={{ fontSize: 13, color: 'var(--text2)', fontStyle: 'italic' }}>
                      Generating AI recommendations…
                    </span>
                  </div>
                )}

                {!aiLoading && aiRecs && aiRecs.map((rec, i) => (
                  <div key={i} className={`action-item ${aiUrgency} action-enter`}
                    style={{ animationDelay: `${0.32 + i * 0.09}s` }}>
                    <div className={`action-dot ${aiUrgency}`} />
                    <span>{rec}</span>
                  </div>
                ))}

                {!aiLoading && !aiRecs && staticActions.map((a, i) => (
                  <div key={i} className={`action-item ${a.u} action-enter`}
                    style={{ animationDelay: `${0.32 + i * 0.09}s` }}>
                    <div className={`action-dot ${a.u}`} />
                    <span>{a.t}</span>
                  </div>
                ))}

              </div>
            </div>

          ) : !error && (
            <div className="card empty-state">
              <div className="empty-icon">◈</div>
              <h3 style={{ color: 'var(--text2)', fontWeight: 500, marginBottom: 8 }}>
                Ready to Score
              </h3>
              <p style={{ color: 'var(--text3)', fontSize: 13 }}>
                Configure order parameters and run the pipeline.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
