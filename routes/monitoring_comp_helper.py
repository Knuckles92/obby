"""
Helper module for comprehensive summary generation with async worker pattern

Refactored to use Claude Agent SDK via ComprehensiveSummaryService.
"""
import logging
import time
import threading
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Global state for comprehensive summary generation
_comp_lock = threading.Lock()
_last_comp_result = {
    'running': False,
    'last': None,
}


def run_comprehensive_worker(force: bool, result_box: dict):
    """Background worker for comprehensive summary generation"""
    with _comp_lock:
        _last_comp_result['running'] = True
        try:
            from database.models import ComprehensiveSummaryModel, ConfigModel, db
            from services.comprehensive_summary_service import get_comprehensive_summary_service
            import asyncio

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

            # Get service instance
            service = get_comprehensive_summary_service()

            # Check if Claude Agent is available
            if not service.is_available():
                result = {
                    'success': False,
                    'message': 'Claude Agent SDK not available. Check ANTHROPIC_API_KEY environment variable.',
                    'result': {
                        'processed': False,
                        'changes_count': len(changes),
                        'error': 'Claude Agent SDK not configured'
                    }
                }
                result_box['result'] = result
                _last_comp_result['last'] = result
                logger.error("Comprehensive worker: Claude Agent SDK not available")
                return

            # Prepare combined diff
            combined_diff = service.prepare_combined_diff(changes_by_file, max_len=4000)
            time_span = service.calculate_time_span(last_summary_timestamp, datetime.now())

            # Fingerprint check to skip redundant runs
            fp = service.fingerprint_combined(len(changes_by_file), len(changes), combined_diff)
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
                            'time_span': time_span,
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
            logger.info("Comprehensive worker: calling Claude Agent with brief mode")

            # Run async method in sync context
            current_time = datetime.now()
            success, summary_data, error_msg = asyncio.run(
                service.generate_comprehensive_summary(
                    changes_by_file=changes_by_file,
                    time_range_start=last_summary_timestamp,
                    time_range_end=current_time,
                    settings={'summaryLength': 'brief'}
                )
            )

            if not success or not summary_data:
                result = {
                    'success': False,
                    'message': f'Failed to generate comprehensive summary: {error_msg}',
                    'result': {
                        'processed': False,
                        'changes_count': len(changes),
                        'error': error_msg or 'Unknown error from Claude Agent'
                    }
                }
                result_box['result'] = result
                _last_comp_result['last'] = result
                logger.error(f"Comprehensive worker: AI generation failed - {error_msg}")
                return
            
            # Save to database
            summary_id = ComprehensiveSummaryModel.create_summary(
                time_range_start=last_summary_timestamp,
                time_range_end=current_time,
                summary_content=summary_data.get('summary', 'No summary generated'),
                key_topics=summary_data.get('topics', []),
                key_keywords=summary_data.get('keywords', []),
                overall_impact=summary_data.get('impact', 'moderate'),
                files_affected_count=len(changes_by_file),
                changes_count=len(changes),
                time_span=time_span
            )

            # Also create a semantic entry + markdown file for display in Summary Notes page
            if summary_id:
                try:
                    from database.models import SemanticModel
                    from pathlib import Path
                    import os

                    # Create markdown file for comprehensive summary
                    output_dir = Path("output/summaries")
                    output_dir.mkdir(parents=True, exist_ok=True)

                    timestamp_str = current_time.strftime('%Y-%m-%d-%H%M%S')
                    markdown_filename = f"Comprehensive-Summary-{timestamp_str}.md"
                    markdown_path = output_dir / markdown_filename

                    # Format comprehensive summary as markdown
                    topics_str = ", ".join(summary_data.get('topics', []))
                    keywords_str = ", ".join(summary_data.get('keywords', []))

                    markdown_content = f"""# Comprehensive Summary - {current_time.strftime('%Y-%m-%d %H:%M')}

*Generated: {current_time.strftime('%Y-%m-%d at %H:%M:%S')}*
*Time Range: {last_summary_timestamp.strftime('%Y-%m-%d %H:%M')} to {current_time.strftime('%Y-%m-%d %H:%M')} ({time_span})*
*Files Affected: {len(changes_by_file)} files*
*Changes Processed: {len(changes)} changes*
*Overall Impact: {summary_data.get('impact', 'moderate')}*

---

## Summary

{summary_data.get('summary', 'No summary available')}

---

## Metadata

**Topics:** {topics_str or 'None'}

**Keywords:** {keywords_str or 'None'}

**Files Changed:**
"""

                    # Add list of changed files
                    file_summaries = service.prepare_file_summaries(changes_by_file)
                    for fs in file_summaries[:20]:  # Limit to first 20
                        markdown_content += f"\n- `{fs['file_path']}` - {fs['summary']}"

                    if len(file_summaries) > 20:
                        markdown_content += f"\n- ... and {len(file_summaries) - 20} more files"

                    markdown_content += f"\n\n---\n\n*Summary ID: {summary_id}*"

                    # Write markdown file
                    with open(markdown_path, 'w', encoding='utf-8') as f:
                        f.write(markdown_content)

                    logger.info(f"Created markdown file: {markdown_path}")

                    # Create semantic entry for display in Summary Notes
                    semantic_id = SemanticModel.insert_entry(
                        summary=summary_data.get('summary', 'No summary'),
                        entry_type='comprehensive',  # Different type to distinguish from living notes
                        impact=summary_data.get('impact', 'moderate'),
                        topics=summary_data.get('topics', []),
                        keywords=summary_data.get('keywords', []),
                        file_path=f"comprehensive/{len(changes_by_file)} files",  # Virtual path
                        version_id=None,
                        timestamp=current_time
                    )

                    # Update semantic entry with markdown path and source type
                    db.execute_update(
                        "UPDATE semantic_entries SET markdown_file_path = ?, source_type = ? WHERE id = ?",
                        (str(markdown_path), 'comprehensive', semantic_id)
                    )

                    logger.info(f"Created semantic entry {semantic_id} for comprehensive summary {summary_id}")

                except Exception as e:
                    logger.warning(f"Failed to create semantic entry for comprehensive summary: {e}")
                    # Don't fail the whole operation if semantic entry fails
            
            processing_time = time.time() - start_time
            
            if summary_id:
                # Save fingerprint
                try:
                    if fp:
                        ConfigModel.set('last_comprehensive_fingerprint', fp, 'Fingerprint of last comprehensive input')
                except Exception:
                    pass

                summary_text = summary_data.get('summary', 'No summary')
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
                        'time_span': time_span,
                        'summary_preview': summary_text[:200] + '...' if len(summary_text) > 200 else summary_text
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

