/**
 * MasonryLayout - Real-time insights display with backend data
 *
 * This layout fetches real insights from the backend and displays them
 * using the reusable InsightCard component. Also includes semantic insights
 * section for AI-powered analysis.
 */

import React, { useState } from 'react';
import { Sparkles, RefreshCw, Trash2, FilePlus } from 'lucide-react';
import { SemanticInsightsSection } from '../semantic-insights';
import { NoteViewerModal, FileNotFoundDialog } from '../modals';
import { checkFileExists } from '../../utils/fileOperations';
import { useSemanticInsights } from '../../hooks/useInsights';

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
  const [displayLimit, setDisplayLimit] = useState(6);
  
  // Individual loading states for each button
  const [isClearingInsights, setIsClearingInsights] = useState(false);
  const [isIncrementalScanning, setIsIncrementalScanning] = useState(false);
  const [isFullScanning, setIsFullScanning] = useState(false);

  const { performAction, refetch: refetchSemanticInsights, clearInsights, triggerProcessing, triggerIncrementalProcessing, insights, meta } = useSemanticInsights({
    status: undefined,
    limit: displayLimit
  });

  // Filter to only show new, viewed, and pinned insights
  const visibleInsights = insights.filter(
    i => ['new', 'viewed', 'pinned'].includes(i.status)
  );

  // Check if any operation is in progress
  const isAnyProcessing = isClearingInsights || isIncrementalScanning || isFullScanning;

  const handleClearInsights = async () => {
    setIsClearingInsights(true);
    await clearInsights();
    setIsClearingInsights(false);
    await refetchSemanticInsights();
  };

  const handleIncrementalScan = async () => {
    setIsIncrementalScanning(true);
    await triggerIncrementalProcessing();
    setIsIncrementalScanning(false);
    await refetchSemanticInsights();
  };

  const handleFullScan = async () => {
    setIsFullScanning(true);
    await triggerProcessing();
    setIsFullScanning(false);
    await refetchSemanticInsights();
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
                <Sparkles className="h-6 w-6" />
              </div>
              <h1 className="text-3xl font-bold tracking-tight">Insights</h1>
            </div>
            <p className="text-blue-100 text-lg">
              AI-powered semantic insights and analysis
              {dateRange.days && ` (Last ${dateRange.days} days)`}
            </p>
          </div>

          {/* Actions - Button Group */}
          <div className="flex items-center gap-2 flex-wrap">
            <select
              value={displayLimit}
              onChange={(e) => setDisplayLimit(Number(e.target.value))}
              className="px-2 py-1.5 text-sm rounded-lg bg-white/20 border border-white/30 text-white backdrop-blur-sm"
            >
              <option value={6} className="bg-gray-800">6 items</option>
              <option value={12} className="bg-gray-800">12 items</option>
              <option value={18} className="bg-gray-800">18 items</option>
              <option value={24} className="bg-gray-800">24 items</option>
            </select>

            {/* Clear Insights Button */}
            <div className="relative group">
              <button
                onClick={handleClearInsights}
                disabled={isAnyProcessing || visibleInsights.length === 0}
                className={`relative overflow-hidden px-4 py-2 rounded-xl font-semibold transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 ${
                  isClearingInsights
                    ? 'bg-white/10 border border-white/20 text-white'
                    : 'bg-white/20 hover:bg-white/30 border border-white/30 text-white'
                }`}
              >
                <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/20 to-white/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700"></div>
                <Trash2 size={14} className={isClearingInsights ? 'animate-pulse' : ''} />
                <span>{isClearingInsights ? 'Clearing...' : 'Clear'}</span>
              </button>
              <div className="absolute right-full top-1/2 -translate-y-1/2 mr-2 z-[9999] opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 pointer-events-none">
                <div className="px-4 py-3 rounded-xl shadow-2xl backdrop-blur-lg bg-black/80 border border-white/30 text-white min-w-[240px]">
                  <div className="font-semibold mb-1 text-sm text-white">Clear Insights</div>
                  <div className="text-xs text-white/90 leading-relaxed">
                    Remove all non-pinned insights. Pinned insights will be preserved.
                  </div>
                </div>
              </div>
            </div>

            {/* Scan for New Notes Button */}
            <div className="relative group">
              <button
                onClick={handleIncrementalScan}
                disabled={isAnyProcessing}
                className={`relative overflow-hidden px-4 py-2 rounded-xl font-semibold transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 ${
                  isIncrementalScanning
                    ? 'bg-white/10 border border-white/20 text-white'
                    : 'bg-white/20 hover:bg-white/30 border border-white/30 text-white'
                }`}
              >
                <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/20 to-white/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700"></div>
                <FilePlus size={14} className={isIncrementalScanning ? 'animate-spin' : ''} />
                <span>{isIncrementalScanning ? 'Scanning...' : 'Scan New'}</span>
              </button>
              <div className="absolute right-full top-1/2 -translate-y-1/2 mr-2 z-[9999] opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 pointer-events-none">
                <div className="px-4 py-3 rounded-xl shadow-2xl backdrop-blur-lg bg-black/80 border border-white/30 text-white min-w-[240px]">
                  <div className="font-semibold mb-1 text-sm text-white">Scan for New Notes</div>
                  <div className="text-xs text-white/90 leading-relaxed">
                    Process only notes that have changed since last scan. Existing insights are preserved.
                  </div>
                </div>
              </div>
            </div>

            {/* Full Scan Button */}
            <div className="relative group">
              <button
                onClick={handleFullScan}
                disabled={isAnyProcessing}
                className={`relative overflow-hidden px-4 py-2 rounded-xl font-semibold transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 ${
                  isFullScanning
                    ? 'bg-white/10 border border-white/20 text-white'
                    : 'bg-white/20 hover:bg-white/30 border border-white/30 text-white'
                }`}
              >
                <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/20 to-white/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700"></div>
                <RefreshCw size={14} className={isFullScanning ? 'animate-spin' : ''} />
                <span>{isFullScanning ? 'Scanning...' : 'Full Scan'}</span>
              </button>
              <div className="absolute right-full top-1/2 -translate-y-1/2 mr-2 z-[9999] opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 pointer-events-none">
                <div className="px-4 py-3 rounded-xl shadow-2xl backdrop-blur-lg bg-black/80 border border-white/30 text-white min-w-[240px]">
                  <div className="font-semibold mb-1 text-sm text-white">Full Scan & Replace</div>
                  <div className="text-xs text-white/90 leading-relaxed">
                    Scan all changed notes and replace all non-pinned insights with fresh analysis.
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Semantic Insights Section */}
      <SemanticInsightsSection 
        onOpenNote={handleOpenNote}
        displayLimit={displayLimit}
        onClearInsights={handleClearInsights}
        onIncrementalScan={handleIncrementalScan}
        onFullScan={handleFullScan}
        isClearingInsights={isClearingInsights}
        isIncrementalScanning={isIncrementalScanning}
        isFullScanning={isFullScanning}
        isAnyProcessing={isAnyProcessing}
        visibleInsightsCount={visibleInsights.length}
        onRefetch={refetchSemanticInsights}
      />

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


