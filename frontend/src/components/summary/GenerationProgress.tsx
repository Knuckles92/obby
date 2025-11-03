import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  FileText,
  CheckCircle2,
  Circle,
  Loader2,
  Clock,
  ChevronDown,
  ChevronUp,
  Copy,
  X,
  AlertCircle,
  FileSearch,
  TrendingUp,
  Tag,
  Hash
} from 'lucide-react';

interface ProgressEvent {
  type: 'progress' | 'phase_change' | 'file_examined' | 'step' | 'complete' | 'error';
  phase?: string;
  currentFile?: string;
  filesExamined?: number;
  totalFiles?: number;
  progress?: number;
  message?: string;
  timestamp?: string;
  details?: any;
  error?: string;
}

interface GenerationProgressProps {
  isOpen: boolean;
  summaryType: 'session' | 'note';
  onComplete?: () => void;
  onError?: (error: string) => void;
  onCancel?: () => void;
}

interface PhaseInfo {
  id: number;
  name: string;
  description: string;
  status: 'completed' | 'current' | 'pending';
  timestamp?: string;
}

interface ActivityLog {
  id: string;
  timestamp: string;
  type: 'file_read' | 'analysis' | 'generation' | 'info';
  description: string;
  status: 'success' | 'info' | 'warning';
}

const PHASES = [
  { id: 1, name: 'Data Collection', description: 'Gathering changed files' },
  { id: 2, name: 'File Exploration', description: 'Claude reading files' },
  { id: 3, name: 'Analysis', description: 'Claude analyzing patterns' },
  { id: 4, name: 'Generation', description: 'Claude writing summary' }
];

