import { useState, useCallback, useEffect } from 'react';

interface ModalData {
  insight?: any;
  logs?: any[];
  [key: string]: any;
}

interface ModalManagerReturn {
  activeModal: string | null;
  modalData: ModalData | null;
  openModal: (modalType: string, data?: ModalData) => void;
  closeModal: () => void;
  openEnhancedEvidence: (insight: any) => void;
  openAgentTimeline: (insight: any, logs?: any[]) => void;
  openProvenanceDisplay: (insight: any) => void;
  openTransparencyPreferences: () => void;
  openProgressDashboard: () => void;
}

export const useModalManager = (): ModalManagerReturn => {
  const [activeModal, setActiveModal] = useState<string | null>(null);
  const [modalData, setModalData] = useState<ModalData | null>(null);

  const openModal = useCallback((modalType: string, data?: ModalData) => {
    setActiveModal(modalType);
    setModalData(data || null);
  }, []);

  const closeModal = useCallback(() => {
    setActiveModal(null);
    setModalData(null);
  }, []);

  // Specific modal openers for better type safety
  const openEnhancedEvidence = useCallback((insight: any) => {
    openModal('enhanced-evidence', { insight });
  }, [openModal]);

  const openAgentTimeline = useCallback((insight: any, logs?: any[]) => {
    openModal('agent-timeline', { insight, logs: logs || [] });
  }, [openModal]);

  const openProvenanceDisplay = useCallback((insight: any) => {
    openModal('provenance-display', { insight });
  }, [openModal]);

  const openTransparencyPreferences = useCallback(() => {
    openModal('transparency-preferences');
  }, [openModal]);

  const openProgressDashboard = useCallback(() => {
    openModal('progress-dashboard');
  }, [openModal]);

  // Global keyboard handler
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        closeModal();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [closeModal]);

  // Global click-outside handler
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as Element;

      // Check if click is on modal backdrop (outside modal content)
      if (target.classList.contains('modal-backdrop')) {
        closeModal();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [closeModal]);

  return {
    activeModal,
    modalData,
    openModal,
    closeModal,
    openEnhancedEvidence,
    openAgentTimeline,
    openProvenanceDisplay,
    openTransparencyPreferences,
    openProgressDashboard
  };
};