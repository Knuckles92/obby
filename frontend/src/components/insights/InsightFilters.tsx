import React from 'react';
import { useTheme } from '../../contexts/ThemeContext';

interface InsightFiltersProps {
  filter: string;
  setFilter: (filter: string) => void;
  timeRange: number;
  setTimeRange: (range: number) => void;
  includeDismissed: boolean;
  setIncludeDismissed: (include: boolean) => void;
  insights: any[];
  categoryConfig: Record<string, any>;
}

const InsightFilters: React.FC<InsightFiltersProps> = ({
  filter,
  setFilter,
  timeRange,
  setTimeRange,
  includeDismissed,
  setIncludeDismissed,
  insights,
  categoryConfig
}) => {
  const { currentTheme } = useTheme();
  const isDark = currentTheme.name.toLowerCase().includes('dark');

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          Filters
        </h2>
        <div className="flex gap-4 items-center">
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {insights.length} insights
          </div>
          <div className="flex gap-2">
            <select
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className={`px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm focus:ring-2 focus:ring-blue-500 
                       bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                       ${isDark ? 'border-gray-600' : 'border-gray-300'}`}
            >
              <option value="all">All Categories</option>
              {Object.entries(categoryConfig).map(([key, config]) => (
                <option key={key} value={key}>{config.label}</option>
              ))}
            </select>
            
            <select
              value={timeRange}
              onChange={(e) => setTimeRange(Number(e.target.value))}
              className={`px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md text-sm focus:ring-2 focus:ring-blue-500 
                       bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100
                       ${isDark ? 'border-gray-600' : 'border-gray-300'}`}
            >
              <option value={3}>Last 3 days</option>
              <option value={7}>Last 7 days</option>
              <option value={14}>Last 14 days</option>
              <option value={30}>Last 30 days</option>
            </select>
            
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={includeDismissed}
                onChange={(e) => setIncludeDismissed(e.target.checked)}
                className="mr-2 h-4 w-4 text-blue-600 rounded focus:ring-blue-500 
                       border-gray-300 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-100"
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">Include Dismissed</span>
            </label>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InsightFilters;