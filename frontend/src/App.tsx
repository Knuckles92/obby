import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { useState } from 'react'
import { ThemeProvider } from './contexts/ThemeContext'
import Sidebar from './components/Sidebar'
import ThemeEffects from './components/ThemeEffects'
import Dashboard from './pages/Dashboard'
import DiffViewer from './pages/DiffViewer'
import LivingNote from './pages/LivingNote'
import SearchPage from './pages/SearchPage'
import Settings from './pages/Settings'

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
                <Route path="/living-note" element={<LivingNote />} />
                <Route path="/search" element={<SearchPage />} />
                <Route path="/settings" element={<Settings />} />
              </Routes>
            </div>
          </main>
        </div>
      </Router>
    </ThemeProvider>
  )
}

export default App