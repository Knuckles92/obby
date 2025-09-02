"""
Pure File Content Tracking System
=================================

File content monitoring and version tracking without git dependencies.
Uses file system monitoring, content hashing, and native diff generation.
"""

import hashlib
import os
import difflib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging

from database.models import (
    FileVersionModel, ContentDiffModel, FileChangeModel, 
    FileStateModel, EventModel, SemanticModel
)

logger = logging.getLogger(__name__)

class FileContentTracker:
    """Tracks file content changes without git dependency."""
    
    def __init__(self, watch_paths: List[str] = None):
        self.watch_paths = watch_paths or []
        self.file_cache: Dict[str, Dict[str, Any]] = {}
        
    def track_file_change(self, file_path: str, change_type: str = 'modified') -> Optional[int]:
        """Process a file change and create version/diff records."""
        try:
            file_path = str(Path(file_path).resolve())
            
            # Get current file content and state
            current_content = self._read_file_safely(file_path) if os.path.exists(file_path) else None
            current_hash = self._calculate_content_hash(current_content) if current_content else None
            
            # Get previous state from database
            previous_state = FileStateModel.get_state(file_path)
            
            # Check if file actually changed using content hash comparison
            if previous_state and previous_state.get('content_hash') == current_hash:
                logger.debug(f"[FILE_TRACKER] No content change detected for {file_path}: hash {current_hash[:8] if current_hash else 'None'} unchanged")
                return None
            
            # Handle different change types
            if change_type == 'created':
                return self._handle_file_creation(file_path, current_content, current_hash)
            elif change_type == 'modified':
                return self._handle_file_modification(file_path, current_content, current_hash, previous_state)
            elif change_type == 'deleted':
                return self._handle_file_deletion(file_path, previous_state)
            elif change_type == 'moved':
                return self._handle_file_move(file_path, current_content, current_hash)
                
            logger.warning(f"Unknown change type: {change_type}")
            return None
            
        except Exception as e:
            logger.error(f"Error tracking file change for {file_path}: {e}")
            return None
    
    def _handle_file_creation(self, file_path: str, content: str, content_hash: str) -> Optional[int]:
        """Handle file creation."""
        if not content:
            return None
            
        # Create file version
        line_count = len(content.splitlines())
        version_id = FileVersionModel.insert(
            file_path=file_path,
            content_hash=content_hash,
            content=content,
            line_count=line_count,
            change_description="File created"
        )
        
        # Update file state
        FileStateModel.update_state(
            file_path=file_path,
            content_hash=content_hash,
            line_count=line_count,
            file_size=len(content.encode('utf-8'))
        )
        
        # Create content diff for file creation (diff against empty content)
        self._create_content_diff(
            file_path=file_path,
            old_version_id=None,
            new_version_id=version_id,
            old_content="",
            new_content=content,
            change_type='created'
        )
        
        # Record file change
        FileChangeModel.insert(
            file_path=file_path,
            change_type='created',
            new_content_hash=content_hash
        )
        
        logger.info(f"[FILE_TRACKER] Tracked file creation: {file_path}")
        return version_id
    
    def _handle_file_modification(self, file_path: str, current_content: str, 
                                 current_hash: str, previous_state: Dict[str, Any]) -> Optional[int]:
        """Handle file modification."""
        if not current_content:
            return None
        
        # Check if content has actually changed by comparing hashes
        previous_hash = previous_state.get('content_hash') if previous_state else None
        if previous_hash == current_hash:
            logger.debug(f"[FILE_TRACKER] Skipping modification processing for {file_path}: content hash unchanged")
            return None
            
        # Get previous version for diff
        previous_version = None
        
        if previous_hash:
            previous_version = FileVersionModel.get_by_hash(previous_hash, file_path)
        
        # Create new file version
        line_count = len(current_content.splitlines())
        version_id = FileVersionModel.insert(
            file_path=file_path,
            content_hash=current_hash,
            content=current_content,
            line_count=line_count,
            change_description="File modified"
        )
        
        # Generate diff
        if previous_version and previous_version.get('content'):
            # Normal modification diff
            self._create_content_diff(
                file_path=file_path,
                old_version_id=previous_version['id'],
                new_version_id=version_id,
                old_content=previous_version['content'],
                new_content=current_content,
                change_type='modified'
            )
        else:
            # First time seeing this file: create a 'created' diff against empty content
            self._create_content_diff(
                file_path=file_path,
                old_version_id=None,
                new_version_id=version_id,
                old_content="",
                new_content=current_content,
                change_type='created'
            )
        
        # Update file state
        FileStateModel.update_state(
            file_path=file_path,
            content_hash=current_hash,
            line_count=line_count,
            file_size=len(current_content.encode('utf-8'))
        )
        
        # Record file change
        FileChangeModel.insert(
            file_path=file_path,
            change_type='modified',
            old_content_hash=previous_hash,
            new_content_hash=current_hash
        )
        
        logger.info(f"[FILE_TRACKER] Tracked file modification: {file_path}")
        return version_id
    
    def _handle_file_deletion(self, file_path: str, previous_state: Dict[str, Any]) -> Optional[int]:
        """Handle file deletion."""
        if not previous_state:
            return None
            
        # Record file change
        change_id = FileChangeModel.insert(
            file_path=file_path,
            change_type='deleted',
            old_content_hash=previous_state.get('content_hash')
        )
        
        # Note: We keep the file state and versions for history
        logger.info(f"[FILE_TRACKER] Tracked file deletion: {file_path}")
        return change_id
    
    def _handle_file_move(self, file_path: str, current_content: str, current_hash: str) -> Optional[int]:
        """Handle file move/rename."""
        # For now, treat as creation at new location
        # In the future, could implement move detection by content hash
        return self._handle_file_creation(file_path, current_content, current_hash)
    
    def _create_content_diff(self, file_path: str, old_version_id: Optional[int], new_version_id: int,
                           old_content: str, new_content: str, change_type: str = 'modified') -> Optional[int]:
        """Create a content diff between two file versions.

        change_type may be one of: 'created', 'modified', 'deleted', 'moved'
        """
        # Check if we should create this diff to avoid +0/-0 entries
        if not ContentDiffModel.should_create_diff(old_version_id, new_version_id, old_content, new_content):
            logger.debug(f"[FILE_TRACKER] Skipping diff creation for {file_path}: no actual changes detected")
            return None
        
        # Generate diff using difflib
        diff_content, lines_added, lines_removed = ContentDiffModel.generate_diff(
            old_content, new_content
        )
        
        # Store the diff
        diff_id = ContentDiffModel.insert(
            file_path=file_path,
            old_version_id=old_version_id,
            new_version_id=new_version_id,
            change_type=change_type,
            diff_content=diff_content,
            lines_added=lines_added,
            lines_removed=lines_removed
        )
        
        # Enhanced logging for debugging
        if lines_added == 0 and lines_removed == 0:
            logger.warning(f"[FILE_TRACKER] Created +0/-0 content diff {diff_id} for {file_path}: {change_type} "
                         f"(versions: {old_version_id} -> {new_version_id})")
        else:
            logger.debug(f"[FILE_TRACKER] Created content diff {diff_id}: +{lines_added}/-{lines_removed} lines")
        return diff_id
    
    def get_file_history(self, file_path: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get complete change history for a file."""
        file_path = str(Path(file_path).resolve())
        
        # Get version history
        versions = FileVersionModel.get_file_history(file_path, limit)
        
        # Get change history
        changes = FileChangeModel.get_for_file(file_path, limit)
        
        # Get diff history
        diffs = ContentDiffModel.get_for_file(file_path, limit)
        
        return {
            'versions': versions,
            'changes': changes,
            'diffs': diffs
        }
    
    def get_file_diff(self, file_path: str, old_version_id: int = None, 
                     new_version_id: int = None) -> Optional[str]:
        """Get diff content between two versions of a file."""
        file_path = str(Path(file_path).resolve())
        
        if old_version_id and new_version_id:
            # Get specific diff
            diffs = ContentDiffModel.get_for_file(file_path, 1000)  # Large limit to find it
            for diff in diffs:
                if diff['old_version_id'] == old_version_id and diff['new_version_id'] == new_version_id:
                    return diff['diff_content']
        
        return None
    
    def get_current_file_state(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get current state of a file."""
        file_path = str(Path(file_path).resolve())
        return FileStateModel.get_state(file_path)
    
    def scan_directory(self, directory_path: str, recursive: bool = True) -> int:
        """Scan a directory and track all files."""
        directory_path = Path(directory_path)
        files_processed = 0
        
        if not directory_path.exists():
            logger.warning(f"Directory does not exist: {directory_path}")
            return 0
        
        pattern = "**/*" if recursive else "*"
        
        for file_path in directory_path.glob(pattern):
            if file_path.is_file():
                try:
                    # Skip internal semantic index artifact to avoid polluting tracked diffs
                    try:
                        if file_path.name.lower() == 'semantic_index.json':
                            continue
                    except Exception:
                        pass
                    # Check if file has changed since last scan
                    current_content = self._read_file_safely(str(file_path))
                    if current_content is not None:
                        current_hash = self._calculate_content_hash(current_content)
                        
                        if FileStateModel.has_changed(str(file_path), current_hash):
                            logger.debug(f"[FILE_TRACKER] Periodic scan found change in {file_path}")
                            self.track_file_change(str(file_path), 'modified')
                            files_processed += 1
                            
                except Exception as e:
                    logger.error(f"Error scanning file {file_path}: {e}")
        
        if files_processed > 0:
            logger.info(f"[FILE_TRACKER] Scanned directory {directory_path}: {files_processed} files processed")
        else:
            logger.debug(f"[FILE_TRACKER] Scanned directory {directory_path}: no changes detected")
        return files_processed
    
    def _read_file_safely(self, file_path: str) -> Optional[str]:
        """Safely read file content with encoding detection."""
        try:
            # Try UTF-8 first
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            try:
                # Try with error handling
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Could not read file {file_path}: {e}")
                return None
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None
    
    def _calculate_content_hash(self, content: str) -> str:
        """Calculate SHA-256 hash of file content with normalization."""
        if content is None:
            return ""
        # Normalize line endings and whitespace for consistent hashing
        normalized_content = content.replace('\r\n', '\n').replace('\r', '\n')
        return hashlib.sha256(normalized_content.encode('utf-8')).hexdigest()
    
    def cleanup_old_versions(self, max_versions_per_file: int = 100) -> int:
        """Clean up old file versions to prevent database bloat."""
        # This would implement cleanup logic
        # For now, just return 0
        logger.info("Version cleanup not yet implemented")
        return 0

# Global file tracker instance
file_tracker = FileContentTracker()

logger.info("File content tracking system initialized")
