import React, { useState, useEffect, useRef } from 'react';
import { useTheme } from '../../contexts/ThemeContext';

// Types for progress events
interface ProgressEvent {
  type: 'progress' | 'connection' | 'heartbeat' | 'error';
  session_id: string;
  timestamp: string;
  phase?: 'data_collection' | 'file_exploration' | 'analysis' | 'generation' | 'error';
  operation?: string;
  details?: Record<string, any>;
  files_processed?: number;
  total_files?: number;
  current_file?: string;
  timing?: Record<string, any>;
  message?: string;
  error?: string;
}

interface InsightsProgressDashboardProps {
  isVisible: boolean;
  onClose: () => void;
  insightsUrl?: string;
}

const InsightsProgressDashboard: React.FC<InsightsProgressDashboardProps> = ({
  isVisible,
  onClose,
  insightsUrl = '/api/insights/progress/events'
}) => {
  const { currentTheme } = useTheme();
  const isDark = currentTheme.name.toLowerCase().includes('dark');

  const [events, setEvents] = useState<ProgressEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPhase, setCurrentPhase] = useState<string>('');
  const [progress, setProgress] = useState({ files: 0, total: 0, percentage: 0 });
  const eventSourceRef = useRef<EventSource | null>(null);
  const eventsEndRef = useRef<HTMLDivElement>(null);

  // Phase configuration
  const phaseConfig = {
    data_collection: {
      label: 'Data Collection',
      icon: '📊',
      color: '#3b82f6',
      description: 'Gathering signals from various sources'
    },
    file_exploration: {
      label: 'File Exploration',
      icon: '🔍',
      color: '#10b981',
      description: 'AI is examining files to understand changes'
    },
    analysis: {
      label: 'AI Analysis',
      icon: '🧠',
      color: '#8b5cf6',
      description: 'Processing patterns and generating insights'
    },
    generation: {
      label: 'Generation',
      icon: '✨',
      color: '#f59e0b',
      description: 'Creating final insights output'
    },
    error: {
      label: 'Error',
      icon: '❌',
      color: '#ef4444',
      description: 'An error occurred during processing'
    }
  };

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (eventsEndRef.current) {
      eventsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [events]);

  // Connect to SSE endpoint when component becomes visible
  useEffect(() => {
    if (!isVisible) {
      // Close connection when hidden
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
        setIsConnected(false);
      }
      return;
    }

    const connectToProgressStream = () => {
      try {
        setError(null);
        const eventSource = new EventSource(insightsUrl);
        eventSourceRef.current = eventSource;

        eventSource.onopen = () => {
          console.log('Connected to insights progress stream');
          setIsConnected(true);
        };

        eventSource.onmessage = (event) => {
          try {
            const data: ProgressEvent = JSON.parse(event.data);

            setEvents(prev => {
              // Keep only last 50 events to prevent memory issues
              const newEvents = [...prev, data];
              return newEvents.slice(-50);
            });

            // Update current state
            if (data.phase) {
              setCurrentPhase(data.phase);
            }

            // Update progress
            if (data.files_processed !== undefined && data.total_files !== undefined) {
              const percentage = data.total_files > 0
                ? Math.round((data.files_processed / data.total_files) * 100)
                : 0;
              setProgress({
                files: data.files_processed,
                total: data.total_files,
                percentage
              });
            }

            // Auto-close on completion
            if (data.phase === 'generation' && data.operation === 'Generation complete') {
              setTimeout(() => {
                setIsConnected(false);
                if (eventSourceRef.current) {
                  eventSourceRef.current.close();
                  eventSourceRef.current = null;
                }
              }, 2000);
            }

          } catch (parseError) {
            console.error('Failed to parse SSE data:', parseError);
          }
        };

        eventSource.onerror = (event) => {
          console.error('SSE error:', event);
          setError('Connection to progress stream failed');
          setIsConnected(false);

          if (eventSourceRef.current) {
            eventSourceRef.current.close();
            eventSourceRef.current = null;
          }
        };

      } catch (err) {
        console.error('Failed to connect to progress stream:', err);
        setError('Failed to establish connection to progress stream');
        setIsConnected(false);
      }
    };

    connectToProgressStream();

    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [isVisible, insightsUrl]);

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString();
  };

  const getPhaseIcon = (phase: string) => {
    return phaseConfig[phase as keyof typeof phaseConfig]?.icon || '🔄';
  };

  const getPhaseColor = (phase: string) => {
    return phaseConfig[phase as keyof typeof phaseConfig]?.color || '#6b7280';
  };

  const getEventDescription = (event: ProgressEvent) => {
    if (event.message) return event.message;
    if (event.error) return `Error: ${event.error}`;
    if (event.operation) return event.operation;
    return event.type;
  };

  if (!isVisible) return null;

  return (
    <div className={`fixed inset-0 z-50 flex items-center justify-center ${
      isDark ? 'bg-black/50' : 'bg-black/30'
    }`}>
      <div className={`w-full max-w-4xl max-h-[90vh] overflow-hidden rounded-xl shadow-2xl ${
        isDark ? 'bg-gray-900 border-gray-700' : 'bg-white border-gray-200'
      } border`}>

        {/* Header */}
        <div className={`px-6 py-4 border-b ${
          isDark ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-gray-50'
        }`}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="text-2xl">🤖</div>
              <div>
                <h2 className={`text-xl font-semibold ${
                  isDark ? 'text-white' : 'text-gray-900'
                }`}>
                  AI Insights Generation
                </h2>
                <p className={`text-sm ${
                  isDark ? 'text-gray-400' : 'text-gray-600'
                }`}>
                  Real-time progress of AI analysis
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              {/* Connection status */}
              <div className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm ${
                isConnected
                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                  : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
              }`}>
                <div className={`w-2 h-2 rounded-full ${
                  isConnected ? 'bg-green-500' : 'bg-red-500'
                }`} />
                {isConnected ? 'Connected' : 'Disconnected'}
              </div>

              {/* Close button */}
              <button
                onClick={onClose}
                className={`p-2 rounded-lg transition-colors ${
                  isDark
                    ? 'hover:bg-gray-700 text-gray-400'
                    : 'hover:bg-gray-200 text-gray-600'
                }`}
              >
                ✕
              </button>
            </div>
          </div>
        </div>

        <div className="flex h-[calc(90vh-80px)]">
          {/* Main progress panel */}
          <div className="flex-1 p-6 overflow-y-auto">
            {/* Current phase indicator */}
            <div className="mb-6">
              <div className={`text-sm font-medium mb-2 ${
                isDark ? 'text-gray-400' : 'text-gray-600'
              }`}>
                Current Phase
              </div>

              {currentPhase && (
                <div className={`flex items-center gap-3 p-4 rounded-lg border-2`}
                     style={{ borderColor: getPhaseColor(currentPhase) }}>
                  <div className="text-3xl">
                    {getPhaseIcon(currentPhase)}
                  </div>
                  <div className="flex-1">
                    <div className="font-semibold text-lg"
                         style={{ color: getPhaseColor(currentPhase) }}>
                      {phaseConfig[currentPhase as keyof typeof phaseConfig]?.label}
                    </div>
                    <div className={`text-sm ${
                      isDark ? 'text-gray-400' : 'text-gray-600'
                    }`}>
                      {phaseConfig[currentPhase as keyof typeof phaseConfig]?.description}
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Progress indicator */}
            {progress.total > 0 && (
              <div className="mb-6">
                <div className={`text-sm font-medium mb-2 ${
                  isDark ? 'text-gray-400' : 'text-gray-600'
                }`}>
                  File Processing Progress
                </div>

                <div className={`w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden`}>
                  <div
                    className="h-full transition-all duration-300 ease-out"
                    style={{
                      width: `${progress.percentage}%`,
                      backgroundColor: getPhaseColor(currentPhase)
                    }}
                  />
                </div>

                <div className={`flex justify-between mt-2 text-sm ${
                  isDark ? 'text-gray-400' : 'text-gray-600'
                }`}>
                  <span>{progress.files} files processed</span>
                  <span>{progress.total} total files</span>
                  <span>{progress.percentage}%</span>
                </div>
              </div>
            )}

            {/* Current operation */}
            {events.length > 0 && (
              <div className="mb-6">
                <div className={`text-sm font-medium mb-2 ${
                  isDark ? 'text-gray-400' : 'text-gray-600'
                }`}>
                  Current Operation
                </div>

                <div className={`p-3 rounded-lg ${
                  isDark ? 'bg-gray-800' : 'bg-gray-100'
                }`}>
                  <div className={`font-mono text-sm ${
                    isDark ? 'text-gray-300' : 'text-gray-700'
                  }`}>
                    {events[events.length - 1]?.operation || 'Initializing...'}
                  </div>

                  {events[events.length - 1]?.current_file && (
                    <div className={`text-xs mt-1 ${
                      isDark ? 'text-gray-500' : 'text-gray-500'
                    }`}>
                      File: {events[events.length - 1].current_file}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Error display */}
            {error && (
              <div className="mb-6 p-4 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
                <div className="flex items-center gap-2 text-red-700 dark:text-red-400">
                  <span>❌</span>
                  <span className="font-medium">Connection Error</span>
                </div>
                <div className="text-sm text-red-600 dark:text-red-300 mt-1">
                  {error}
                </div>
              </div>
            )}
          </div>

          {/* Events timeline */}
          <div className={`w-80 border-l ${
            isDark ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-gray-50'
          }`}>
            <div className={`p-4 border-b ${
              isDark ? 'border-gray-700' : 'border-gray-200'
            }`}>
              <h3 className={`font-semibold ${
                isDark ? 'text-white' : 'text-gray-900'
              }`}>
                Event Timeline
              </h3>
              <p className={`text-xs mt-1 ${
                isDark ? 'text-gray-400' : 'text-gray-600'
              }`}>
                Latest events from AI analysis
              </p>
            </div>

            <div className="p-4 overflow-y-auto h-[calc(90vh-200px)]">
              {events.length === 0 ? (
                <div className={`text-center py-8 ${
                  isDark ? 'text-gray-500' : 'text-gray-400'
                }`}>
                  <div className="text-2xl mb-2">⏳</div>
                  <div className="text-sm">Waiting for events...</div>
                </div>
              ) : (
                <div className="space-y-3">
                  {events.slice(-20).reverse().map((event, index) => (
                    <div
                      key={`${event.timestamp}-${index}`}
                      className={`p-3 rounded-lg border ${
                        isDark ? 'border-gray-700 bg-gray-900' : 'border-gray-200 bg-white'
                      }`}
                    >
                      <div className="flex items-start gap-2">
                        <div className="text-lg">
                          {getPhaseIcon(event.phase || 'data_collection')}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className={`font-medium text-sm truncate ${
                            isDark ? 'text-gray-200' : 'text-gray-800'
                          }`}>
                            {getEventDescription(event)}
                          </div>
                          <div className={`text-xs mt-1 ${
                            isDark ? 'text-gray-500' : 'text-gray-400'
                          }`}>
                            {formatTimestamp(event.timestamp)}
                          </div>

                          {event.details && Object.keys(event.details).length > 0 && (
                            <div className={`text-xs mt-2 ${
                              isDark ? 'text-gray-600' : 'text-gray-500'
                            }`}>
                              {Object.entries(event.details).slice(0, 2).map(([key, value]) => (
                                <div key={key}>
                                  {key}: {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}

                  <div ref={eventsEndRef} />
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InsightsProgressDashboard;