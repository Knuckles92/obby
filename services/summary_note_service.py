import json
import logging
import os
import re
import sqlite3
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
    
    def get_summary_list(self, page: int = 1, page_size: int = 10, search_query: str = None) -> Dict:
        """Get paginated list of summary notes from database.
        
        Args:
            page: Page number (1-based)
            page_size: Number of items per page
            search_query: Optional search query to filter summaries by content
            
        Returns:
            Dict containing summaries, pagination info, and metadata
        """
        try:
            # Get semantic entries from database instead of files
            offset = (page - 1) * page_size
            
            # Build query based on whether search is provided
            if search_query:
                # Use search-enabled query
                query = """
                    SELECT se.id, se.timestamp, se.summary, se.impact, se.file_path, se.markdown_file_path,
                           GROUP_CONCAT(st.topic) as topics,
                           GROUP_CONCAT(sk.keyword) as keywords
                    FROM semantic_entries se
                    LEFT JOIN semantic_topics st ON se.id = st.entry_id
                    LEFT JOIN semantic_keywords sk ON se.id = sk.entry_id
                    WHERE se.source_type IN ('living_note', 'comprehensive')
                      AND (se.summary LIKE ? OR 
                           EXISTS (SELECT 1 FROM semantic_topics st2 WHERE st2.entry_id = se.id AND st2.topic LIKE ?) OR
                           EXISTS (SELECT 1 FROM semantic_keywords sk2 WHERE sk2.entry_id = se.id AND sk2.keyword LIKE ?))
                    GROUP BY se.id, se.timestamp, se.summary, se.impact, se.file_path, se.markdown_file_path
                    ORDER BY se.timestamp DESC
                    LIMIT ? OFFSET ?
                """
                search_pattern = f"%{search_query}%"
                query_params = (search_pattern, search_pattern, search_pattern, page_size, offset)
                
                # Count query for search results
                count_query = """
                    SELECT COUNT(DISTINCT se.id) as count 
                    FROM semantic_entries se
                    LEFT JOIN semantic_topics st ON se.id = st.entry_id
                    LEFT JOIN semantic_keywords sk ON se.id = sk.entry_id
                    WHERE se.source_type IN ('living_note', 'comprehensive')
                      AND (se.summary LIKE ? OR 
                           EXISTS (SELECT 1 FROM semantic_topics st2 WHERE st2.entry_id = se.id AND st2.topic LIKE ?) OR
                           EXISTS (SELECT 1 FROM semantic_keywords sk2 WHERE sk2.entry_id = se.id AND sk2.keyword LIKE ?))
                """
                count_params = (search_pattern, search_pattern, search_pattern)
            else:
                # Standard query without search
                query = """
                    SELECT se.id, se.timestamp, se.summary, se.impact, se.file_path, se.markdown_file_path,
                           GROUP_CONCAT(st.topic) as topics,
                           GROUP_CONCAT(sk.keyword) as keywords
                    FROM semantic_entries se
                    LEFT JOIN semantic_topics st ON se.id = st.entry_id
                    LEFT JOIN semantic_keywords sk ON se.id = sk.entry_id
                    WHERE se.source_type IN ('living_note', 'comprehensive')
                    GROUP BY se.id, se.timestamp, se.summary, se.impact, se.file_path, se.markdown_file_path
                    ORDER BY se.timestamp DESC
                    LIMIT ? OFFSET ?
                """
                query_params = (page_size, offset)
                
                # Standard count query
                count_query = "SELECT COUNT(*) as count FROM semantic_entries WHERE source_type IN ('living_note', 'comprehensive')"
                count_params = ()
            
            # Execute count query
            count_result = db.execute_query(count_query, count_params)
            total_count = count_result[0]['count'] if count_result else 0
            
            # Get paginated results
            rows = db.execute_query(query, query_params)
            
            # Convert database entries to summary format expected by frontend
            summaries = []
            for row in rows:
                # Use the actual markdown filename from database
                markdown_path = row['markdown_file_path'] or ''
                if markdown_path:
                    filename = Path(markdown_path).name
                else:
                    # Fallback filename
                    filename = f"Summary-{row['id']}-living-note.md"
                
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
            
        except sqlite3.OperationalError as e:
            # If the semantic_entries table doesn't exist yet, return an empty result
            if 'no such table: semantic_entries' in str(e):
                logger.warning("semantic_entries table not found; returning empty summaries list")
                return {
                    'summaries': [],
                    'pagination': {
                        'current_page': page,
                        'page_size': page_size,
                        'total_count': 0,
                        'total_pages': 0,
                        'has_next': False,
                        'has_previous': False
                    }
                }
            # Re-raise for other operational errors
            logger.error(f"Operational error getting summary list: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to get summary list: {e}")
            raise
    
    def get_summary_content(self, filename: str) -> Dict:
        """Get content of a specific summary from hybrid database + file system.
        
        Args:
            filename: Name of the summary file (actual markdown filename)
            
        Returns:
            Dict containing summary content and metadata
        """
        try:
            logger.debug(f"get_summary_content called with filename: {filename}")
            
            # First try to find by exact filename match in markdown_file_path
            # Use multiple patterns to handle both forward and backslash separators
            query = """
                SELECT se.id, se.timestamp, se.summary, se.impact, se.file_path, se.markdown_file_path,
                       GROUP_CONCAT(st.topic) as topics,
                       GROUP_CONCAT(sk.keyword) as keywords
                FROM semantic_entries se
                LEFT JOIN semantic_topics st ON se.id = st.entry_id
                LEFT JOIN semantic_keywords sk ON se.id = sk.entry_id
                WHERE se.source_type IN ('living_note', 'comprehensive') AND
                      (se.markdown_file_path LIKE ? OR 
                       se.markdown_file_path LIKE ? OR 
                       se.markdown_file_path = ?)
                GROUP BY se.id, se.timestamp, se.summary, se.impact, se.file_path, se.markdown_file_path
                ORDER BY se.timestamp DESC
                LIMIT 1
            """

            # Try pattern match with both forward and backslash paths (OS-agnostic)
            rows = db.execute_query(query, (f"%/{filename}", f"%\\{filename}", filename))
            
            logger.debug(f"Query returned {len(rows) if rows else 0} rows for filename: {filename}")
            
            # Fallback: try to extract semantic ID from old format (Summary-{id}-{stem}.md)
            if not rows:
                logger.debug(f"No rows found with path matching, trying ID extraction for: {filename}")
                import re
                match = re.match(r'Summary-(\d+)-.*\.md', filename)
                if match:
                    semantic_id = int(match.group(1))
                    logger.debug(f"Extracted semantic_id: {semantic_id} from filename")
                    id_query = """
                        SELECT se.id, se.timestamp, se.summary, se.impact, se.file_path, se.markdown_file_path,
                               GROUP_CONCAT(st.topic) as topics,
                               GROUP_CONCAT(sk.keyword) as keywords
                        FROM semantic_entries se
                        LEFT JOIN semantic_topics st ON se.id = st.entry_id
                        LEFT JOIN semantic_keywords sk ON se.id = sk.entry_id
                        WHERE se.id = ? AND se.source_type IN ('living_note', 'comprehensive')
                        GROUP BY se.id, se.timestamp, se.summary, se.impact, se.file_path, se.markdown_file_path
                    """
                    rows = db.execute_query(id_query, (semantic_id,))
                    logger.debug(f"ID-based query returned {len(rows) if rows else 0} rows")
            
            if not rows:
                logger.error(f"Summary not found for {filename} - no database entries matched")
                raise FileNotFoundError(f"Summary not found for {filename}")
            
            row = rows[0]
            timestamp = datetime.fromisoformat(row['timestamp']) if row['timestamp'] else datetime.now()
            
            # Read content from the actual markdown file
            markdown_file_path = row['markdown_file_path']
            logger.debug(f"Found markdown_file_path: {markdown_file_path}")

            content = None
            file_size = 0
            last_modified = timestamp

            if markdown_file_path:
                # Handle both relative and absolute paths
                file_path = Path(markdown_file_path)
                if not file_path.is_absolute():
                    file_path = Path.cwd() / file_path
                
                logger.debug(f"Resolved file path: {file_path}")
                
                if file_path.exists():
                    logger.debug(f"Reading markdown file: {file_path}")
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    logger.debug(f"Successfully read {len(content)} characters from {file_path.name}")
                    file_stats = file_path.stat()
                    file_size = file_stats.st_size
                    last_modified = datetime.fromtimestamp(file_stats.st_mtime)
                else:
                    logger.warning(f"Markdown file not found on disk for {filename}: {file_path}. Falling back to database content.")
            else:
                logger.warning(f"No markdown file path linked for {filename} (semantic_id: {row['id']}). Falling back to database content.")

            if content is None:
                if row['summary']:
                    content = self._format_summary_as_markdown(row, timestamp)
                    file_size = len(content.encode('utf-8'))
                    last_modified = timestamp
                    logger.debug(f"Generated markdown content from database for {filename}")
                else:
                    logger.error(f"No markdown content available for {filename} (semantic_id: {row['id']})")
                    raise FileNotFoundError(f"Summary content not available for {filename}")
            
            return {
                'filename': filename,
                'content': content,
                'timestamp': timestamp.isoformat(),
                'title': f"Living Note Summary - {timestamp.strftime('%Y-%m-%d')}",
                'word_count': len(content.split()) if content else 0,
                'created_time': f"*Created: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}*",
                'file_size': file_size,
                'last_modified': last_modified.isoformat(),
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
        """Delete a specific summary from database and file system.
        
        Args:
            filename: Name of the summary file to delete
        
        Returns:
            Dict containing success status and message
        """
        try:
            # Find the database entry by filename (exact or suffix match)
            query = """
                SELECT se.id, se.markdown_file_path
                FROM semantic_entries se
                WHERE se.source_type IN ('living_note', 'comprehensive') AND
                      (se.markdown_file_path LIKE ? OR se.markdown_file_path = ?)
                ORDER BY se.timestamp DESC
                LIMIT 1
            """
            rows = db.execute_query(query, (f"%{filename}", filename))

            # Fallback: try to extract semantic ID from old format Summary-{id}-....md
            if not rows:
                match = re.match(r'Summary-(\d+)-.*\.md', filename)
                if match:
                    semantic_id = int(match.group(1))
                    id_query = (
                        "SELECT id, markdown_file_path FROM semantic_entries "
                        "WHERE id = ? AND source_type IN ('living_note', 'comprehensive')"
                    )
                    rows = db.execute_query(id_query, (semantic_id,))

            if not rows:
                raise FileNotFoundError(f"Summary not found: {filename}")

            row = rows[0]
            semantic_id = row['id']
            markdown_file_path = row['markdown_file_path']

            # Delete from database (auto-commit handled by execute_update)
            delete_query = "DELETE FROM semantic_entries WHERE id = ?"
            db.execute_update(delete_query, (semantic_id,))

            # Best-effort delete the markdown file if it exists
            if markdown_file_path:
                file_path = Path(markdown_file_path)
                if not file_path.is_absolute():
                    file_path = Path.cwd() / file_path
                if file_path.exists():
                    try:
                        os.remove(file_path)
                        logger.info(f"Deleted markdown file: {file_path}")
                    except Exception as file_err:
                        logger.warning(f"Failed to delete markdown file {file_path}: {file_err}")
                else:
                    logger.warning(f"Markdown file not found for deletion: {file_path}")

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
                    
                    # Use the single delete method for consistency and proper file cleanup
                    delete_result = self.delete_summary(filename)
                    if delete_result.get('success', False):
                        results.append({
                            'filename': filename,
                            'success': True,
                            'message': f'Successfully deleted {filename}'
                        })
                        succeeded += 1
                    else:
                        results.append({
                            'filename': filename,
                            'success': False,
                            'error': delete_result.get('message', 'Unknown error')
                        })
                        failed += 1
                        failed_files.append(filename)
                    
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
