"""
Helper module for comprehensive summary generation with async worker pattern
"""
import logging
import hashlib
import time
import threading
from datetime import datetime, timedelta
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# Global state for comprehensive summary generation
_comp_lock = threading.Lock()
_last_comp_result = {
    'running': False,
    'last': None,
}


def _fingerprint_combined(files_count: int, total_changes: int, combined_diff: str) -> str:
    """Create fingerprint hash of comprehensive summary inputs"""
    try:
        h = hashlib.sha256()
        h.update(str(files_count).encode('utf-8'))
        h.update(str(total_changes).encode('utf-8'))
        h.update((combined_diff or '').encode('utf-8'))
        return h.hexdigest()
    except Exception:
        return ''


def _prepare_combined_diff(changes_by_file: dict, max_len: int = 4000) -> str:
    """Prepare a combined diff string with length cap"""
    diff_parts = []
    
    for file_path, file_changes in changes_by_file.items():
        diff_parts.append(f"\n=== Changes in {file_path} ===")
        
        for change in file_changes:
            if change.get('diff_content'):
                timestamp = change.get('timestamp', 'unknown')
                diff_parts.append(f"--- Change at {timestamp} ---")
                diff_parts.append(change['diff_content'])
        
        diff_parts.append("")  # Add spacing between files
    
    combined = "\n".join(diff_parts)
    
    # Truncate if too long to avoid API limits
    if len(combined) > max_len:
        return combined[:max_len] + "\n... (truncated for API limits)"
    
    return combined


def _calculate_time_span(start_time: datetime, end_time: datetime) -> str:
    """Calculate human-readable time span between two timestamps."""
    span = end_time - start_time
    
    if span.days > 0:
        return f"{span.days} day{'s' if span.days != 1 else ''}"
    elif span.seconds >= 3600:
        hours = span.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''}"
    elif span.seconds >= 60:
        minutes = span.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    else:
        return f"{span.seconds} second{'s' if span.seconds != 1 else ''}"


def _prepare_file_summaries(changes_by_file: dict) -> list:
    """Prepare individual file summary data."""
    file_summaries = []
    
    for file_path, file_changes in changes_by_file.items():
        changes_count = len(file_changes)
        lines_added = sum(c.get('lines_added', 0) for c in file_changes)
        lines_removed = sum(c.get('lines_removed', 0) for c in file_changes)
        
        summary = f"{changes_count} change{'s' if changes_count != 1 else ''}"
        if lines_added > 0 or lines_removed > 0:
            summary += f" (+{lines_added}/-{lines_removed} lines)"
        
        file_summaries.append({
            'file_path': file_path,
            'summary': summary,
            'changes_count': changes_count,
            'lines_added': lines_added,
            'lines_removed': lines_removed
        })
    
    return file_summaries


def _parse_ai_summary(ai_summary: str) -> dict:
    """Parse structured AI summary response into components."""
    import re
    
    parsed = {
        'summary': ai_summary,
        'topics': [],
        'keywords': [],
        'impact': 'moderate'
    }
    
    # Try to extract structured sections
    lines = ai_summary.split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Extract topics
        if line.startswith('**Key Topics**:'):
            topics_text = line.replace('**Key Topics**:', '').strip()
            parsed['topics'] = [t.strip() for t in topics_text.split(',') if t.strip()]
        
        # Extract keywords  
        elif line.startswith('**Key Keywords**:'):
            keywords_text = line.replace('**Key Keywords**:', '').strip()
            parsed['keywords'] = [k.strip() for k in keywords_text.split(',') if k.strip()]
        
        # Extract impact
        elif line.startswith('**Overall Impact**:'):
            impact_text = line.replace('**Overall Impact**:', '').strip().lower()
            if impact_text in ['brief', 'moderate', 'significant']:
                parsed['impact'] = impact_text
        
        # Extract main summary
        elif line.startswith('**Batch Summary**:'):
            parsed['summary'] = line.replace('**Batch Summary**:', '').strip()
    
    return parsed


