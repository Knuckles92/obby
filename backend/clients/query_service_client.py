"""
gRPC client for the Go Query Service.

This client communicates with the Go query service microservice via gRPC.
"""

import grpc
import logging
from typing import Iterator, List, Optional, Dict
from pathlib import Path

from generated import query_pb2, query_pb2_grpc

logger = logging.getLogger(__name__)


class QueryServiceClient:
    """Client for communicating with the Go Query Service."""

    def __init__(self, host: str = "localhost", port: int = 50053):
        """
        Initialize the query service client.

        Args:
            host: Hostname of the Go service
            port: Port of the Go service
        """
        self.host = host
        self.port = port
        self.channel: Optional[grpc.Channel] = None
        self.stub: Optional[query_pb2_grpc.QueryServiceStub] = None

    def connect(self):
        """Establish connection to the Go service."""
        if self.channel is None:
            self.channel = grpc.insecure_channel(
                f"{self.host}:{self.port}",
                options=[
                    ('grpc.keepalive_time_ms', 10000),
                    ('grpc.keepalive_timeout_ms', 5000),
                    ('grpc.keepalive_permit_without_calls', True),
                    ('grpc.http2.max_pings_without_data', 0),
                ]
            )
            self.stub = query_pb2_grpc.QueryServiceStub(self.channel)
            logger.info(f"Connected to Query Service at {self.host}:{self.port}")

    def close(self):
        """Close the connection."""
        if self.channel:
            self.channel.close()
            self.channel = None
            self.stub = None

    def get_recent_diffs(self, limit: int = 20) -> Iterator[Dict]:
        """
        Get recent diffs from the database.

        Args:
            limit: Maximum number of diffs to return

        Yields:
            Dictionary with diff information
        """
        self.connect()

        request = query_pb2.DiffQuery(limit=limit)

        try:
            for diff in self.stub.GetRecentDiffs(request):
                yield {
                    "id": diff.id,
                    "file_path": diff.file_path,
                    "change_type": diff.change_type,
                    "diff_content": diff.diff_content,
                    "lines_added": diff.lines_added,
                    "lines_removed": diff.lines_removed,
                    "timestamp": diff.timestamp,
                    "content_hash": diff.content_hash,
                    "size": diff.size
                }
        except grpc.RpcError as e:
            logger.error(f"gRPC error getting recent diffs: {e.code()}: {e.details()}")

    def get_diffs_since(self, timestamp: int, limit: int = 50) -> Iterator[Dict]:
        """
        Get diffs since a specific timestamp.

        Args:
            timestamp: Unix timestamp to get diffs since
            limit: Maximum number of diffs to return

        Yields:
            Dictionary with diff information
        """
        self.connect()

        request = query_pb2.SinceQuery(timestamp=timestamp, limit=limit)

        try:
            for diff in self.stub.GetDiffsSince(request):
                yield {
                    "id": diff.id,
                    "file_path": diff.file_path,
                    "change_type": diff.change_type,
                    "diff_content": diff.diff_content,
                    "lines_added": diff.lines_added,
                    "lines_removed": diff.lines_removed,
                    "timestamp": diff.timestamp,
                    "content_hash": diff.content_hash,
                    "size": diff.size
                }
        except grpc.RpcError as e:
            logger.error(f"gRPC error getting diffs since: {e.code()}: {e.details()}")

    def get_file_versions(self, file_path: str, limit: int = 20) -> Iterator[Dict]:
        """
        Get version history for a specific file.

        Args:
            file_path: Path to the file
            limit: Maximum number of versions to return

        Yields:
            Dictionary with file version information
        """
        self.connect()

        request = query_pb2.FileQuery(file_path=file_path, limit=limit)

        try:
            for version in self.stub.GetFileVersions(request):
                yield {
                    "id": version.id,
                    "file_path": version.file_path,
                    "content_hash": version.content_hash,
                    "size": version.size,
                    "timestamp": version.timestamp
                }
        except grpc.RpcError as e:
            logger.error(f"gRPC error getting file versions: {e.code()}: {e.details()}")

    def search_content(self, query: str, limit: int = 20) -> Iterator[Dict]:
        """
        Search content across all files using full-text search.

        Args:
            query: Search query string
            limit: Maximum number of results to return

        Yields:
            Dictionary with search results
        """
        self.connect()

        request = query_pb2.SearchQuery(query=query, limit=limit)

        try:
            for result in self.stub.SearchContent(request):
                yield {
                    "file_path": result.file_path,
                    "content": result.content,
                    "highlighted": result.highlighted,
                    "rank": result.rank
                }
        except grpc.RpcError as e:
            logger.error(f"gRPC error searching content: {e.code()}: {e.details()}")

    def get_topic_files(self, topic: str, limit: int = 20) -> Iterator[Dict]:
        """
        Get files related to a specific topic.

        Args:
            topic: Topic to search for
            limit: Maximum number of files to return

        Yields:
            Dictionary with file information
        """
        self.connect()

        request = query_pb2.TopicQuery(topic=topic, limit=limit)

        try:
            for file_record in self.stub.GetTopicFiles(request):
                yield {
                    "file_path": file_record.file_path,
                    "last_modified": file_record.last_modified,
                    "size": file_record.size
                }
        except grpc.RpcError as e:
            logger.error(f"gRPC error getting topic files: {e.code()}: {e.details()}")

    def get_time_analysis(self, start_timestamp: int, end_timestamp: int) -> Dict:
        """
        Get time-based activity analysis.

        Args:
            start_timestamp: Start timestamp for analysis
            end_timestamp: End timestamp for analysis

        Returns:
            Dictionary with time analysis results
        """
        self.connect()

        request = query_pb2.TimeQuery(
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp
        )

        try:
            result = self.stub.GetTimeAnalysis(request)
            return {
                "total_files_changed": result.total_files_changed,
                "total_lines_added": result.total_lines_added,
                "total_lines_removed": result.total_lines_removed,
                "top_topics": list(result.top_topics),
                "top_keywords": list(result.top_keywords)
            }
        except grpc.RpcError as e:
            logger.error(f"gRPC error getting time analysis: {e.code()}: {e.details()}")
            return {}

    def get_activity_stats(self, start_timestamp: int, end_timestamp: int) -> Dict:
        """
        Get activity statistics for a time period.

        Args:
            start_timestamp: Start timestamp for stats
            end_timestamp: End timestamp for stats

        Returns:
            Dictionary with activity statistics
        """
        self.connect()

        request = query_pb2.StatsQuery(
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp
        )

        try:
            stats = self.stub.GetActivityStats(request)
            return {
                "files_changed": stats.files_changed,
                "total_changes": stats.total_changes,
                "lines_added": stats.lines_added,
                "lines_removed": stats.lines_removed,
                "avg_changes_per_file": stats.avg_changes_per_file
            }
        except grpc.RpcError as e:
            logger.error(f"gRPC error getting activity stats: {e.code()}: {e.details()}")
            return {}

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()