import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from database.models import db

logger = logging.getLogger(__name__)


class SummaryNoteService:
    """Service layer for individual summary note operations.
    
    Handles pagination, file management, and operations for individual summary files
    stored in the output/summaries/ directory.
    """
    
    def __init__(self, summaries_dir: str = "output/summaries"):
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
        """Get paginated list of summary notes from database.
        
        Args:
            page: Page number (1-based)
            page_size: Number of items per page
            
        Returns:
            Dict containing summaries, pagination info, and metadata
        """
        try:
            # Get semantic entries from database instead of files
            offset = (page - 1) * page_size
            
            # Query for semantic entries with pagination
            query = """
                SELECT se.id, se.timestamp, se.summary, se.impact, se.file_path,
                       GROUP_CONCAT(st.topic) as topics,
                       GROUP_CONCAT(sk.keyword) as keywords
                FROM semantic_entries se
                LEFT JOIN semantic_topics st ON se.id = st.entry_id
                LEFT JOIN semantic_keywords sk ON se.id = sk.entry_id
                GROUP BY se.id, se.timestamp, se.summary, se.impact, se.file_path
                ORDER BY se.timestamp DESC
                LIMIT ? OFFSET ?
            """
            
            # Get total count for pagination
            count_query = "SELECT COUNT(*) as count FROM semantic_entries"
            count_result = db.execute_query(count_query)
            total_count = count_result[0]['count'] if count_result else 0
            
            # Get paginated results
            rows = db.execute_query(query, (page_size, offset))
            
            # Convert database entries to summary format expected by frontend
            summaries = []
            for row in rows:
                # Create a filename based on the semantic entry ID and source file
                file_stem = Path(row['file_path']).stem if row['file_path'] else 'summary'
                filename = f"Summary-{row['id']}-{file_stem}.md"
                
                # Parse timestamp
                timestamp = datetime.fromisoformat(row['timestamp']) if row['timestamp'] else datetime.now()
                
                # Create summary data structure
                summary_preview = row['summary'][:150] + '...' if row['summary'] and len(row['summary']) > 150 else row['summary']
                word_count = len(row['summary'].split()) if row['summary'] else 0
                
                summaries.append({
                    'filename': filename,
                    'timestamp': timestamp.isoformat(),
                    'title': f"Summary of {Path(row['file_path']).name}" if row['file_path'] else "AI Summary",
                    'preview': summary_preview,
                    'word_count': word_count,
                    'created_time': f"*Created: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}*",
                    'file_size': len(row['summary'].encode('utf-8')) if row['summary'] else 0,
                    'last_modified': timestamp.isoformat(),
                    'semantic_id': row['id'],  # Add semantic ID for reference
                    'impact': row['impact'],
                    'topics': row['topics'].split(',') if row['topics'] else [],
                    'keywords': row['keywords'].split(',') if row['keywords'] else []
                })
            
            # Calculate pagination
            total_pages = (total_count + page_size - 1) // page_size
            
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
        """Get content of a specific summary from database.
        
        Args:
            filename: Name of the summary file (format: Summary-{id}-{stem}.md)
            
        Returns:
            Dict containing summary content and metadata
        """
        try:
            # Extract semantic ID from filename (format: Summary-{id}-{stem}.md)
            import re
            match = re.match(r'Summary-(\d+)-.*\.md', filename)
            if not match:
                raise FileNotFoundError(f"Invalid summary filename format: {filename}")
            
            semantic_id = int(match.group(1))
            
            # Query database for semantic entry
            query = """
                SELECT se.id, se.timestamp, se.summary, se.impact, se.file_path,
                       GROUP_CONCAT(st.topic) as topics,
                       GROUP_CONCAT(sk.keyword) as keywords
                FROM semantic_entries se
                LEFT JOIN semantic_topics st ON se.id = st.entry_id
                LEFT JOIN semantic_keywords sk ON se.id = sk.entry_id
                WHERE se.id = ?
                GROUP BY se.id, se.timestamp, se.summary, se.impact, se.file_path
            """
            
            rows = db.execute_query(query, (semantic_id,))
            if not rows:
                raise FileNotFoundError(f"Summary not found for {filename}")
            
            row = rows[0]
            timestamp = datetime.fromisoformat(row['timestamp']) if row['timestamp'] else datetime.now()
            
            # Format as markdown content
            content = self._format_summary_as_markdown(row, timestamp)
            
            return {
                'filename': filename,
                'content': content,
                'timestamp': timestamp.isoformat(),
                'title': f"Summary of {Path(row['file_path']).name}" if row['file_path'] else "AI Summary",
                'word_count': len(row['summary'].split()) if row['summary'] else 0,
                'created_time': f"*Created: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}*",
                'file_size': len(content.encode('utf-8')),
                'last_modified': timestamp.isoformat(),
                'semantic_id': row['id'],
                'impact': row['impact'],
                'topics': row['topics'].split(',') if row['topics'] else [],
                'keywords': row['keywords'].split(',') if row['keywords'] else []
            }
            
        except Exception as e:
            logger.error(f"Failed to get summary content for {filename}: {e}")
            raise
    
    def _format_summary_as_markdown(self, row: dict, timestamp: datetime) -> str:
        """Format semantic entry as markdown content."""
        file_name = Path(row['file_path']).name if row['file_path'] else "Unknown File"
        
        content = f"""# Summary of {file_name}

*Created: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}*
*Impact: {row['impact']}*

---

## Summary

{row['summary'] or 'No summary available'}

---

## Metadata

**Topics:** {row['topics'] or 'None'}

**Keywords:** {row['keywords'] or 'None'}

**Source File:** {row['file_path'] or 'Unknown'}

**Generated:** {timestamp.strftime('%Y-%m-%d at %H:%M:%S')}
"""
        return content
    
    def delete_summary(self, filename: str) -> Dict:
        """Delete a specific summary from database.
        
        Args:
            filename: Name of the summary file to delete (format: Summary-{id}-{stem}.md)
            
        Returns:
            Dict containing success status and message
        """
        try:
            # Extract semantic ID from filename (format: Summary-{id}-{stem}.md)
            import re
            match = re.match(r'Summary-(\d+)-.*\.md', filename)
            if not match:
                raise FileNotFoundError(f"Invalid summary filename format: {filename}")
            
            semantic_id = int(match.group(1))
            
            # Check if semantic entry exists
            check_query = "SELECT id FROM semantic_entries WHERE id = ?"
            check_result = db.execute_query(check_query, (semantic_id,))
            if not check_result:
                raise FileNotFoundError(f"Summary not found: {filename}")
            
            # Delete from database (foreign keys will handle related tables)
            delete_query = "DELETE FROM semantic_entries WHERE id = ?"
            db.execute_update(delete_query, (semantic_id,))
            
            return {
                'success': True,
                'message': f'Summary {filename} deleted successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to delete summary {filename}: {e}")
            raise
    
    def delete_multiple_summaries(self, filenames: List[str]) -> Dict:
        """Delete multiple summaries from database in bulk.
        
        Args:
            filenames: List of summary file names to delete (format: Summary-{id}-{stem}.md)
            
        Returns:
            Dict containing overall success status, detailed results, and summary
        """
        if not filenames:
            return {
                'success': True,
                'message': 'No files specified for deletion',
                'results': [],
                'summary': {
                    'total': 0,
                    'succeeded': 0,
                    'failed': 0,
                    'failed_files': []
                }
            }
        
        results = []
        succeeded = 0
        failed = 0
        failed_files = []
        
        try:
            # Process each file
            for filename in filenames:
                try:
                    # Validate filename to prevent path traversal and check format
                    if not filename.endswith('.md') or '/' in filename or '\\' in filename or '..' in filename:
                        results.append({
                            'filename': filename,
                            'success': False,
                            'error': 'Invalid filename'
                        })
                        failed += 1
                        failed_files.append(filename)
                        continue
                    
                    # Extract semantic ID from filename (format: Summary-{id}-{stem}.md)
                    import re
                    match = re.match(r'Summary-(\d+)-.*\.md', filename)
                    if not match:
                        results.append({
                            'filename': filename,
                            'success': False,
                            'error': 'Invalid filename format'
                        })
                        failed += 1
                        failed_files.append(filename)
                        continue
                    
                    semantic_id = int(match.group(1))
                    
                    # Check if semantic entry exists
                    check_query = "SELECT id FROM semantic_entries WHERE id = ?"
                    check_result = db.execute_query(check_query, (semantic_id,))
                    if not check_result:
                        results.append({
                            'filename': filename,
                            'success': False,
                            'error': 'Summary not found'
                        })
                        failed += 1
                        failed_files.append(filename)
                        continue
                    
                    # Delete from database (foreign keys will handle related tables)
                    delete_query = "DELETE FROM semantic_entries WHERE id = ?"
                    db.execute_update(delete_query, (semantic_id,))
                    results.append({
                        'filename': filename,
                        'success': True,
                        'message': f'Successfully deleted {filename}'
                    })
                    succeeded += 1
                    
                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Failed to delete summary {filename}: {error_msg}")
                    results.append({
                        'filename': filename,
                        'success': False,
                        'error': error_msg
                    })
                    failed += 1
                    failed_files.append(filename)
            
            # Generate overall response
            total = len(filenames)
            overall_success = failed == 0
            
            if overall_success:
                message = f"Successfully deleted all {succeeded} files"
            elif succeeded == 0:
                message = f"Failed to delete all {failed} files"
            else:
                message = f"Partially successful: {succeeded} deleted, {failed} failed"
            
            return {
                'success': overall_success,
                'message': message,
                'results': results,
                'summary': {
                    'total': total,
                    'succeeded': succeeded,
                    'failed': failed,
                    'failed_files': failed_files
                }
            }
            
        except Exception as e:
            logger.error(f"Critical error during bulk delete: {e}")
            return {
                'success': False,
                'message': f'Critical error during bulk delete: {str(e)}',
                'results': results,
                'summary': {
                    'total': len(filenames),
                    'succeeded': succeeded,
                    'failed': len(filenames) - succeeded,
                    'failed_files': [f for f in filenames if f not in [r['filename'] for r in results if r.get('success', False)]]
                }
            }
    
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