def run_comprehensive_worker(force: bool, result_box: dict):
    """Background worker for comprehensive summary generation"""
    with _comp_lock:
        _last_comp_result['running'] = True
        try:
            from database.models import ComprehensiveSummaryModel, ConfigModel, db
            from ai.openai_client import OpenAIClient
            
            logger.info(f"Comprehensive worker starting (force={force})")
            start_time = time.time()
            
            # Get last comprehensive summary timestamp
            last_summary_timestamp = ComprehensiveSummaryModel.get_last_summary_timestamp()
            
            if not last_summary_timestamp:
                last_summary_timestamp = datetime.now() - timedelta(days=7)
                logger.info("No previous comprehensive summary found, using 7 days ago as start time")
            
            # Get ALL changes since last comprehensive summary
            changes_query = """
                SELECT cd.*, fv_new.content, fv_new.file_path, fv_new.content_hash
                FROM content_diffs cd
                LEFT JOIN file_versions fv_new ON cd.new_version_id = fv_new.id
                WHERE cd.timestamp > ?
                ORDER BY cd.timestamp ASC
            """
            
            changes = db.execute_query(changes_query, (last_summary_timestamp,))
            
            if not changes and not force:
                result = {
                    'success': True,
                    'message': 'No changes found since last comprehensive summary',
                    'result': {
                        'processed': False,
                        'changes_count': 0,
                        'time_range_start': last_summary_timestamp.isoformat(),
                        'time_range_end': datetime.now().isoformat(),
                        'reason': 'No changes to summarize'
                    }
                }
                result_box['result'] = result
                _last_comp_result['last'] = result
                return
            
            # Group changes by file
            changes_by_file = {}
            for change in changes:
                change_dict = dict(change)
                file_path = change_dict['file_path']
                try:
                    if str(file_path).lower().endswith('semantic_index.json'):
                        continue
                except Exception:
                    pass
                if file_path not in changes_by_file:
                    changes_by_file[file_path] = []
                changes_by_file[file_path].append(change_dict)
            
            logger.info(f"Comprehensive worker: processing {len(changes)} changes across {len(changes_by_file)} files")
            
            # Get AI client
            ai_client = OpenAIClient.get_instance()
            ai_client.warm_up()
            
            # Prepare batch data (with reduced diff size)
            batch_data = {
                'files_count': len(changes_by_file),
                'total_changes': len(changes),
                'time_span': _calculate_time_span(last_summary_timestamp, datetime.now()),
                'combined_diff': _prepare_combined_diff(changes_by_file, max_len=4000),
                'file_summaries': _prepare_file_summaries(changes_by_file)
            }
            
            # Fingerprint check to skip redundant runs
            fp = _fingerprint_combined(batch_data['files_count'], batch_data['total_changes'], batch_data['combined_diff'])
            try:
                last_fp = ConfigModel.get('last_comprehensive_fingerprint', '')
                if fp and last_fp == fp and not force:
                    result = {
                        'success': True,
                        'message': 'No new effective changes (fingerprint match)',
                        'result': {
                            'processed': False,
                            'changes_count': len(changes),
                            'files_count': len(changes_by_file),
                            'time_range_start': last_summary_timestamp.isoformat(),
                            'time_range_end': datetime.now().isoformat(),
                            'processing_time': time.time() - start_time,
                            'time_span': batch_data['time_span'],
                            'reason': 'fingerprint_unchanged'
                        }
                    }
                    result_box['result'] = result
                    _last_comp_result['last'] = result
                    logger.info("Comprehensive worker: fingerprint match, skipping AI call")
                    return
            except Exception as e:
                logger.debug(f"Fingerprint check failed: {e}")
            
            # Generate summary with brief setting for speed
            logger.info("Comprehensive worker: calling AI with brief mode")
            ai_summary = ai_client.summarize_batch_changes(batch_data, settings={'summaryLength': 'brief'})
            
            if not ai_summary or "Error" in ai_summary:
                result = {
                    'success': False,
                    'message': 'Failed to generate comprehensive summary',
                    'result': {
                        'processed': False,
                        'changes_count': len(changes),
                        'error': ai_summary or 'Unknown AI error'
                    }
                }
                result_box['result'] = result
                _last_comp_result['last'] = result
                return
            
            # Parse and save
            summary_data = _parse_ai_summary(ai_summary)
            current_time = datetime.now()
            
            summary_id = ComprehensiveSummaryModel.create_summary(
                time_range_start=last_summary_timestamp,
                time_range_end=current_time,
                summary_content=summary_data.get('summary', ai_summary),
                key_topics=summary_data.get('topics', []),
                key_keywords=summary_data.get('keywords', []),
                overall_impact=summary_data.get('impact', 'moderate'),
                files_affected_count=len(changes_by_file),
                changes_count=len(changes),
                time_span=batch_data['time_span']
            )
            
            processing_time = time.time() - start_time
            
            if summary_id:
                # Save fingerprint
                try:
                    if fp:
                        ConfigModel.set('last_comprehensive_fingerprint', fp, 'Fingerprint of last comprehensive input')
                except Exception:
                    pass
                
                result = {
                    'success': True,
                    'message': f'Comprehensive summary generated successfully for {len(changes)} changes across {len(changes_by_file)} files',
                    'result': {
                        'processed': True,
                        'summary_id': summary_id,
                        'changes_count': len(changes),
                        'files_count': len(changes_by_file),
                        'time_range_start': last_summary_timestamp.isoformat(),
                        'time_range_end': current_time.isoformat(),
                        'processing_time': processing_time,
                        'time_span': batch_data['time_span'],
                        'summary_preview': summary_data.get('summary', ai_summary)[:200] + '...'
                    }
                }
                result_box['result'] = result
                _last_comp_result['last'] = result
                logger.info(f"Comprehensive worker: completed in {processing_time:.2f}s, summary_id={summary_id}")
            else:
                result = {
                    'success': False,
                    'message': 'Failed to save comprehensive summary',
                    'result': {
                        'processed': False,
                        'changes_count': len(changes),
                        'error': 'Database save failed'
                    }
                }
                result_box['result'] = result
                _last_comp_result['last'] = result
                
        except Exception as e:
            logger.error(f"Comprehensive worker failed: {e}", exc_info=True)
            result = {
                'success': False,
                'message': f'Comprehensive summary generation failed: {str(e)}',
                'result': {
                    'processed': False,
                    'changes_count': 0,
                    'processing_time': 0,
                    'error': str(e)
                }
            }
            result_box['result'] = result
            _last_comp_result['last'] = result
        finally:
            _last_comp_result['running'] = False


def get_comprehensive_status():
    """Get current comprehensive summary generation status"""
    return {
        'running': _last_comp_result.get('running', False),
        'last': _last_comp_result.get('last')
    }

