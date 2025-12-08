import MasonryLayout from '../components/layouts/MasonryLayout'

interface DateRange {
  start: string
  end: string
  days?: number
}

export default function Insights() {
  // Calculate date range - default to last 7 days
  const getDateRange = (): DateRange => {
    const end = new Date()
    const start = new Date()
    start.setDate(start.getDate() - 7)
    return {
      start: start.toISOString().split('T')[0],
      end: end.toISOString().split('T')[0],
      days: 7
    }
  }

  const dateRange = getDateRange()

  return <MasonryLayout dateRange={dateRange} />
}
