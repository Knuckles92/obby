import React from 'react';
import { useTheme } from '../../contexts/ThemeContext';

interface BaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
  maxWidth?: string;
  maxHeight?: string;
  showCloseButton?: boolean;
  preventCloseOnBackdrop?: boolean;
}

const BaseModal: React.FC<BaseModalProps> = ({
  isOpen,
  onClose,
  title,
  children,
  maxWidth = 'max-w-4xl',
  maxHeight = 'max-h-[90vh]',
  showCloseButton = true,
  preventCloseOnBackdrop = false
}) => {
  const { currentTheme } = useTheme();
  const isDark = currentTheme.name.toLowerCase().includes('dark');

  if (!isOpen) return null;

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget && !preventCloseOnBackdrop) {
      onClose();
    }
  };

  const handleClose = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onClose();
  };

  return (
    <div
      className={`fixed inset-0 z-50 flex items-center justify-center modal-backdrop ${
        isDark ? 'bg-black/50' : 'bg-black/30'
      }`}
      onClick={handleBackdropClick}
    >
      <div
        className={`w-full ${maxWidth} ${maxHeight} overflow-hidden rounded-xl shadow-2xl ${
          isDark ? 'bg-gray-900 border-gray-700' : 'bg-white border-gray-200'
        } border`}
        data-modal
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className={`px-6 py-4 border-b ${
          isDark ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-gray-50'
        }`}>
          <div className="flex items-center justify-between">
            <h2 className={`text-xl font-semibold ${
              isDark ? 'text-white' : 'text-gray-900'
            }`}>
              {title}
            </h2>

            {showCloseButton && (
              <button
                onClick={handleClose}
                className={`p-2 rounded-lg transition-colors ${
                  isDark
                    ? 'hover:bg-gray-700 text-gray-400'
                    : 'hover:bg-gray-200 text-gray-600'
                }`}
                aria-label="Close modal"
              >
                ✕
              </button>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="overflow-y-auto" style={{ height: 'calc(90vh - 80px)' }}>
          {children}
        </div>
      </div>
    </div>
  );
};

export default BaseModal;