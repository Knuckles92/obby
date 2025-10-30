import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ThemeProvider } from '../../contexts/ThemeContext';
import InsightFilters from '../../components/insights/InsightFilters';
import InsightEvidence from '../../components/insights/InsightEvidence';
import { defaultTheme } from '../../themes';

// Mock theme context
const MockThemeProvider = ({ children }: { children: React.ReactNode }) => (
  <ThemeProvider initialTheme={defaultTheme.id}>
    {children}
  </ThemeProvider>
);

// Test data
const mockInsights = [
  {
    id: 'insight_1',
    category: 'quality' as const,
    priority: 'high' as const,
    title: 'Code Quality Issue',
    content: 'Potential code duplication detected',
    relatedFiles: ['src/utils.py', 'src/helpers.py'],
    evidence: {
      reasoning: 'Similar code patterns found across multiple files',
      data_points: ['Duplicate function in utils.py and helpers.py'],
      generated_by_agent: 'claude-sonnet',
      semantic_entries_count: 5,
      file_changes_count: 12,
      comprehensive_summaries_count: 2,
      session_summaries_count: 1,
      most_active_files: ['src/utils.py', 'src/helpers.py']
    },
    timestamp: '2023-12-01T10:00:00Z',
    dismissed: false,
    archived: false
  },
  {
    id: 'insight_2',
    category: 'velocity' as const,
    priority: 'medium' as const,
    title: 'Development Velocity',
    content: 'Code changes are happening at a good pace',
    relatedFiles: ['src/components/'],
    evidence: {
      reasoning: 'Consistent commit patterns observed',
      generated_by_agent: 'claude-haiku'
    },
    timestamp: '2023-12-01T11:00:00Z',
    dismissed: false,
    archived: false
  }
];

const mockCategoryConfig = {
  quality: { label: 'Quality', icon: '🔍', color: '#ef4444', bgColor: '#fecaca' },
  velocity: { label: 'Velocity', icon: '🚀', color: '#f97316', bgColor: '#fef3c7' }
};

describe('InsightFilters', () => {
  const defaultProps = {
    filter: 'all',
    setFilter: jest.fn(),
    timeRange: 7,
    setTimeRange: jest.fn(),
    includeDismissed: false,
    setIncludeDismissed: jest.fn(),
    insights: mockInsights,
    categoryConfig: mockCategoryConfig
  };

  const renderWithTheme = (component: React.ReactElement) => {
    return render(
      <MockThemeProvider>
        {component}
      </MockThemeProvider>
    );
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders filter controls correctly', () => {
    renderWithTheme(<InsightFilters {...defaultProps} />);
    
    expect(screen.getByText('Filters')).toBeInTheDocument();
    expect(screen.getByText('All Categories')).toBeInTheDocument();
    expect(screen.getByText('Last 7 days')).toBeInTheDocument();
    expect(screen.getByText('Include Dismissed')).toBeInTheDocument();
    expect(screen.getByText('2 insights')).toBeInTheDocument();
  });

  test('calls setFilter when category changes', async () => {
    const mockSetFilter = jest.fn();
    renderWithTheme(
      <InsightFilters {...defaultProps} setFilter={mockSetFilter} />
    );
    
    const categorySelect = screen.getByDisplayValue('All Categories');
    fireEvent.change(categorySelect, { target: { value: 'quality' } });
    
    await waitFor(() => {
      expect(mockSetFilter).toHaveBeenCalledWith('quality');
    });
  });

  test('calls setTimeRange when time range changes', async () => {
    const mockSetTimeRange = jest.fn();
    renderWithTheme(
      <InsightFilters {...defaultProps} setTimeRange={mockSetTimeRange} />
    );
    
    const timeRangeSelect = screen.getByDisplayValue('Last 7 days');
    fireEvent.change(timeRangeSelect, { target: { value: '14' } });
    
    await waitFor(() => {
      expect(mockSetTimeRange).toHaveBeenCalledWith(14);
    });
  });

  test('calls setIncludeDismissed when checkbox toggled', async () => {
    const mockSetIncludeDismissed = jest.fn();
    renderWithTheme(
      <InsightFilters {...defaultProps} setIncludeDismissed={mockSetIncludeDismissed} />
    );
    
    const checkbox = screen.getByRole('checkbox');
    fireEvent.click(checkbox);
    
    await waitFor(() => {
      expect(mockSetIncludeDismissed).toHaveBeenCalledWith(true);
    });
  });

  test('displays correct insight count', () => {
    renderWithTheme(<InsightFilters {...defaultProps} />);
    
    expect(screen.getByText('2 insights')).toBeInTheDocument();
  });

  test('renders all category options', () => {
    renderWithTheme(<InsightFilters {...defaultProps} />);
    
    expect(screen.getByText('All Categories')).toBeInTheDocument();
    expect(screen.getByText('Quality')).toBeInTheDocument();
    expect(screen.getByText('Velocity')).toBeInTheDocument();
  });
});

