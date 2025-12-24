/**
 * MasonryLayout - Real-time insights display with backend data
 *
 * This layout fetches real insights from the backend and displays them
 * using the reusable InsightCard component. Also includes semantic insights
 * section for AI-powered analysis.
 */

import React, { useState } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';
import InsightCard from '../insights/InsightCard';
import { useInsights, useSemanticInsights } from '../../hooks/useInsights';
import { SemanticInsightsSection } from '../semantic-insights';
import NoteViewerModal from '../NoteViewerModal';
import FileNotFoundDialog from '../FileNotFoundDialog';
import { checkFileExists } from '../../utils/fileOperations';

interface MasonryLayoutProps {
  dateRange: {
    start: string;
    end: string;
    days?: number;
  };
}

export default function MasonryLayout({ dateRange }: MasonryLayoutProps) {
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

  const { insights, loading, error, refetch } = useInsights({
    layoutName: 'masonry',
    dateRange
  });

  const { performAction, refetch: refetchSemanticInsights } = useSemanticInsights({
    status: undefined,
    limit: 50
  });

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

  // Convert insights object to sorted array
  const insightArray = Object.values(insights).sort((a, b) => {
    // Sort by position if available in config, otherwise maintain order
    return 0;
  });

  return (
    <div className="min-h-screen p-6" style={{ backgroundColor: 'var(--color-background)' }}>
      {/* Header */}
      <div className="mb-8 flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold mb-2" style={{ color: 'var(--color-text-primary)' }}>
            Insights Overview
          </h1>
          <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
            Clean, organized view of your development metrics
            {dateRange.days && ` (Last ${dateRange.days} days)`}
          </p>
        </div>

        {/* Refresh Button */}
        <button
          onClick={refetch}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 rounded-lg transition-colors"
          style={{
            backgroundColor: 'var(--color-surface)',
            color: 'var(--color-text)',
            border: '1px solid var(--color-border)'
          }}
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Loading State */}
      {loading && insightArray.length === 0 && (
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <RefreshCw size={32} className="animate-spin mx-auto mb-4" style={{ color: 'var(--color-primary)' }} />
            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
              Loading insights...
            </p>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div
          className="p-4 rounded-lg flex items-start gap-3 mb-6"
          style={{
            backgroundColor: 'var(--color-error)20',
            border: '1px solid var(--color-error)',
            color: 'var(--color-error)'
          }}
        >
          <AlertCircle size={20} />
          <div>
            <p className="font-semibold">Error Loading Insights</p>
            <p className="text-sm mt-1">{error}</p>
            <button
              onClick={refetch}
              className="mt-2 px-3 py-1 rounded text-sm"
              style={{
                backgroundColor: 'var(--color-error)',
                color: 'white'
              }}
            >
              Try Again
            </button>
          </div>
        </div>
      )}

      {/* Semantic Insights Section */}
      <SemanticInsightsSection onOpenNote={handleOpenNote} />

      {/* Activity Insights Header */}
      <div className="mb-4">
        <h2 className="text-xl font-bold" style={{ color: 'var(--color-text-primary)' }}>
          Activity Metrics
        </h2>
        <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
          File activity and development metrics
        </p>
      </div>

      {/* Insights Grid */}
      {insightArray.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {insightArray.map((insight) => (
            <InsightCard
              key={insight.metadata.id}
              insight={insight}
              size="medium"
              onOpenNote={handleOpenNote}
            />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && insightArray.length === 0 && (
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <AlertCircle size={48} className="mx-auto mb-4" style={{ color: 'var(--color-text-secondary)' }} />
            <p className="text-lg font-semibold mb-2" style={{ color: 'var(--color-text)' }}>
              No Insights Available
            </p>
            <p className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
              No data found for the selected time range.
            </p>
          </div>
        </div>
      )}

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


