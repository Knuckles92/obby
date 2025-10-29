import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { ThemeProvider } from '../../contexts/ThemeContext'
import Insights from '../../pages/Insights'
import * as apiModule from '../../utils/api'

// Mock the API module
jest.mock('../../utils/api')
const mockedApi = apiModule as jest.Mocked<typeof apiModule>

// Mock theme context
const mockTheme = {
  currentTheme: 'professional',
  isDark: false,
  setTheme: jest.fn(),
  useThemeClasses: jest.fn(() => ({})),
  useThemeFeature: jest.fn(() => false)
}

jest.mock('../../contexts/ThemeContext', () => ({
  useTheme: () => mockTheme,
  ThemeProvider: ({ children }: { children: React.ReactNode }) => children
}))

// Wrap component with router
const renderWithRouter = (component: React.ReactElement) => {
  return render(
    <BrowserRouter>
      <ThemeProvider>
        {component}
      </ThemeProvider>
    </BrowserRouter>
  )
}

describe('Insights Page', () => {
  const mockInsights = [
    {
      id: 'insight-1',
      category: 'action' as const,
      priority: 'high' as const,
      title: 'Follow up with team',
      content: 'You mentioned discussing the Q4 roadmap with the team 5 days ago. Consider following up.',
      relatedFiles: ['notes/team-meeting.md', 'docs/roadmap.md'],
      evidence: {
        reasoning: 'Detected todo item about Q4 discussion with timestamp from 5 days ago',
        data_points: ['todo item found', '5 days since last mention']
      },
      timestamp: '2025-10-26T15:00:00Z',
      dismissed: false,
      archived: false
    },
    {
      id: 'insight-2',
      category: 'pattern' as const,
      priority: 'medium' as const,
      title: 'Repetitive config changes',
      content: 'You have been editing config.py multiple times daily for the past week.',
      relatedFiles: ['config.py'],
      evidence: {
        reasoning: 'Pattern detected in file change frequency',
        data_points: ['4 changes per day average', '7 consecutive days']
      },
      timestamp: '2025-10-26T14:30:00Z',
      dismissed: false,
      archived: false
    }
  ]

  beforeEach(() => {
    jest.clearAllMocks()
  })

  test('renders loading state', () => {
    mockedApi.get = jest.fn().mockResolvedValue({ success: true, data: [] })
    
    renderWithRouter(<Insights />)
    
    expect(screen.getByText('Analyzing patterns and generating insights...')).toBeInTheDocument()
  })

  test('renders insights when loaded successfully', async () => {
    mockedApi.get.mockResolvedValue({
      success: true,
      data: mockInsights,
      metadata: {
        time_range_days: 7,
        max_insights: 20,
        generated_at: '2025-10-26T15:00:00Z',
        total_insights: 2
      }
    })

    renderWithRouter(<Insights />)

    await waitFor(() => {
      expect(screen.getByText('Follow up with team')).toBeInTheDocument()
      expect(screen.getByText('Repetitive config changes')).toBeInTheDocument()
    })

    // Check category badges
    expect(screen.getByText('Action Items')).toBeInTheDocument()
    expect(screen.getByText('Patterns')).toBeInTheDocument()

    // Check priority badges
    expect(screen.getByText('High')).toBeInTheDocument()
    expect(screen.getByText('Medium')).toBeInTheDocument()
  })

  test('renders error state', async () => {
    mockedApi.get.mockRejectedValue(new Error('API Error'))

    renderWithRouter(<Insights />)

    await waitFor(() => {
      expect(screen.getByText('Failed to load insights')).toBeInTheDocument()
    })

    expect(screen.getByText('Try again')).toBeInTheDocument()
  })

  test('renders empty state when no insights', async () => {
    mockedApi.get.mockResolvedValue({
      success: true,
      data: [],
      metadata: {
        time_range_days: 7,
        max_insights: 20,
        generated_at: '2025-10-26T15:00:00Z',
        total_insights: 0
      }
    })

    renderWithRouter(<Insights />)

    await waitFor(() => {
      expect(screen.getByText('No insights found')).toBeInTheDocument()
    })
  })

  test('filter functionality works', async () => {
    mockedApi.get.mockResolvedValue({
      success: true,
      data: mockInsights,
      metadata: {
        time_range_days: 7,
        max_insights: 20,
        generated_at: '2025-10-26T15:00:00Z',
        total_insights: 2
      }
    })

    renderWithRouter(<Insights />)

    await waitFor(() => {
      expect(screen.getByText('Follow up with team')).toBeInTheDocument()
    })

    // Click on action items filter
    const actionFilter = screen.getByText('Action Items (1)')
    fireEvent.click(actionFilter)

    // Should show only action items
    expect(screen.getByText('Follow up with team')).toBeInTheDocument()
    expect(screen.queryByText('Repetitive config changes')).not.toBeInTheDocument()

    // Click on "All" filter
    const allFilter = screen.getByText('All (2)')
    fireEvent.click(allFilter)

    // Should show both insights again
    expect(screen.getByText('Follow up with team')).toBeInTheDocument()
    expect(screen.getByText('Repetitive config changes')).toBeInTheDocument()
  })

  test('time range selection works', async () => {
    mockedApi.get.mockResolvedValue({
      success: true,
      data: mockInsights,
      metadata: {
        time_range_days: 7,
        max_insights: 20,
        generated_at: '2025-10-26T15:00:00Z',
        total_insights: 2
      }
    })

    renderWithRouter(<Insights />)

    await waitFor(() => {
      expect(screen.getByText('Follow up with team')).toBeInTheDocument()
    })

    // Change time range
    const timeRangeSelect = screen.getByDisplayValue('Last 7 days')
    fireEvent.change(timeRangeSelect, { target: { value: '14' } })

    // API should be called with new time range
    expect(mockedApi.get).toHaveBeenCalledWith('/api/insights/?time_range_days=14&max_insights=20')
  })

  test('refresh button works', async () => {
    mockedApi.get
      .mockResolvedValueOnce({
        success: true,
        data: mockInsights,
        metadata: {
          time_range_days: 7,
          max_insights: 20,
          generated_at: '2025-10-26T15:00:00Z',
          total_insights: 2
        }
      })
      .mockResolvedValueOnce({
        success: true,
        data: [...mockInsights, {
          id: 'insight-3',
          category: 'opportunity' as const,
          priority: 'low' as const,
          title: 'New insight',
          content: 'This is a new insight',
          relatedFiles: ['new-file.py'],
          evidence: {},
          timestamp: '2025-10-26T16:00:00Z',
          dismissed: false,
          archived: false
        }],
        metadata: {
          time_range_days: 7,
          max_insights: 20,
          generated_at: '2025-10-26T16:00:00Z',
          total_insights: 3
        }
      })

    renderWithRouter(<Insights />)

    await waitFor(() => {
      expect(screen.getByText('Follow up with team')).toBeInTheDocument()
    })

    // Click refresh button
    const refreshButton = screen.getByText('Refresh Insights')
    fireEvent.click(refreshButton)

    await waitFor(() => {
      expect(screen.getByText('New insight')).toBeInTheDocument()
    })

    expect(mockedApi.get).toHaveBeenCalledTimes(2)
  })

  test('insight card expansion works', async () => {
    mockedApi.get.mockResolvedValue({
      success: true,
      data: mockInsights,
      metadata: {
        time_range_days: 7,
        max_insights: 20,
        generated_at: '2025-10-26T15:00:00Z',
        total_insights: 2
      }
    })

    renderWithRouter(<Insights />)

    await waitFor(() => {
      expect(screen.getByText('Follow up with team')).toBeInTheDocument()
    })

    // Click on insight to expand
    const insightCard = screen.getByText('Follow up with team').closest('[class*="cursor-pointer"]')
    fireEvent.click(insightCard!)

    // Should show expanded content
    await waitFor(() => {
      expect(screen.getByText('Related Files:')).toBeInTheDocument()
      expect(screen.getByText('team-meeting.md')).toBeInTheDocument()
      expect(screen.getByText('roadmap.md')).toBeInTheDocument()
      expect(screen.getByText('Why this matters:')).toBeInTheDocument()
      expect(screen.getByText('Dismiss')).toBeInTheDocument()
      expect(screen.getByText('Archive')).toBeInTheDocument()
    })
  })

  test('dismiss insight functionality', async () => {
    mockedApi.get.mockResolvedValue({
      success: true,
      data: [mockInsights[0]], // Only one insight
      metadata: {
        time_range_days: 7,
        max_insights: 20,
        generated_at: '2025-10-26T15:00:00Z',
        total_insights: 1
      }
    })

    mockedApi.post.mockResolvedValue({ success: true })

    renderWithRouter(<Insights />)

    await waitFor(() => {
      expect(screen.getByText('Follow up with team')).toBeInTheDocument()
    })

    // Expand the insight
    const insightCard = screen.getByText('Follow up with team').closest('[class*="cursor-pointer"]')
    fireEvent.click(insightCard!)

    // Click dismiss button
    await waitFor(() => {
      const dismissButton = screen.getByText('Dismiss')
      fireEvent.click(dismissButton)
    })

    // API should be called to dismiss
    expect(mockedApi.post).toHaveBeenCalledWith('/api/insights/insight-1/dismiss')

    // Insight should be removed from display
    await waitFor(() => {
      expect(screen.queryByText('Follow up with team')).not.toBeInTheDocument()
    })
  })
})