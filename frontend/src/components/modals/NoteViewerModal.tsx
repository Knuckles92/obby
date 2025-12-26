import React from 'react';
import BaseModal from './BaseModal';
import NoteEditor from '../NoteEditor';

interface NoteViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  filePath: string | null;
}

const NoteViewerModal: React.FC<NoteViewerModalProps> = ({
  isOpen,
  onClose,
  filePath
}) => {
  // Extract filename for the title
  const fileName = filePath ? filePath.split(/[/\\]/).pop() || 'Note' : 'Note';

  return (
    <BaseModal
      isOpen={isOpen}
      onClose={onClose}
      title={fileName}
      maxWidth="max-w-5xl"
    >
      <div className="h-[calc(90vh-80px)]">
        <NoteEditor
          filePath={filePath}
          onClose={onClose}
          onSave={() => {
            // Optional: Handle save event if needed
          }}
        />
      </div>
    </BaseModal>
  );
};

export default NoteViewerModal;

