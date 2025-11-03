"""
Agent Logging Service
====================

Centralized service for logging and retrieving Claude Agent SDK operations.

This service provides transparency into AI operations by storing detailed
logs of all agent activities including file exploration, tool usage, and
operation timings.

Features:
- Store agent operations in database
- Query logs by session, operation type, phase
- Generate usage statistics
- Support manual cleanup operations
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from database.models import db
from config import settings as cfg

logger = logging.getLogger(__name__)


class AgentLoggingService:
    """Service for logging and querying agent operations."""

    def __init__(self):
        """Initialize the agent logging service."""
        self.enabled = cfg.AGENT_LOGGING_ENABLED
        self.verbosity = cfg.AGENT_LOG_VERBOSITY
        self.include_prompts = cfg.AGENT_LOG_INCLUDE_PROMPTS
        self.include_responses = cfg.AGENT_LOG_INCLUDE_RESPONSES

        if self.enabled:
            logger.info(f"Agent logging service initialized (verbosity={self.verbosity})")
        else:
            logger.info("Agent logging service initialized (DISABLED)")

    def log_operation(
        self,
        session_id: str,
        phase: str,
        operation: str,
        details: Optional[Dict[str, Any]] = None,
        files_processed: int = 0,
        total_files: Optional[int] = None,
        current_file: Optional[str] = None,
        timing: Optional[Dict[str, Any]] = None,
        insight_id: Optional[int] = None
    ) -> bool:
        """
        Log an agent operation to the database.

        Args:
            session_id: Unique session identifier for the agent operation
            phase: Operation phase (data_collection, file_exploration, analysis, generation, error)
            operation: Description of the operation
            details: Optional dict with additional operation details
            files_processed: Number of files processed so far
            total_files: Total number of files to process
            current_file: Path to currently processing file
            timing: Optional dict with timing information (start_time, end_time, duration)
            insight_id: Optional insight ID if this is an insight operation

        Returns:
            bool: True if logged successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Serialize details and timing as JSON
            details_json = json.dumps(details) if details else None
            timing_json = json.dumps(timing) if timing else None

            # Insert log entry
            insert_query = """
                INSERT INTO agent_action_logs
                (session_id, insight_id, phase, operation, details, files_processed,
                 total_files, current_file, timing, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """

            params = (
                session_id,
                insight_id,
                phase,
                operation,
                details_json,
                files_processed,
                total_files,
                current_file,
                timing_json,
                datetime.now().isoformat()
            )

            db.execute_update(insert_query, params)
            logger.debug(f"Logged agent operation: session={session_id}, phase={phase}, operation={operation}")
            return True

        except Exception as e:
            logger.error(f"Failed to log agent operation: {e}", exc_info=True)
            return False

    def get_session_logs(
        self,
        session_id: str,
        order_by: str = 'timestamp ASC'
    ) -> List[Dict[str, Any]]:
        """
        Retrieve all logs for a specific session.

        Args:
            session_id: Session identifier
            order_by: Sort order (default: chronological)

        Returns:
            List of log entries as dicts
        """
        try:
            query = f"""
                SELECT id, session_id, insight_id, phase, operation, details,
                       files_processed, total_files, current_file, timing,
                       timestamp, created_at
                FROM agent_action_logs
                WHERE session_id = ?
                ORDER BY {order_by}
            """

            rows = db.execute_query(query, (session_id,))
            return [self._parse_log_row(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get session logs for {session_id}: {e}")
            return []

    def get_recent_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        operation_type: Optional[str] = None,
        phase: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Retrieve recent agent logs with optional filtering.

        Args:
            limit: Maximum number of logs to retrieve
            offset: Pagination offset
            operation_type: Optional filter by operation type (summary, chat, insights)
            phase: Optional filter by phase (data_collection, file_exploration, analysis, generation, error)

        Returns:
            Tuple of (log entries, total count)
        """
        try:
            # Build WHERE clause
            where_clauses = []
            params = []

            if operation_type:
                where_clauses.append("operation LIKE ?")
                params.append(f"%{operation_type}%")

            if phase:
                where_clauses.append("phase = ?")
                params.append(phase)

            where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            # Get total count
            count_query = f"SELECT COUNT(*) as count FROM agent_action_logs {where_clause}"
            count_result = db.execute_query(count_query, tuple(params))
            total_count = count_result[0]['count'] if count_result else 0

            # Get paginated results
            query = f"""
                SELECT id, session_id, insight_id, phase, operation, details,
                       files_processed, total_files, current_file, timing,
                       timestamp, created_at
                FROM agent_action_logs
                {where_clause}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """

            params.extend([limit, offset])
            rows = db.execute_query(query, tuple(params))
            logs = [self._parse_log_row(row) for row in rows]

            return logs, total_count

        except Exception as e:
            logger.error(f"Failed to get recent logs: {e}")
            return [], 0

    def get_logs_by_phase(
        self,
        phase: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve logs filtered by phase.

        Args:
            phase: Phase to filter by (data_collection, file_exploration, analysis, generation, error)
            limit: Maximum number of logs to retrieve

        Returns:
            List of log entries
        """
        try:
            query = """
                SELECT id, session_id, insight_id, phase, operation, details,
                       files_processed, total_files, current_file, timing,
                       timestamp, created_at
                FROM agent_action_logs
                WHERE phase = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """

            rows = db.execute_query(query, (phase, limit))
            return [self._parse_log_row(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get logs by phase {phase}: {e}")
            return []

    def get_logs_in_range(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """
        Retrieve logs within a specific time range.

        Args:
            start_time: Start of time range
            end_time: End of time range

        Returns:
            List of log entries
        """
        try:
            query = """
                SELECT id, session_id, insight_id, phase, operation, details,
                       files_processed, total_files, current_file, timing,
                       timestamp, created_at
                FROM agent_action_logs
                WHERE timestamp >= ? AND timestamp <= ?
                ORDER BY timestamp DESC
            """

            params = (start_time.isoformat(), end_time.isoformat())
            rows = db.execute_query(query, params)
            return [self._parse_log_row(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get logs in range: {e}")
            return []

    def get_tool_usage_stats(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get aggregate statistics on tool usage.

        Args:
            start_time: Optional start time for filtering
            end_time: Optional end time for filtering

        Returns:
            Dict with tool usage statistics
        """
        try:
            where_clause = ""
            params = []

            if start_time and end_time:
                where_clause = "WHERE timestamp >= ? AND timestamp <= ?"
                params = [start_time.isoformat(), end_time.isoformat()]

            # Get operations that contain tool names
            query = f"""
                SELECT operation, COUNT(*) as count
                FROM agent_action_logs
                {where_clause}
                GROUP BY operation
                ORDER BY count DESC
            """

            rows = db.execute_query(query, tuple(params))

            # Parse tool usage from operations
            tool_stats = {
                'Read': 0,
                'Write': 0,
                'Bash': 0,
                'Grep': 0,
                'Glob': 0,
                'Edit': 0,
                'Other': 0
            }

            for row in rows:
                operation = row['operation']
                count = row['count']

                # Check if operation mentions a tool
                matched = False
                for tool in ['Read', 'Write', 'Bash', 'Grep', 'Glob', 'Edit']:
                    if tool.lower() in operation.lower():
                        tool_stats[tool] += count
                        matched = True
                        break

                if not matched:
                    tool_stats['Other'] += count

            return {
                'tool_usage': tool_stats,
                'total_operations': sum(tool_stats.values())
            }

        except Exception as e:
            logger.error(f"Failed to get tool usage stats: {e}")
            return {'tool_usage': {}, 'total_operations': 0}

    def get_operation_stats(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get aggregate statistics on operations.

        Args:
            start_time: Optional start time for filtering
            end_time: Optional end time for filtering

        Returns:
            Dict with operation statistics
        """
        try:
            where_clause = ""
            params = []

            if start_time and end_time:
                where_clause = "WHERE timestamp >= ? AND timestamp <= ?"
                params = [start_time.isoformat(), end_time.isoformat()]

            # Get phase distribution
            phase_query = f"""
                SELECT phase, COUNT(*) as count
                FROM agent_action_logs
                {where_clause}
                GROUP BY phase
            """

            phase_rows = db.execute_query(phase_query, tuple(params))
            phase_distribution = {row['phase']: row['count'] for row in phase_rows}

            # Get operation type distribution (summary, chat, insights)
            type_stats = {
                'summary': 0,
                'chat': 0,
                'insights': 0,
                'other': 0
            }

            operation_query = f"""
                SELECT operation, COUNT(*) as count
                FROM agent_action_logs
                {where_clause}
            """

            operation_rows = db.execute_query(operation_query, tuple(params))

            for row in operation_rows:
                operation = row['operation'].lower()
                count = row['count']

                if 'summary' in operation:
                    type_stats['summary'] += count
                elif 'chat' in operation:
                    type_stats['chat'] += count
                elif 'insight' in operation:
                    type_stats['insights'] += count
                else:
                    type_stats['other'] += count

            # Get average operation duration
            duration_query = f"""
                SELECT timing
                FROM agent_action_logs
                {where_clause}
                WHERE timing IS NOT NULL
            """

            duration_rows = db.execute_query(duration_query, tuple(params))
            durations = []

            for row in duration_rows:
                try:
                    timing = json.loads(row['timing'])
                    if 'duration' in timing:
                        durations.append(timing['duration'])
                except (json.JSONDecodeError, KeyError):
                    pass

            avg_duration = sum(durations) / len(durations) if durations else 0

            return {
                'phase_distribution': phase_distribution,
                'operation_types': type_stats,
                'avg_duration_ms': avg_duration,
                'total_operations': sum(phase_distribution.values())
            }

        except Exception as e:
            logger.error(f"Failed to get operation stats: {e}")
            return {
                'phase_distribution': {},
                'operation_types': {},
                'avg_duration_ms': 0,
                'total_operations': 0
            }

    def get_unique_sessions(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Get list of unique agent sessions with summary information.

        Args:
            limit: Maximum number of sessions to retrieve
            offset: Pagination offset

        Returns:
            Tuple of (session summaries, total count)
        """
        try:
            # Get total count
            count_query = "SELECT COUNT(DISTINCT session_id) as count FROM agent_action_logs"
            count_result = db.execute_query(count_query)
            total_count = count_result[0]['count'] if count_result else 0

            # Get paginated sessions
            query = """
                SELECT
                    session_id,
                    MIN(timestamp) as start_time,
                    MAX(timestamp) as end_time,
                    COUNT(*) as operation_count,
                    MAX(files_processed) as files_processed,
                    GROUP_CONCAT(DISTINCT phase) as phases
                FROM agent_action_logs
                GROUP BY session_id
                ORDER BY start_time DESC
                LIMIT ? OFFSET ?
            """

            rows = db.execute_query(query, (limit, offset))

            sessions = []
            for row in rows:
                sessions.append({
                    'session_id': row['session_id'],
                    'start_time': row['start_time'],
                    'end_time': row['end_time'],
                    'operation_count': row['operation_count'],
                    'files_processed': row['files_processed'] or 0,
                    'phases': row['phases'].split(',') if row['phases'] else []
                })

            return sessions, total_count

        except Exception as e:
            logger.error(f"Failed to get unique sessions: {e}")
            return [], 0

    def delete_session_logs(self, session_id: str) -> bool:
        """
        Delete all logs for a specific session.

        Args:
            session_id: Session identifier

        Returns:
            bool: True if deleted successfully
        """
        try:
            query = "DELETE FROM agent_action_logs WHERE session_id = ?"
            db.execute_update(query, (session_id,))
            logger.info(f"Deleted agent logs for session {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete session logs for {session_id}: {e}")
            return False

    def delete_logs_before(self, timestamp: datetime) -> int:
        """
        Delete all logs before a specific timestamp.

        Args:
            timestamp: Delete logs before this time

        Returns:
            int: Number of logs deleted
        """
        try:
            # Get count first
            count_query = "SELECT COUNT(*) as count FROM agent_action_logs WHERE timestamp < ?"
            count_result = db.execute_query(count_query, (timestamp.isoformat(),))
            count = count_result[0]['count'] if count_result else 0

            # Delete logs
            delete_query = "DELETE FROM agent_action_logs WHERE timestamp < ?"
            db.execute_update(delete_query, (timestamp.isoformat(),))

            logger.info(f"Deleted {count} agent logs before {timestamp.isoformat()}")
            return count

        except Exception as e:
            logger.error(f"Failed to delete logs before {timestamp}: {e}")
            return 0

    def count_logs(self) -> int:
        """
        Get total count of agent logs.

        Returns:
            int: Total number of logs
        """
        try:
            query = "SELECT COUNT(*) as count FROM agent_action_logs"
            result = db.execute_query(query)
            return result[0]['count'] if result else 0

        except Exception as e:
            logger.error(f"Failed to count logs: {e}")
            return 0

    def _parse_log_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse a database row into a log entry dict.

        Args:
            row: Database row dict

        Returns:
            Parsed log entry dict
        """
        try:
            # Parse JSON fields
            details = json.loads(row['details']) if row.get('details') else None
            timing = json.loads(row['timing']) if row.get('timing') else None

            return {
                'id': row['id'],
                'session_id': row['session_id'],
                'insight_id': row.get('insight_id'),
                'phase': row['phase'],
                'operation': row['operation'],
                'details': details,
                'files_processed': row.get('files_processed', 0),
                'total_files': row.get('total_files'),
                'current_file': row.get('current_file'),
                'timing': timing,
                'timestamp': row['timestamp'],
                'created_at': row.get('created_at')
            }

        except Exception as e:
            logger.error(f"Failed to parse log row: {e}")
            return row


# Singleton instance
_agent_logging_service = None


def get_agent_logging_service() -> AgentLoggingService:
    """
    Get the singleton agent logging service instance.

    Returns:
        AgentLoggingService instance
    """
    global _agent_logging_service
    if _agent_logging_service is None:
        _agent_logging_service = AgentLoggingService()
    return _agent_logging_service
