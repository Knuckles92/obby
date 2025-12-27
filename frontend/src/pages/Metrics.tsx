import { useState, useRef } from 'react';
import { RefreshCw, BarChart3 } from 'lucide-react';
import ActivityMetricsSection from '../components/metrics/ActivityMetricsSection';
import { NoteViewerModal, FileNotFoundDialog } from '../components/modals';
import { checkFileExists } from '../utils/fileOperations';
import { useSemanticInsights } from '../hooks/useInsights';

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

  // Calculate date range - default to last 7 days
  const getDateRange = (): DateRange => {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 7);
    return {
      start: start.toISOString().split('T')[0],
      end: end.toISOString().split('T')[0],
      days: 7
    };
  };

  const dateRange = getDateRange();

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