describe('InsightEvidence', () => {
  const defaultProps = {
    evidence: {
      reasoning: 'Similar code patterns found across multiple files',
      data_points: ['Duplicate function in utils.py and helpers.py'],
      source_pointers: ['src/utils.py:45-52', 'src/helpers.py:23-30'],
      generated_by_agent: 'claude-sonnet',
      semantic_entries_count: 5,
      file_changes_count: 12,
      comprehensive_summaries_count: 2,
      session_summaries_count: 1,
      most_active_files: ['src/utils.py', 'src/helpers.py']
    }
  };

  const renderWithTheme = (component: React.ReactElement) => {
    return render(
      <MockThemeProvider>
        {component}
      </MockThemeProvider>
    );
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders evidence header', () => {
    renderWithTheme(<InsightEvidence {...defaultProps} />);
    
    expect(screen.getByText('Evidence & Reasoning')).toBeInTheDocument();
  });

  test('renders reasoning when provided', () => {
    renderWithTheme(<InsightEvidence {...defaultProps} />);
    
    expect(screen.getByText('Why this matters')).toBeInTheDocument();
    expect(screen.getByText('Similar code patterns found across multiple files')).toBeInTheDocument();
  });

  test('renders data points when provided', () => {
    renderWithTheme(<InsightEvidence {...defaultProps} />);
    
    expect(screen.getByText('Data Points')).toBeInTheDocument();
    expect(screen.getByText('Duplicate function in utils.py and helpers.py')).toBeInTheDocument();
  });

  test('renders source pointers when provided', () => {
    renderWithTheme(<InsightEvidence {...defaultProps} />);
    
    expect(screen.getByText('Source Pointers')).toBeInTheDocument();
    expect(screen.getByText('src/utils.py:45-52')).toBeInTheDocument();
    expect(screen.getByText('src/helpers.py:23-30')).toBeInTheDocument();
  });

  test('renders analysis scope counts', () => {
    renderWithTheme(<InsightEvidence {...defaultProps} />);
    
    expect(screen.getByText('Analysis Scope:')).toBeInTheDocument();
    expect(screen.getByText('5 semantic entries')).toBeInTheDocument();
    expect(screen.getByText('12 file changes')).toBeInTheDocument();
    expect(screen.getByText('2 comprehensive summaries')).toBeInTheDocument();
    expect(screen.getByText('1 session summaries')).toBeInTheDocument();
  });

  test('renders most active files when provided', () => {
    renderWithTheme(<InsightEvidence {...defaultProps} />);
    
    expect(screen.getByText('Most Active Files')).toBeInTheDocument();
    expect(screen.getByText('utils.py')).toBeInTheDocument();
    expect(screen.getByText('helpers.py')).toBeInTheDocument();
  });

  test('calls onClose when close button is clicked', async () => {
    const mockOnClose = jest.fn();
    renderWithTheme(
      <InsightEvidence {...defaultProps} onClose={mockOnClose} />
    );
    
    const closeButton = screen.getByText('✕');
    fireEvent.click(closeButton);
    
    await waitFor(() => {
      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  test('does not render close button when onClose not provided', () => {
    renderWithTheme(<InsightEvidence {...defaultProps} />);
    
    expect(screen.queryByText('✕')).not.toBeInTheDocument();
  });

  test('renders generated by agent information', () => {
    renderWithTheme(<InsightEvidence {...defaultProps} />);
    
    expect(screen.getByText('Generated by claude-sonnet')).toBeInTheDocument();
  });

  test('handles empty evidence gracefully', () => {
    const emptyEvidence = {
      reasoning: undefined,
      data_points: [],
      source_pointers: [],
      generated_by_agent: undefined,
      semantic_entries_count: 0,
      file_changes_count: 0,
      comprehensive_summaries_count: 0,
      session_summaries_count: 0,
      most_active_files: []
    };
    
    renderWithTheme(<InsightEvidence evidence={emptyEvidence} />);
    
    expect(screen.getByText('Evidence & Reasoning')).toBeInTheDocument();
    expect(screen.getByText('Generated by AI')).toBeInTheDocument();
    expect(screen.getByText('0 semantic entries')).toBeInTheDocument();
  });

  test('truncates long file names in most active files', () => {
    const longFileName = '/very/long/path/to/a/file/with/very/long/name/that/should/be/truncated.py';
    const evidenceWithLongFile = {
      ...defaultProps.evidence,
      most_active_files: [longFileName]
    };
    
    renderWithTheme(<InsightEvidence evidence={evidenceWithLongFile} />);
    
    // Should show truncated filename
    expect(screen.getByText('truncated.py')).toBeInTheDocument();
  });
});