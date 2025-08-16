import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class SummaryNoteService:
    """Service layer for individual summary note operations.
    
    Handles pagination, file management, and operations for individual summary files
    stored in the notes/summaries/ directory.
    """
    
    def __init__(self, summaries_dir: str = "notes/summaries"):
        self.summaries_dir = Path(summaries_dir)
        self.summaries_dir.mkdir(parents=True, exist_ok=True)
        
    def _parse_filename_timestamp(self, filename: str) -> Optional[datetime]:
        """Parse timestamp from summary filename.
        
        Expected format: Summary-YYYY-MM-DD-HHMMSS.md
        """
        try:
            # Remove .md extension and extract timestamp part
            base_name = filename.replace('.md', '')
            # Pattern: Summary-YYYY-MM-DD-HHMMSS
            match = re.search(r'Summary-(\d{4}-\d{2}-\d{2}-\d{6})', base_name)
            if match:
                timestamp_str = match.group(1)
                # Parse YYYY-MM-DD-HHMMSS format
                return datetime.strptime(timestamp_str, '%Y-%m-%d-%H%M%S')
            return None
        except Exception as e:
            logger.warning(f"Failed to parse timestamp from filename '{filename}': {e}")
            return None
    
    def _extract_metadata_from_content(self, content: str) -> Dict:
        """Extract metadata from summary file content."""
        metadata = {
            'word_count': len(content.split()) if content else 0,
            'preview': '',
            'title': '',
            'created_time': ''
        }
        
        lines = content.split('\n')
        
        # Extract title (first line starting with #)
        for line in lines:
            if line.strip().startswith('# '):
                metadata['title'] = line.strip()[2:]
                break
        
        # Extract created time (look for *Created: pattern)
        for line in lines:
            if line.strip().startswith('*Created:'):
                metadata['created_time'] = line.strip()
                break
        
        # Create preview (first few lines of actual content, excluding metadata)
        content_lines = []
        in_content = False
        for line in lines:
            if line.strip() == '---' and not in_content:
                in_content = True
                continue
            elif line.strip() == '---' and in_content:
                break
            elif in_content and line.strip():
                content_lines.append(line.strip())
                if len(content_lines) >= 3:  # Limit preview to 3 lines
                    break
        
        if content_lines:
            metadata['preview'] = ' '.join(content_lines)[:150] + '...'
        
        return metadata
    
    def get_summary_list(self, page: int = 1, page_size: int = 10) -> Dict:
        """Get paginated list of summary notes with metadata.
        
        Args:
            page: Page number (1-based)
            page_size: Number of items per page
            
        Returns:
            Dict containing summaries, pagination info, and metadata
        """
        try:
            # Get all .md files in summaries directory
            summary_files = list(self.summaries_dir.glob('*.md'))
            
            # Parse and sort by timestamp (newest first)
            file_data = []
            for file_path in summary_files:
                timestamp = self._parse_filename_timestamp(file_path.name)
                if timestamp:
                    file_data.append({
                        'filename': file_path.name,
                        'path': file_path,
                        'timestamp': timestamp,
                        'file_stat': file_path.stat()
                    })
            
            # Sort by timestamp descending (newest first)
            file_data.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # Calculate pagination
            total_count = len(file_data)
            total_pages = (total_count + page_size - 1) // page_size
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            
            # Get page data
            page_files = file_data[start_idx:end_idx]
            
            # Load content and extract metadata for each file
            summaries = []
            for file_info in page_files:
                try:
                    content = file_info['path'].read_text(encoding='utf-8')
                    metadata = self._extract_metadata_from_content(content)
                    
                    summaries.append({
                        'filename': file_info['filename'],
                        'timestamp': file_info['timestamp'].isoformat(),
                        'title': metadata['title'],
                        'preview': metadata['preview'],
                        'word_count': metadata['word_count'],
                        'created_time': metadata['created_time'],
                        'file_size': file_info['file_stat'].st_size,
                        'last_modified': datetime.fromtimestamp(file_info['file_stat'].st_mtime).isoformat()
                    })
                except Exception as e:
                    logger.error(f"Failed to read summary file {file_info['filename']}: {e}")
                    continue
            
            return {
                'summaries': summaries,
                'pagination': {
                    'current_page': page,
                    'page_size': page_size,
                    'total_count': total_count,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_previous': page > 1
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get summary list: {e}")
            raise
    
    def get_summary_content(self, filename: str) -> Dict:
        """Get content of a specific summary file.
        
        Args:
            filename: Name of the summary file
            
        Returns:
            Dict containing file content and metadata
        """
        try:
            file_path = self.summaries_dir / filename
            
            if not file_path.exists():
                raise FileNotFoundError(f"Summary file not found: {filename}")
            
            content = file_path.read_text(encoding='utf-8')
            metadata = self._extract_metadata_from_content(content)
            timestamp = self._parse_filename_timestamp(filename)
            file_stat = file_path.stat()
            
            return {
                'filename': filename,
                'content': content,
                'timestamp': timestamp.isoformat() if timestamp else None,
                'title': metadata['title'],
                'word_count': metadata['word_count'],
                'created_time': metadata['created_time'],
                'file_size': file_stat.st_size,
                'last_modified': datetime.fromtimestamp(file_stat.st_mtime).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get summary content for {filename}: {e}")
            raise
    
    def delete_summary(self, filename: str) -> Dict:
        """Delete a specific summary file.
        
        Args:
            filename: Name of the summary file to delete
            
        Returns:
            Dict containing success status and message
        """
        try:
            file_path = self.summaries_dir / filename
            
            if not file_path.exists():
                raise FileNotFoundError(f"Summary file not found: {filename}")
            
            file_path.unlink()
            
            return {
                'success': True,
                'message': f'Summary file {filename} deleted successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to delete summary {filename}: {e}")
            raise
    
    def create_summary_filename(self, timestamp: datetime = None) -> str:
        """Generate a filename for a new summary.
        
        Args:
            timestamp: Optional timestamp, defaults to current time
            
        Returns:
            Generated filename in format: Summary-YYYY-MM-DD-HHMMSS.md
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        timestamp_str = timestamp.strftime('%Y-%m-%d-%H%M%S')
        return f"Summary-{timestamp_str}.md"
    
    def create_summary(self, content: str, timestamp: datetime = None) -> Dict:
        """Create a new summary file with the given content.
        
        Args:
            content: Markdown content for the summary
            timestamp: Optional timestamp, defaults to current time
            
        Returns:
            Dict containing filename and success status
        """
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            filename = self.create_summary_filename(timestamp)
            file_path = self.summaries_dir / filename
            
            # Ensure directory exists
            self.summaries_dir.mkdir(parents=True, exist_ok=True)
            
            # Write content to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                'success': True,
                'filename': filename,
                'message': f'Summary created successfully: {filename}'
            }
            
        except Exception as e:
            logger.error(f"Failed to create summary: {e}")
            raise
    
    def get_stats(self) -> Dict:
        """Get statistics about summary files.
        
        Returns:
            Dict containing various statistics
        """
        try:
            summary_files = list(self.summaries_dir.glob('*.md'))
            total_count = len(summary_files)
            
            if total_count == 0:
                return {
                    'total_count': 0,
                    'oldest_date': None,
                    'newest_date': None,
                    'total_size_bytes': 0
                }
            
            # Calculate statistics
            timestamps = []
            total_size = 0
            
            for file_path in summary_files:
                timestamp = self._parse_filename_timestamp(file_path.name)
                if timestamp:
                    timestamps.append(timestamp)
                total_size += file_path.stat().st_size
            
            timestamps.sort()
            
            return {
                'total_count': total_count,
                'oldest_date': timestamps[0].isoformat() if timestamps else None,
                'newest_date': timestamps[-1].isoformat() if timestamps else None,
                'total_size_bytes': total_size
            }
            
        except Exception as e:
            logger.error(f"Failed to get summary stats: {e}")
            raise