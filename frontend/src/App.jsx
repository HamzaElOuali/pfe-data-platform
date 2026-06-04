import { useState } from 'react'
import Layout from './components/Layout'
import OrderIntelligence from './pages/OrderIntelligence'
import SegmentIntelligence from './pages/SegmentIntelligence'
import PlatformStatus from './pages/PlatformStatus'

export default function App() {
  const [page, setPage] = useState('order')
  return (
    <Layout page={page} setPage={setPage}>
      {page === 'order'    && <OrderIntelligence />}
      {page === 'segments' && <SegmentIntelligence />}
      {page === 'platform' && <PlatformStatus />}
    </Layout>
  )
}
