import { Route, Routes } from 'react-router-dom'
import { QueuePage } from '@/pages/QueuePage'
import { ReferralWorkspace } from '@/pages/ReferralWorkspace'

function App() {
  return (
    <Routes>
      <Route path="/" element={<QueuePage />} />
      <Route path="/referrals/:id" element={<ReferralWorkspace />} />
    </Routes>
  )
}

export default App
