import { useState, useRef } from 'react';
import { RefreshCw } from 'lucide-react';
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
      {/* Header */}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2" style={{ color: 'var(--color-text-primary)' }}>
            Metrics
          </h1>
          <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
            File activity and development metrics
            {dateRange.days && ` (Last ${dateRange.days} days)`}
          </p>
        </div>

        {/* Refresh Button */}
        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="flex items-center gap-2 px-4 py-2 rounded-lg transition-colors"
          style={{
            backgroundColor: 'var(--color-surface)',
            color: 'var(--color-text)',
            border: '1px solid var(--color-border)'
          }}
        >
          <RefreshCw size={16} className={isRefreshing ? 'animate-spin' : ''} />
          Refresh
        </button>
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

