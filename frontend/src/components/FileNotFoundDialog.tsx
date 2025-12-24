/**
 * FileNotFoundDialog - Dialog shown when a file referenced by an insight doesn't exist
 *
 * Asks the user if they want to delete the insight since the file is missing.
 */

import React from 'react';
import { AlertCircle, X, Trash2 } from 'lucide-react';

interface FileNotFoundDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onDelete: () => void;
  filePath: string;
}

export default function FileNotFoundDialog({
  isOpen,
  onClose,
  onDelete,
  filePath
}: FileNotFoundDialogProps) {
  if (!isOpen) return null;

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ backgroundColor: 'rgba(0, 0, 0, 0.5)' }}
      onClick={handleBackdropClick}
    >
      <div
        className="w-full max-w-md rounded-lg shadow-xl"
        style={{
          backgroundColor: 'var(--color-surface)',
          border: '1px solid var(--color-border)'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="px-6 py-4 border-b flex items-center justify-between"
          style={{ borderColor: 'var(--color-border)' }}
        >
          <div className="flex items-center gap-3">
            <div
              className="p-2 rounded-lg"
              style={{
                backgroundColor: 'var(--color-error)20',
                color: 'var(--color-error)'
              }}
            >
              <AlertCircle size={20} />
            </div>
            <h2
              className="text-lg font-semibold"
              style={{ color: 'var(--color-text-primary)' }}
            >
              File Not Found
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg transition-colors hover:opacity-70"
            style={{ color: 'var(--color-text-secondary)' }}
            aria-label="Close dialog"
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="px-6 py-4">
          <p
            className="text-sm mb-4"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            The file referenced by this insight no longer exists:
          </p>
          <div
            className="p-3 rounded mb-4 font-mono text-sm break-all"
            style={{
              backgroundColor: 'var(--color-background)',
              border: '1px solid var(--color-border)',
              color: 'var(--color-text-primary)'
            }}
          >
            {filePath}
          </div>
          <p
            className="text-sm mb-4"
            style={{ color: 'var(--color-text-secondary)' }}
          >
            Would you like to delete this insight?
          </p>
        </div>

        {/* Actions */}
        <div
          className="px-6 py-4 border-t flex justify-end gap-3"
          style={{ borderColor: 'var(--color-border)' }}
        >
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
            style={{
              backgroundColor: 'var(--color-surface)',
              color: 'var(--color-text-primary)',
              border: '1px solid var(--color-border)'
            }}
          >
            Cancel
          </button>
          <button
            onClick={onDelete}
            className="px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2"
            style={{
              backgroundColor: 'var(--color-error)',
              color: 'white'
            }}
          >
            <Trash2 size={16} />
            Delete Insight
          </button>
        </div>
      </div>
    </div>
  );
}

