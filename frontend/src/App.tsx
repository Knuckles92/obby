import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useState } from 'react'
import { ThemeProvider } from './contexts/ThemeContext'
import Sidebar from './components/Sidebar'
import { ThemeEffects } from './components/ui'
import Dashboard from './pages/Dashboard'
import DiffViewer from './pages/DiffViewer'
import SessionSummary from './pages/SessionSummary'
import SummaryNotes from './pages/SummaryNotes'
import Settings from './pages/Settings'
import Services from './pages/Services'
import NotFound from './pages/NotFound'
import Chat from './pages/Chat'
import Insights from './pages/Insights'

function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true)

  return (
    <ThemeProvider>
      <Router>
        <div className="flex h-screen" style={{
          backgroundColor: 'var(--color-background)',
          color: 'var(--color-text-primary)',
          fontFamily: 'var(--font-family-sans)'
        }}>
          <ThemeEffects />
          <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />
          
          <main 
            className={`flex-1 transition-all duration-300 ${sidebarOpen ? 'ml-64' : 'ml-16'}`}
            style={{
              transitionDuration: 'var(--duration-normal)',
              transitionTimingFunction: 'var(--easing-ease)'
            }}
          >
            <div className="h-full overflow-auto" style={{ padding: 'var(--spacing-lg)' }}>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/diffs" element={<DiffViewer />} />
                <Route path="/chat" element={<Chat />} />
                <Route path="/session-summary" element={<SessionSummary />} />
                <Route path="/summary-notes" element={<SummaryNotes />} />
                <Route path="/insights" element={<Insights />} />
                <Route path="/services" element={<Services />} />
                <Route path="/admin" element={<Navigate to="/settings" replace />} />
                <Route path="/settings" element={<Settings />} />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </div>
          </main>
        </div>
      </Router>
    </ThemeProvider>
  )
}

export default App
