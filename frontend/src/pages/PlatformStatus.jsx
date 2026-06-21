import { useEffect, useState } from 'react'
import { getHealth } from '../api'

const SERVICES = [
  { name: 'Apache Airflow', desc: 'Orchestration',  url: 'http://localhost:8080/dags/e-commerce_platform_industrialized/grid' },
  { name: 'dbt Docs',       desc: 'Data Catalog',   url: 'http://localhost:8085' },
  { name: 'Grafana',        desc: 'Observability',  url: 'http://localhost:3000/d/dq_pfe_platform/pfe-data-platform-3a-observability?orgId=1&from=now-7d&to=now&timezone=browser&refresh=30s' },
  { name: 'pgAdmin',        desc: 'Database Admin', url: 'http://localhost:5050' },
  { name: 'FastAPI Mock',   desc: 'Prediction API', url: 'http://localhost:8090/docs' },
]

const MODEL_REGISTRY = [
  { name: 'M1 — Delay Regressor', algo: 'LightGBM',   metric: 'MAE',        value: '4.84', sub: 'RMSE 6.96 · R² 0.31', color: '#D4002A' },
  { name: 'M2 — Risk Classifier',  algo: 'XGBoost',    metric: 'AUC-ROC',    value: '0.93', sub: 'Binary classification', color: '#0089CF' },
  { name: 'M3 — Segment Model',    algo: 'KMeans K=4', metric: 'Silhouette', value: '0.71', sub: '4 clusters',             color: '#D97706' },
]

const MODEL_LABELS = {
  m1: 'M1 · Delay Regressor',
  m2: 'M2 · Risk Classifier',
  m3: 'M3 · Segment Model',
}

export default function PlatformStatus() {
  const [health,    setHealth]    = useState(null)
  const [healthErr, setHealthErr] = useState(null)
  const [loading,   setLoading]   = useState(true)

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch(err => setHealthErr(err.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <div className="mb6">
        <h1>Platform Status</h1>
        <p className="ts tm mt3">Service health · ML diagnostics · Model registry</p>
      </div>

      <div className="g2 mb6">

        {/* ML Pipeline */}
        <div className="card">
          <div className="card-accent" />
          <h3 style={{ marginBottom: 16 }}>ML Pipeline</h3>

          {loading && (
            <div style={{ display: 'flex', justifyContent: 'center', padding: 24 }}>
              <div className="spin" />
            </div>
          )}

          {healthErr && (
            <div className="svc-card" style={{ borderColor: '#FECACA', background: '#FEF2F2' }}>
              <div className="svc-dot fail" />
              <div>
                <div style={{ fontWeight: 600, fontSize: 13 }}>Scoring API</div>
                <div style={{ fontSize: 11, color: 'var(--text3)', fontFamily: 'JetBrains Mono, monospace' }}>
                  {healthErr}
                </div>
              </div>
            </div>
          )}

          {health && (
            <>
              {Object.entries(health.model_versions || {}).map(([k, v]) => (
                <div key={k} className="svc-card">
                  <div className="svc-dot ok" />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: 600, fontSize: 13 }}>{MODEL_LABELS[k] || k}</div>
                    <div style={{ fontSize: 11, color: 'var(--text3)', fontFamily: 'JetBrains Mono, monospace' }}>
                      {v}
                    </div>
                  </div>
                </div>
              ))}
              <div style={{
                marginTop: 10, fontSize: 11,
                color: 'var(--text3)', fontFamily: 'JetBrains Mono, monospace',
              }}>
                last_check · {health.timestamp?.slice(0, 19)}
              </div>
            </>
          )}
        </div>

        {/* Infrastructure */}
        <div className="card">
          <div className="card-accent" />
          <h3 style={{ marginBottom: 16 }}>Infrastructure Services</h3>
          {SERVICES.map(svc => (
            <div key={svc.name} className="svc-card">
              <div className="svc-dot ok" />
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: 13 }}>{svc.name}</div>
                <div style={{ fontSize: 11, color: 'var(--text3)' }}>{svc.desc}</div>
              </div>
              <a href={svc.url} target="_blank" rel="noreferrer" style={{
                fontSize: 12, color: 'var(--red)',
                textDecoration: 'none', fontWeight: 600,
              }}>
                Open →
              </a>
            </div>
          ))}
        </div>
      </div>

      {/* Model Performance Registry */}
      <h2 style={{ marginBottom: 16 }}>Model Performance Registry</h2>
      <div className="g3">
        {MODEL_REGISTRY.map(m => (
          <div key={m.name} className="card" style={{ borderTop: `3px solid ${m.color}` }}>
            <div className="section-label" style={{ marginTop: 0 }}>{m.name}</div>
            <div style={{
              fontSize: 11, color: 'var(--text3)',
              fontFamily: 'JetBrains Mono, monospace', marginBottom: 14,
            }}>
              {m.algo}
            </div>
            <div style={{
              fontSize: 10, textTransform: 'uppercase',
              letterSpacing: '.12em', color: 'var(--text3)', marginBottom: 4,
            }}>
              {m.metric}
            </div>
            <div className="kpi-num" style={{ color: m.color, fontSize: 28 }}>
              {m.value}
            </div>
            <div style={{
              fontSize: 10, color: 'var(--text3)',
              fontFamily: 'JetBrains Mono, monospace', marginTop: 6,
            }}>
              {m.sub}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
