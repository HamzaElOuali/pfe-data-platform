const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8090'

async function request(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } }
  if (body) opts.body = JSON.stringify(body)
  const res = await fetch(`${API_URL}${path}`, opts)
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export const predict             = (payload) => request('POST', '/predict', payload)
export const getSegmentStats     = ()        => request('GET',  '/predict/segments/stats')
export const getHealth           = ()        => request('GET',  '/predict/health')
export const getRecommendations  = (payload) => request('POST', '/recommend', payload)
