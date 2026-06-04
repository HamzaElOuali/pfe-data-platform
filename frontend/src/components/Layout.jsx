const NAV = [
  { id: 'order',    label: 'Order Intelligence'  },
  { id: 'segments', label: 'Segment Intelligence' },
  { id: 'platform', label: 'Platform Status'      },
]

const LOGO = 'https://www.alten.com/wp-content/uploads/2019/03/LOGO_Alten_Couleurs_Black.png'

export default function Layout({ page, setPage, children }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>

      {/* ── Navbar ─────────────────────────────────────────────── */}
      <header style={{
        background: '#fff',
        borderBottom: '1px solid var(--border)',
        position: 'sticky', top: 0, zIndex: 100,
        boxShadow: '0 1px 3px rgba(0,0,0,.06)',
      }}>
        <div style={{
          maxWidth: 1340, margin: '0 auto', padding: '0 28px',
          height: 74, display: 'flex', alignItems: 'center',
          justifyContent: 'space-between',
        }}>

          {/* Logo + title */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <img src={LOGO} alt="ALTEN"
              style={{ height: 52, objectFit: 'contain' }}
              onError={e => { e.target.style.display = 'none' }}
            />
            <div style={{ width: 1, height: 28, background: 'var(--border)' }} />
            <div>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)', letterSpacing: '-.01em' }}>
                Data Intelligence Platform
              </div>
              <div style={{
                fontSize: 10, color: 'var(--text3)',
                fontFamily: 'JetBrains Mono, monospace', marginTop: 1,
              }}>
                ML Scoring · E-Commerce Analytics
              </div>
            </div>
          </div>

          {/* Navigation */}
          <nav style={{ display: 'flex', gap: 2 }}>
            {NAV.map(n => {
              const active = page === n.id
              return (
                <button key={n.id} onClick={() => setPage(n.id)} style={{
                  padding: '8px 18px',
                  background: active ? 'var(--red-lt)' : 'transparent',
                  border: 'none',
                  borderBottom: active ? '2px solid var(--red)' : '2px solid transparent',
                  borderRadius: '6px 6px 0 0',
                  cursor: 'pointer', fontSize: 14, fontWeight: active ? 600 : 500,
                  fontFamily: 'Inter, sans-serif',
                  color: active ? 'var(--red)' : 'var(--text2)',
                  transition: 'all .15s',
                }}>
                  {n.label}
                </button>
              )
            })}
          </nav>

          {/* Status pill */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 7,
            padding: '5px 14px', background: '#ECFDF5',
            borderRadius: 20, border: '1px solid #A7F3D0',
          }}>
            <div style={{
              width: 7, height: 7, borderRadius: '50%', background: '#059669',
              position: 'relative',
            }}>
              <span style={{
                position: 'absolute', inset: -3, borderRadius: '50%',
                background: '#059669', opacity: .25,
                animation: 'pulse-dot 2s ease-out infinite',
              }} />
            </div>
            <span style={{ fontSize: 12, fontWeight: 600, color: '#065F46' }}>Platform Online</span>
          </div>
        </div>

        {/* ALTEN brand stripe */}
        <div style={{
          height: 3,
          background: 'linear-gradient(90deg, var(--red) 0%, var(--yellow) 60%, var(--blue) 100%)',
        }} />
      </header>

      {/* ── Main ───────────────────────────────────────────────── */}
      <main style={{
        flex: 1, maxWidth: 1340, margin: '0 auto',
        padding: '32px 28px', width: '100%',
      }}>
        {children}
      </main>

      {/* ── Footer ─────────────────────────────────────────────── */}
      <footer style={{
        borderTop: '1px solid var(--border)', background: '#fff',
        padding: '12px 28px', display: 'flex',
        alignItems: 'center', justifyContent: 'space-between',
      }}>
        <img src={LOGO} alt="ALTEN" style={{ height: 22, opacity: .55 }}
          onError={e => { e.target.style.display = 'none' }} />
        <span style={{
          fontSize: 11, color: 'var(--text3)',
          fontFamily: 'JetBrains Mono, monospace',
        }}>
          ALTEN Data Intelligence Platform · PFE 2026 · v3.0.0
        </span>
      </footer>
    </div>
  )
}
