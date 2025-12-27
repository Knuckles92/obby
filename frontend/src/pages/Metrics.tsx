import { useState, useRef, useEffect } from 'react';
import { RefreshCw, BarChart3 } from 'lucide-react';
import ActivityMetricsSection from '../components/metrics/ActivityMetricsSection';
import { NoteViewerModal, FileNotFoundDialog } from '../components/modals';
import { checkFileExists } from '../utils/fileOperations';
import { useSemanticInsights } from '../hooks/useInsights';
import { apiFetch } from '../utils/api';

interface DateRange {
  start: string;
  end: string;
  days?: number;
}

export default function Metrics() {
  const [selectedNotePath, setSelectedNotePath] = useState<string | null>(null);
  const [isNoteModalOpen, setIsNoteModalOpen] = useState(false);
  const [fileNotFoundDialog, setFileNotFoundDialog] = useState<{
    isOpen: boolean;
    filePath: string;
    insightId: number | null;
  }>({
    isOpen: false,
    filePath: '',
    insightId: null
  });
  const [isRefreshing, setIsRefreshing] = useState(false);
  const metricsRefetchRef = useRef<(() => void) | null>(null);

  const { performAction, refetch: refetchSemanticInsights } = useSemanticInsights({
    status: undefined,
    limit: 50
  });

  const [dateRange, setDateRange] = useState<DateRange>(() => {
    // Default to last 7 days while loading
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 7);
    return {
      start: start.toISOString().split('T')[0],
      end: end.toISOString().split('T')[0],
      days: 7
    };
  });
  const [contextWindowDays, setContextWindowDays] = useState<number>(7);
  const [contextConfigSaving, setContextConfigSaving] = useState(false);

  // Fetch context window setting from API
  useEffect(() => {
    const fetchContextConfig = async () => {
      try {
        const response = await apiFetch('/api/semantic-insights/context-config');
        const data = await response.json();
        if (data.success && data.config) {
          const days = data.config.contextWindowDays || 7;
          setContextWindowDays(days);
          const end = new Date();
          const start = new Date();
          start.setDate(start.getDate() - days);
          setDateRange({
            start: start.toISOString().split('T')[0],
            end: end.toISOString().split('T')[0],
            days: days
          });
        }
      } catch (error) {
        console.error('Error fetching context config:', error);
        // Keep default 7 days on error
      }
    };

    fetchContextConfig();

    // Refetch when window regains focus (e.g., user returns from Settings page)
    const handleFocus = () => {
      fetchContextConfig();
    };
    window.addEventListener('focus', handleFocus);

    return () => {
      window.removeEventListener('focus', handleFocus);
    };
  }, []);

  const updateContextWindowDays = async (days: number) => {
    setContextConfigSaving(true);
    try {
      const response = await apiFetch('/api/semantic-insights/context-config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context_window_days: days })
      });
      const data = await response.json();
      if (data.success) {
        setContextWindowDays(days);
        const end = new Date();
        const start = new Date();
        start.setDate(start.getDate() - days);
        setDateRange({
          start: start.toISOString().split('T')[0],
          end: end.toISOString().split('T')[0],
          days: days
        });
        // Trigger a refresh of metrics when the date range changes
        if (metricsRefetchRef.current) {
          await metricsRefetchRef.current();
        }
      } else {
        console.error('Failed to update context config:', data.error);
      }
    } catch (error) {
      console.error('Error updating context config:', error);
    } finally {
      setContextConfigSaving(false);
    }
  };

  const handleOpenNote = async (path: string, insightId?: number) => {
    // Check if file exists
    const fileExists = await checkFileExists(path);
    
    if (!fileExists && insightId !== undefined && insightId !== null) {
      // File doesn't exist and we have an insight ID - show dialog
      setFileNotFoundDialog({
        isOpen: true,
        filePath: path,
        insightId: insightId
      });
      return;
    }
    
    if (!fileExists) {
      // File doesn't exist but no insight ID - just show error
      console.warn(`File not found: ${path}`);
      return;
    }
    
    // File exists - open normally
    setSelectedNotePath(path);
    setIsNoteModalOpen(true);
  };

  const handleCloseNoteModal = () => {
    setIsNoteModalOpen(false);
    setSelectedNotePath(null);
  };

  const handleCloseFileNotFoundDialog = () => {
    setFileNotFoundDialog({
      isOpen: false,
      filePath: '',
      insightId: null
    });
  };

  const handleDeleteInsight = async () => {
    if (fileNotFoundDialog.insightId !== null) {
      await performAction(fileNotFoundDialog.insightId, 'dismiss');
      await refetchSemanticInsights();
      handleCloseFileNotFoundDialog();
    }
  };

  const handleRefetchReady = (refetch: () => void) => {
    metricsRefetchRef.current = refetch;
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    if (metricsRefetchRef.current) {
      await metricsRefetchRef.current();
    }
    setIsRefreshing(false);
  };

  return (
    <div className="min-h-screen p-6" style={{ backgroundColor: 'var(--color-background)' }}>
      {/* Modern Header */}
      <div className="relative overflow-hidden rounded-2xl mb-8 p-8 text-white shadow-2xl" style={{
        background: 'linear-gradient(135deg, var(--color-primary) 0%, var(--color-accent) 50%, var(--color-secondary) 100%)'
      }}>
        <div className="absolute inset-0 bg-black/10"></div>
        <div className="absolute -top-10 -right-10 w-40 h-40 bg-white/10 rounded-full blur-3xl"></div>
        <div className="absolute -bottom-10 -left-10 w-32 h-32 bg-white/5 rounded-full blur-2xl"></div>

        <div className="relative z-10 flex items-center justify-between">
          <div className="space-y-2">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-white/20 rounded-xl backdrop-blur-sm">
                <BarChart3 className="h-6 w-6" />
              </div>
              <h1 className="text-3xl font-bold tracking-tight">Metrics</h1>
            </div>
            <p className="text-blue-100 text-lg">
              File activity and development metrics
              {dateRange.days && ` (Last ${dateRange.days} days)`}
            </p>
          </div>

          {/* Actions - Button Group */}
          <div className="flex items-center gap-2 flex-wrap">
            {/* Context Window Selector */}
            <div className="flex items-center gap-1 bg-white/10 rounded-lg p-1 border border-white/20">
              {[7, 14, 30].map((days) => (
                <button
                  key={days}
                  onClick={() => updateContextWindowDays(days)}
                  disabled={contextConfigSaving}
                  className={`px-3 py-1.5 text-sm rounded-md font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed ${
                    contextWindowDays === days
                      ? 'bg-white/30 text-white shadow-sm'
                      : 'text-white/80 hover:text-white hover:bg-white/10'
                  }`}
                >
                  {days}d
                </button>
              ))}
            </div>

            {/* Refresh Button */}
            <button
              onClick={handleRefresh}
              disabled={isRefreshing}
              className={`relative overflow-hidden px-6 py-3 rounded-xl font-semibold transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed group ${
                isRefreshing
                  ? 'bg-white/10 border border-white/20 text-white'
                  : 'bg-white/20 hover:bg-white/30 border border-white/30 text-white'
              }`}
            >
              <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/20 to-white/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700"></div>
              <div className="relative flex items-center space-x-2">
                <RefreshCw size={16} className={isRefreshing ? 'animate-spin' : ''} />
                <span>Refresh</span>
              </div>
            </button>
          </div>
        </div>
      </div>

      {/* Activity Metrics Section */}
      <ActivityMetricsSection dateRange={dateRange} onOpenNote={handleOpenNote} onRefetchReady={handleRefetchReady} />

      {/* Note Viewer Modal */}
      <NoteViewerModal
        isOpen={isNoteModalOpen}
        onClose={handleCloseNoteModal}
        filePath={selectedNotePath}
      />

      {/* File Not Found Dialog */}
      <FileNotFoundDialog
        isOpen={fileNotFoundDialog.isOpen}
        onClose={handleCloseFileNotFoundDialog}
        onDelete={handleDeleteInsight}
        filePath={fileNotFoundDialog.filePath}
      />
    </div>
  );
}

