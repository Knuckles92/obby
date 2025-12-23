/**
 * Reusable Insight Card Component
 *
 * Displays an insight with its data, metadata, and optional visualizations.
 * Automatically adapts to different data schemas from various insight types.
 */

import React from 'react';
import * as Icons from 'lucide-react';

export interface InsightMetadata {
  id: string;
  title: string;
  description: string;
  icon: string;
  color: string;
  category: string;
  defaultSize: string;
  supportsDrillDown: boolean;
}

export interface InsightData {
  value: string | number;
  label?: string;
  trend?: 'up' | 'down' | 'stable';
  trendValue?: number;
  chart?: {
    type: string;
    data: any;
  };
  details?: any;
  status?: 'success' | 'warning' | 'error';
  message?: string;
}

export interface InsightResult {
  data: InsightData;
  metadata: InsightMetadata;
  calculatedAt: string;
  error?: string;
}

interface InsightCardProps {
  insight: InsightResult;
  className?: string;
  size?: 'small' | 'medium' | 'large';
  onDrillDown?: () => void;
  onOpenNote?: (path: string) => void;
}

export const InsightCard: React.FC<InsightCardProps> = ({
  insight,
  className = '',
  size = 'medium',
  onDrillDown,
  onOpenNote
}) => {
  const { data, metadata, error } = insight;

  // Get the icon component dynamically
  const IconComponent = (Icons as any)[metadata.icon] || Icons.Activity;

  // Determine status color
  const getStatusColor = () => {
    if (error) return 'var(--color-error)';
    if (data.status === 'error') return 'var(--color-error)';
    if (data.status === 'warning') return 'var(--color-warning)';
    return metadata.color;
  };

  // Render trend indicator
  const renderTrend = () => {
    if (!data.trend || data.trend === 'stable') return null;

    const isUp = data.trend === 'up';
    const TrendIcon = isUp ? Icons.TrendingUp : Icons.TrendingDown;
    const trendColor = isUp ? 'var(--color-success)' : 'var(--color-error)';

    return (
      <div className="flex items-center gap-1 text-sm" style={{ color: trendColor }}>
        <TrendIcon size={16} />
        {data.trendValue !== undefined && (
          <span>{Math.abs(data.trendValue)}%</span>
        )}
      </div>
    );
  };

  // Render chart based on type
  const renderChart = () => {
    if (!data.chart) return null;

    const { type, data: chartData } = data.chart;

    switch (type) {
      case 'bar':
        return <BarChart data={chartData} onOpenNote={onOpenNote} />;
      case 'comparison':
        return <ComparisonChart data={chartData} />;
      case 'list':
        return <ListChart data={chartData} onOpenNote={onOpenNote} />;
      default:
        return null;
    }
  };

  // Size classes
  const sizeClasses = {
    small: 'p-4',
    medium: 'p-5',
    large: 'p-6'
  };

  return (
    <div
      className={`insight-card rounded-lg shadow-sm border transition-all hover:shadow-md ${sizeClasses[size]} ${className}`}
      style={{
        backgroundColor: 'var(--color-card)',
        borderColor: 'var(--color-border)'
      }}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div
            className="p-2 rounded-lg"
            style={{
              backgroundColor: `${getStatusColor()}20`,
              color: getStatusColor()
            }}
          >
            <IconComponent size={20} />
          </div>
          <div>
            <h3 className="text-sm font-medium" style={{ color: 'var(--color-text)' }}>
              {metadata.title}
            </h3>
            <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
              {metadata.description}
            </p>
          </div>
        </div>
        {renderTrend()}
      </div>

      {/* Error State */}
      {error && (
        <div className="p-3 rounded bg-red-50 border border-red-200 text-red-700 text-sm">
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Main Value */}
      {!error && (
        <div className="mb-4">
          <div className="flex items-baseline gap-2">
            <span
              className="text-3xl font-bold"
              style={{ color: getStatusColor() }}
            >
              {data.value}
            </span>
            {data.label && (
              <span className="text-sm" style={{ color: 'var(--color-text-secondary)' }}>
                {data.label}
              </span>
            )}
          </div>
          {data.message && (
            <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
              {data.message}
            </p>
          )}
        </div>
      )}

      {/* Chart */}
      {!error && renderChart()}

      {/* Details */}
      {!error && data.details && (
        <div className="mt-4 pt-4 border-t" style={{ borderColor: 'var(--color-border)' }}>
          <DetailsSection details={data.details} />
        </div>
      )}

      {/* Drill Down Button */}
      {metadata.supportsDrillDown && onDrillDown && (
        <button
          onClick={onDrillDown}
          className="mt-4 w-full py-2 px-4 rounded text-sm font-medium transition-colors"
          style={{
            backgroundColor: 'var(--color-background-secondary)',
            color: 'var(--color-text)'
          }}
        >
          View Details →
        </button>
      )}
    </div>
  );
};

// Bar Chart Component
const BarChart: React.FC<{ data: any[]; onOpenNote?: (path: string) => void }> = ({ data, onOpenNote }) => {
  if (!data || data.length === 0) return null;

  const maxValue = Math.max(...data.map((d: any) => d.value || 0));

  return (
    <div className="space-y-2">
      {data.slice(0, 7).map((item: any, idx: number) => {
        const path = item.path || item.filePath;
        const isClickable = !!(path && onOpenNote);

        return (
          <div 
            key={idx} 
            className={`flex items-center gap-2 ${isClickable ? 'cursor-pointer hover:opacity-80' : ''}`}
            onClick={() => isClickable && onOpenNote(path)}
          >
            <span className="text-xs w-12 truncate" style={{ color: 'var(--color-text-secondary)' }} title={item.label || item.hour}>
              {item.hour || item.label}
            </span>
            <div className="flex-1 h-6 bg-gray-100 dark:bg-gray-800 rounded overflow-hidden">
              <div
                className="h-full transition-all"
                style={{
                  width: `${(item.value / maxValue) * 100}%`,
                  backgroundColor: 'var(--color-primary)'
                }}
              />
            </div>
            <span className="text-xs w-8 text-right" style={{ color: 'var(--color-text-secondary)' }}>
              {item.value}
            </span>
          </div>
        );
      })}
    </div>
  );
};

// Comparison Chart Component
const ComparisonChart: React.FC<{ data: any }> = ({ data }) => {
  if (!data) return null;

  const { added, removed, net } = data;

  return (
    <div className="space-y-2">
      <div className="flex justify-between items-center">
        <span className="text-sm" style={{ color: 'var(--color-success)' }}>
          <Icons.Plus size={14} className="inline" /> Added
        </span>
        <span className="font-medium">{added?.toLocaleString() || 0}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm" style={{ color: 'var(--color-error)' }}>
          <Icons.Minus size={14} className="inline" /> Removed
        </span>
        <span className="font-medium">{removed?.toLocaleString() || 0}</span>
      </div>
      {net !== undefined && (
        <div className="flex justify-between items-center pt-2 border-t" style={{ borderColor: 'var(--color-border)' }}>
          <span className="text-sm font-medium">Net Change</span>
          <span className="font-bold" style={{ color: net >= 0 ? 'var(--color-success)' : 'var(--color-error)' }}>
            {net >= 0 ? '+' : ''}{net.toLocaleString()}
          </span>
        </div>
      )}
    </div>
  );
};

// List Chart Component
const ListChart: React.FC<{ data: any[]; onOpenNote?: (path: string) => void }> = ({ data, onOpenNote }) => {
  if (!data || data.length === 0) return null;

  return (
    <div className="space-y-2">
      {data.slice(0, 5).map((item: any, idx: number) => {
        const path = item.path || item.filePath;
        const isClickable = !!(path && onOpenNote);

        return (
          <div 
            key={idx} 
            className={`flex justify-between items-center text-sm ${isClickable ? 'cursor-pointer hover:underline' : ''}`}
            onClick={() => isClickable && onOpenNote(path)}
          >
            <span style={{ color: 'var(--color-text)' }} className="truncate flex-1 mr-2">
              {item.name || item.path}
            </span>
            <span className="font-medium" style={{ color: 'var(--color-text-secondary)' }}>
              {item.changeCount || item.count}
            </span>
          </div>
        );
      })}
    </div>
  );
};

// Details Section Component
const DetailsSection: React.FC<{ details: any }> = ({ details }) => {
  if (!details || typeof details !== 'object') return null;

  return (
    <div className="grid grid-cols-2 gap-3 text-sm">
      {Object.entries(details).map(([key, value]) => {
        // Skip nested objects for now
        if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
          return null;
        }

        const formattedKey = key.replace(/([A-Z])/g, ' $1').trim();
        const capitalizedKey = formattedKey.charAt(0).toUpperCase() + formattedKey.slice(1);

        return (
          <div key={key}>
            <div className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
              {capitalizedKey}
            </div>
            <div className="font-medium" style={{ color: 'var(--color-text)' }}>
              {typeof value === 'number' ? value.toLocaleString() : String(value)}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default InsightCard;