export const GenerationProgress: React.FC<GenerationProgressProps> = ({
  isOpen,
  summaryType,
  onComplete,
  onError,
  onCancel
}) => {
  const [phases, setPhases] = useState<PhaseInfo[]>(
    PHASES.map(p => ({ ...p, status: 'pending' as const }))
  );
  const [currentPhase, setCurrentPhase] = useState<string>('Initializing');
  const [progress, setProgress] = useState<number>(0);
  const [currentFile, setCurrentFile] = useState<string>('');
  const [filesExamined, setFilesExamined] = useState<number>(0);
  const [totalFiles, setTotalFiles] = useState<number>(0);
  const [activities, setActivities] = useState<ActivityLog[]>([]);
  const [isDetailsExpanded, setIsDetailsExpanded] = useState<boolean>(false);
  const [startTime, setStartTime] = useState<Date>(new Date());
  const [elapsedTime, setElapsedTime] = useState<number>(0);
  const [estimatedTimeRemaining, setEstimatedTimeRemaining] = useState<number>(0);
  const [metrics, setMetrics] = useState({
    changesFound: 0,
    topicsIdentified: 0,
    keywordsExtracted: 0
  });
  const [errorMessage, setErrorMessage] = useState<string>('');
  const [isCompleted, setIsCompleted] = useState<boolean>(false);

  const eventSourceRef = useRef<EventSource | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  // Calculate elapsed time
  useEffect(() => {
    if (!isOpen || isCompleted) return;

    timerRef.current = setInterval(() => {
      const elapsed = Math.floor((new Date().getTime() - startTime.getTime()) / 1000);
      setElapsedTime(elapsed);

      // Estimate time remaining based on progress
      if (progress > 0 && progress < 100) {
        const totalEstimated = elapsed / (progress / 100);
        const remaining = totalEstimated - elapsed;
        setEstimatedTimeRemaining(Math.max(0, Math.floor(remaining)));
      }
    }, 1000);

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, [isOpen, startTime, progress, isCompleted]);

  // Connect to SSE
  useEffect(() => {
    if (!isOpen) return;

    const endpoint = summaryType === 'session'
      ? '/api/session-summary/events'
      : '/api/summary-notes/events';

    const eventSource = new EventSource(endpoint);
    eventSourceRef.current = eventSource;

    eventSource.onmessage = (event) => {
      try {
        const data: ProgressEvent = JSON.parse(event.data);
        handleProgressEvent(data);
      } catch (error) {
        console.error('Failed to parse SSE event:', error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE connection error:', error);
      setErrorMessage('Connection to server lost. Retrying...');
      eventSource.close();

      // Retry after 3 seconds
      setTimeout(() => {
        if (isOpen && !isCompleted) {
          const newEventSource = new EventSource(endpoint);
          eventSourceRef.current = newEventSource;
        }
      }, 3000);
    };

    return () => {
      eventSource.close();
      eventSourceRef.current = null;
    };
  }, [isOpen, summaryType, isCompleted]);

  const handleProgressEvent = useCallback((event: ProgressEvent) => {
    const timestamp = event.timestamp || new Date().toISOString();

    switch (event.type) {
      case 'phase_change':
        if (event.phase) {
          setCurrentPhase(event.phase);
          updatePhaseStatus(event.phase);
          addActivity({
            type: 'info',
            description: `Started phase: ${event.phase}`,
            status: 'info',
            timestamp
          });
        }
        break;

      case 'file_examined':
        if (event.currentFile) {
          setCurrentFile(event.currentFile);
          setFilesExamined(event.filesExamined || 0);
          setTotalFiles(event.totalFiles || 0);
          addActivity({
            type: 'file_read',
            description: `Reading: ${event.currentFile}`,
            status: 'success',
            timestamp
          });
        }
        break;

      case 'progress':
        if (typeof event.progress === 'number') {
          setProgress(event.progress);
        }
        if (event.message) {
          addActivity({
            type: 'info',
            description: event.message,
            status: 'info',
            timestamp
          });
        }
        // Update metrics if provided
        if (event.details) {
          setMetrics(prev => ({
            changesFound: event.details.changesFound ?? prev.changesFound,
            topicsIdentified: event.details.topicsIdentified ?? prev.topicsIdentified,
            keywordsExtracted: event.details.keywordsExtracted ?? prev.keywordsExtracted
          }));
        }
        break;

      case 'step':
        if (event.message) {
          addActivity({
            type: event.details?.type || 'info',
            description: event.message,
            status: 'info',
            timestamp
          });
        }
        break;

      case 'complete':
        setProgress(100);
        setIsCompleted(true);
        completeAllPhases();
        addActivity({
          type: 'generation',
          description: 'Summary generation completed successfully',
          status: 'success',
          timestamp
        });
        if (onComplete) {
          setTimeout(() => onComplete(), 1000);
        }
        break;

      case 'error':
        const errorMsg = event.error || event.message || 'An unknown error occurred';
        setErrorMessage(errorMsg);
        addActivity({
          type: 'info',
          description: `Error: ${errorMsg}`,
          status: 'warning',
          timestamp
        });
        if (onError) {
          onError(errorMsg);
        }
        break;
    }
  }, [onComplete, onError]);

  const updatePhaseStatus = (phaseName: string) => {
    setPhases(prevPhases => {
      const phaseIndex = PHASES.findIndex(p =>
        p.name.toLowerCase() === phaseName.toLowerCase()
      );

      if (phaseIndex === -1) return prevPhases;

      return prevPhases.map((phase, idx) => ({
        ...phase,
        status: idx < phaseIndex ? 'completed' : idx === phaseIndex ? 'current' : 'pending',
        timestamp: idx === phaseIndex ? new Date().toISOString() : phase.timestamp
      }));
    });
  };

  const completeAllPhases = () => {
    setPhases(prevPhases =>
      prevPhases.map(phase => ({
        ...phase,
        status: 'completed' as const,
        timestamp: phase.timestamp || new Date().toISOString()
      }))
    );
  };

  const addActivity = (activity: Omit<ActivityLog, 'id'>) => {
    setActivities(prev => [
      {
        ...activity,
        id: `${Date.now()}-${Math.random()}`
      },
      ...prev.slice(0, 9) // Keep last 10 items
    ]);
  };

  const formatTime = (seconds: number): string => {
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  const handleCopyLogs = () => {
    const logs = activities.map(a =>
      `[${new Date(a.timestamp).toLocaleTimeString()}] ${a.description}`
    ).join('\n');
    navigator.clipboard.writeText(logs);
  };

  const handleClose = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    if (onCancel) {
      onCancel();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-start">
          <div className="flex-1">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
              {currentPhase}
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Generating {summaryType === 'session' ? 'session' : 'note'} summary...
            </p>
          </div>
          <button
            onClick={handleClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
            aria-label="Close"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Error Message */}
        {errorMessage && (
          <div className="mx-6 mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-2">
            <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-red-800 dark:text-red-200">{errorMessage}</p>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-6">
          {/* Progress Bar */}
          <div className="space-y-2">
            <div className="flex justify-between items-center text-sm">
              <span className="font-medium text-gray-700 dark:text-gray-300">
                Progress: {progress}%
              </span>
              <div className="flex items-center gap-4 text-gray-600 dark:text-gray-400">
                <span className="flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  {formatTime(elapsedTime)}
                </span>
                {estimatedTimeRemaining > 0 && progress < 100 && (
                  <span className="text-xs">
                    ~{formatTime(estimatedTimeRemaining)} remaining
                  </span>
                )}
              </div>
            </div>
            <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
              <div
                className="bg-blue-600 dark:bg-blue-500 h-full rounded-full transition-all duration-500 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          {/* Phase Timeline */}
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
              Generation Phases
            </h3>
            <div className="space-y-2">
              {phases.map((phase, idx) => (
                <div key={phase.id} className="flex items-start gap-3">
                  <div className="flex-shrink-0 mt-0.5">
                    {phase.status === 'completed' ? (
                      <CheckCircle2 className="w-5 h-5 text-green-500" />
                    ) : phase.status === 'current' ? (
                      <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                    ) : (
                      <Circle className="w-5 h-5 text-gray-300 dark:text-gray-600" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-2">
                      <div>
                        <p className={`text-sm font-medium ${
                          phase.status === 'current'
                            ? 'text-blue-600 dark:text-blue-400'
                            : phase.status === 'completed'
                            ? 'text-gray-700 dark:text-gray-300'
                            : 'text-gray-400 dark:text-gray-500'
                        }`}>
                          {phase.name}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {phase.description}
                        </p>
                      </div>
                      {phase.timestamp && (
                        <span className="text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap">
                          {new Date(phase.timestamp).toLocaleTimeString()}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Current Activity Panel */}
          {currentFile && (
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
              <div className="flex items-start gap-3">
                <FileText className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-blue-900 dark:text-blue-100 mb-1">
                    Current Activity
                  </p>
                  <p className="text-sm text-blue-800 dark:text-blue-200 break-all">
                    Reading: <code className="font-mono text-xs bg-blue-100 dark:bg-blue-900/40 px-1 py-0.5 rounded">{currentFile}</code>
                  </p>
                  {totalFiles > 0 && (
                    <p className="text-xs text-blue-600 dark:text-blue-300 mt-2">
                      Files examined: {filesExamined} of {totalFiles}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Progress Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <FileSearch className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
                  Files Examined
                </span>
              </div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {filesExamined}
              </p>
            </div>
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <TrendingUp className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
                  Changes Found
                </span>
              </div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {metrics.changesFound}
              </p>
            </div>
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <Tag className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
                  Topics
                </span>
              </div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {metrics.topicsIdentified}
              </p>
            </div>
            <div className="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <Hash className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
                  Keywords
                </span>
              </div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {metrics.keywordsExtracted}
              </p>
            </div>
          </div>

          {/* Details/Logs Panel */}
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
            <button
              onClick={() => setIsDetailsExpanded(!isDetailsExpanded)}
              className="w-full px-4 py-3 bg-gray-50 dark:bg-gray-700/50 flex items-center justify-between hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Activity Log ({activities.length})
              </span>
              {isDetailsExpanded ? (
                <ChevronUp className="w-4 h-4 text-gray-500" />
              ) : (
                <ChevronDown className="w-4 h-4 text-gray-500" />
              )}
            </button>
            {isDetailsExpanded && (
              <div className="max-h-64 overflow-y-auto p-4 space-y-2 bg-white dark:bg-gray-800">
                {activities.length === 0 ? (
                  <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
                    No activities yet...
                  </p>
                ) : (
                  activities.map(activity => (
                    <div key={activity.id} className="flex items-start gap-2 text-sm">
                      <span className="text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap mt-0.5">
                        {new Date(activity.timestamp).toLocaleTimeString()}
                      </span>
                      <div className="flex-1 min-w-0">
                        <span className={`${
                          activity.status === 'success'
                            ? 'text-green-600 dark:text-green-400'
                            : activity.status === 'warning'
                            ? 'text-yellow-600 dark:text-yellow-400'
                            : 'text-gray-700 dark:text-gray-300'
                        }`}>
                          {activity.description}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-between items-center">
          <button
            onClick={handleCopyLogs}
            disabled={activities.length === 0}
            className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Copy className="w-4 h-4" />
            Copy Logs
          </button>
          {!isCompleted && onCancel && (
            <button
              onClick={onCancel}
              className="px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
            >
              Cancel Generation
            </button>
          )}
          {isCompleted && (
            <button
              onClick={handleClose}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
            >
              Close
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default GenerationProgress;
