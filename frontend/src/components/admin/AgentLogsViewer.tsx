import React, { useState, useEffect } from 'react';
import { Activity, BarChart3, History, Trash2 } from 'lucide-react';

interface AgentLog {
  id: number;
  session_id: string;
  phase: string;
  operation: string;
  timestamp: string;
  files_processed?: number;
  total_files?: number;
  current_file?: string;
}

interface AgentSession {
  session_id: string;
  start_time: string;
  end_time: string;
  operation_count: number;
  files_processed: number;
  phases: string[];
}

interface Stats {
  total_logs: number;
  last_24_hours: {
    operations: number;
    phase_distribution: Record<string, number>;
    operation_types: Record<string, number>;
    avg_duration_ms: number;
  };
  tool_usage: {
    tool_usage: Record<string, number>;
    total_operations: number;
  };
}

export const AgentLogsViewer: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'sessions' | 'statistics'>('sessions');
  const [sessions, setSessions] = useState<AgentSession[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  // Fetch sessions
  const fetchSessions = async () => {
    setLoading(true);
    try {
      const response = await fetch(`/api/admin/agent-logs/sessions?page=${page}&page_size=20`);
      const data = await response.json();
      setSessions(data.sessions || []);
      setTotalPages(data.pagination?.total_pages || 1);
    } catch (error) {
      console.error('Failed to fetch sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  // Fetch statistics
  const fetchStats = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/admin/agent-logs/stats');
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'sessions') {
      fetchSessions();
    } else if (activeTab === 'statistics') {
      fetchStats();
    }
  }, [activeTab, page]);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  const formatDuration = (start: string, end: string) => {
    const diff = new Date(end).getTime() - new Date(start).getTime();
    const seconds = Math.floor(diff / 1000);
    if (seconds < 60) return `${seconds}s`;
    const minutes = Math.floor(seconds / 60);
    return `${minutes}m ${seconds % 60}s`;
  };

  const getPhaseColor = (phase: string) => {
    const colors: Record<string, string> = {
      data_collection: 'bg-blue-100 text-blue-800',
      file_exploration: 'bg-purple-100 text-purple-800',
      analysis: 'bg-yellow-100 text-yellow-800',
      generation: 'bg-green-100 text-green-800',
      error: 'bg-red-100 text-red-800',
    };
    return colors[phase] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-gray-800">Agent Activity Logs</h2>
          <p className="text-sm text-gray-600 mt-1">
            Monitor and analyze Claude Agent SDK operations
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex space-x-2 border-b border-gray-200">
        <button
          onClick={() => setActiveTab('sessions')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'sessions'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 hover:text-gray-800'
          }`}
        >
          <div className="flex items-center space-x-2">
            <History className="w-4 h-4" />
            <span>Session History</span>
          </div>
        </button>
        <button
          onClick={() => setActiveTab('statistics')}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === 'statistics'
              ? 'text-blue-600 border-b-2 border-blue-600'
              : 'text-gray-600 hover:text-gray-800'
          }`}
        >
          <div className="flex items-center space-x-2">
            <BarChart3 className="w-4 h-4" />
            <span>Statistics</span>
          </div>
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      ) : (
        <>
          {/* Sessions Tab */}
          {activeTab === 'sessions' && (
            <div className="space-y-4">
              {sessions.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  <Activity className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No agent sessions found</p>
                  <p className="text-sm mt-2">Agent operations will appear here once they start</p>
                </div>
              ) : (
                <>
                  <div className="bg-white rounded-lg shadow overflow-hidden">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Session
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Start Time
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Duration
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Operations
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Files
                          </th>
                          <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                            Phases
                          </th>
                        </tr>
                      </thead>
                      <tbody className="bg-white divide-y divide-gray-200">
                        {sessions.map((session) => (
                          <tr key={session.session_id} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900">
                              {session.session_id.substring(0, 8)}...
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {formatDate(session.start_time)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {formatDuration(session.start_time, session.end_time)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {session.operation_count}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {session.files_processed}
                            </td>
                            <td className="px-6 py-4">
                              <div className="flex flex-wrap gap-1">
                                {session.phases.map((phase, idx) => (
                                  <span
                                    key={idx}
                                    className={`px-2 py-1 text-xs rounded ${getPhaseColor(phase)}`}
                                  >
                                    {phase}
                                  </span>
                                ))}
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* Pagination */}
                  {totalPages > 1 && (
                    <div className="flex items-center justify-between">
                      <button
                        onClick={() => setPage((p) => Math.max(1, p - 1))}
                        disabled={page === 1}
                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Previous
                      </button>
                      <span className="text-sm text-gray-700">
                        Page {page} of {totalPages}
                      </span>
                      <button
                        onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                        disabled={page === totalPages}
                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Next
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* Statistics Tab */}
          {activeTab === 'statistics' && stats && (
            <div className="space-y-4">
              {/* Summary Cards */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white rounded-lg shadow p-6">
                  <div className="text-sm font-medium text-gray-600">Total Operations</div>
                  <div className="text-3xl font-bold text-gray-900 mt-2">{stats.total_logs}</div>
                </div>
                <div className="bg-white rounded-lg shadow p-6">
                  <div className="text-sm font-medium text-gray-600">Last 24 Hours</div>
                  <div className="text-3xl font-bold text-gray-900 mt-2">
                    {stats.last_24_hours.operations}
                  </div>
                </div>
                <div className="bg-white rounded-lg shadow p-6">
                  <div className="text-sm font-medium text-gray-600">Avg Duration</div>
                  <div className="text-3xl font-bold text-gray-900 mt-2">
                    {(stats.last_24_hours.avg_duration_ms / 1000).toFixed(1)}s
                  </div>
                </div>
              </div>

              {/* Tool Usage */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Tool Usage (24h)</h3>
                <div className="space-y-3">
                  {Object.entries(stats.tool_usage.tool_usage).map(([tool, count]) => (
                    <div key={tool} className="flex items-center">
                      <div className="w-24 text-sm font-medium text-gray-700">{tool}</div>
                      <div className="flex-1 mx-4">
                        <div className="bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-600 h-2 rounded-full"
                            style={{
                              width: `${(count / stats.tool_usage.total_operations) * 100}%`,
                            }}
                          ></div>
                        </div>
                      </div>
                      <div className="w-16 text-right text-sm text-gray-600">{count}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Operation Types */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Operation Types (24h)</h3>
                <div className="space-y-3">
                  {Object.entries(stats.last_24_hours.operation_types).map(([type, count]) => (
                    <div key={type} className="flex items-center">
                      <div className="w-32 text-sm font-medium text-gray-700 capitalize">
                        {type}
                      </div>
                      <div className="flex-1 mx-4">
                        <div className="bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-green-600 h-2 rounded-full"
                            style={{
                              width: `${(count / stats.last_24_hours.operations) * 100}%`,
                            }}
                          ></div>
                        </div>
                      </div>
                      <div className="w-16 text-right text-sm text-gray-600">{count}</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};
