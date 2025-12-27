import { useState, useEffect } from 'react'
import MasonryLayout from '../components/layouts/MasonryLayout'
import { apiFetch } from '../utils/api'

interface DateRange {
  start: string
  end: string
  days?: number
}

export default function Insights() {
  const [dateRange, setDateRange] = useState<DateRange>(() => {
    // Default to last 7 days while loading
    const end = new Date()
    const start = new Date()
    start.setDate(start.getDate() - 7)
    return {
      start: start.toISOString().split('T')[0],
      end: end.toISOString().split('T')[0],
      days: 7
    }
  })

  // Fetch context window setting from API
  useEffect(() => {
    const fetchContextConfig = async () => {
      try {
        const response = await apiFetch('/api/semantic-insights/context-config')
        const data = await response.json()
        if (data.success && data.config) {
          const contextWindowDays = data.config.contextWindowDays || 7
          const end = new Date()
          const start = new Date()
          start.setDate(start.getDate() - contextWindowDays)
          setDateRange({
            start: start.toISOString().split('T')[0],
            end: end.toISOString().split('T')[0],
            days: contextWindowDays
          })
        }
      } catch (error) {
        console.error('Error fetching context config:', error)
        // Keep default 7 days on error
      }
    }

    fetchContextConfig()

    // Refetch when window regains focus (e.g., user returns from Settings page)
    const handleFocus = () => {
      fetchContextConfig()
    }
    window.addEventListener('focus', handleFocus)

    return () => {
      window.removeEventListener('focus', handleFocus)
    }
  }, [])

  const handleDateRangeChange = (newDateRange: DateRange) => {
    setDateRange(newDateRange);
  };

  return <MasonryLayout dateRange={dateRange} onDateRangeChange={handleDateRangeChange} />
}
