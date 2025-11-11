"""
gRPC client for the Go Content Tracker Service.

This client communicates with the Go content tracker microservice via gRPC.
"""

import grpc
import logging
from typing import Dict, List, Optional, Iterator
from pathlib import Path

from generated import content_tracker_pb2, content_tracker_pb2_grpc

logger = logging.getLogger(__name__)


class ContentTrackerClient:
    """Client for communicating with the Go Content Tracker Service."""

    def __init__(self, host: str = "localhost", port: int = 50052):
        """
        Initialize the content tracker client.

        Args:
            host: Hostname of the Go service
            port: Port of the Go service
        """
        self.host = host
        self.port = port
        self.channel: Optional[grpc.Channel] = None
        self.stub: Optional[content_tracker_pb2_grpc.ContentTrackerStub] = None

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
            self.stub = content_tracker_pb2_grpc.ContentTrackerStub(self.channel)
            logger.info(f"Connected to Content Tracker Service at {self.host}:{self.port}")

    def close(self):
        """Close the connection."""
        if self.channel:
            self.channel.close()
            self.channel = None
            self.stub = None

    def track_change(
        self,
        file_path: str,
        change_type: str,
        project_root: str
    ) -> Dict:
        """
        Track a single file change.

        Args:
            file_path: Path to the file
            change_type: Type of change (created, modified, deleted)
            project_root: Root directory of the project

        Returns:
            Dictionary with success, error, content_hash, file_size, version_id
        """
        self.connect()

        request = content_tracker_pb2.TrackRequest(
            file_path=file_path,
            change_type=change_type,
            project_root=project_root
        )

        try:
            response = self.stub.TrackChange(request)
            return {
                "success": response.success,
                "error": response.error,
                "content_hash": response.content_hash,
                "file_size": response.file_size,
                "version_id": response.version_id
            }
        except grpc.RpcError as e:
            logger.error(f"gRPC error: {e.code()}: {e.details()}")
            return {"success": False, "error": str(e)}

    def track_batch(
        self,
        requests: List[Dict]
    ) -> Iterator[Dict]:
        """
        Track multiple files concurrently.

        Args:
            requests: List of track requests, each with file_path, change_type, project_root

        Yields:
            Dictionary with file_path, success, error, content_hash, version_id
        """
        self.connect()

        track_requests = [
            content_tracker_pb2.TrackRequest(
                file_path=req["file_path"],
                change_type=req["change_type"],
                project_root=req["project_root"]
            )
            for req in requests
        ]

        batch_request = content_tracker_pb2.BatchRequest(requests=track_requests)

        try:
            for progress in self.stub.TrackBatch(batch_request):
                yield {
                    "file_path": progress.file_path,
                    "success": progress.success,
                    "error": progress.error,
                    "content_hash": progress.content_hash,
                    "version_id": progress.version_id
                }
        except grpc.RpcError as e:
            logger.error(f"gRPC error: {e.code()}: {e.details()}")

    def get_content_hash(self, file_path: str) -> Dict:
        """
        Get content hash without storing.

        Args:
            file_path: Path to the file

        Returns:
            Dictionary with success, error, content_hash, file_size
        """
        self.connect()

        request = content_tracker_pb2.HashRequest(file_path=file_path)

        try:
            response = self.stub.GetContentHash(request)
            return {
                "success": response.success,
                "error": response.error,
                "content_hash": response.content_hash,
                "file_size": response.file_size
            }
        except grpc.RpcError as e:
            logger.error(f"gRPC error: {e.code()}: {e.details()}")
            return {"success": False, "error": str(e)}

    def generate_diff(
        self,
        old_file_path: str,
        new_file_path: str,
        old_content: str,
        new_content: str
    ) -> Dict:
        """
        Generate diff between two files.

        Args:
            old_file_path: Path to old file
            new_file_path: Path to new file
            old_content: Old file content
            new_content: New file content

        Returns:
            Dictionary with success, error, diff_content, lines_added, lines_removed
        """
        self.connect()

        request = content_tracker_pb2.DiffRequest(
            old_file_path=old_file_path,
            new_file_path=new_file_path,
            old_content=old_content,
            new_content=new_content
        )

        try:
            response = self.stub.GenerateDiff(request)
            return {
                "success": response.success,
                "error": response.error,
                "diff_content": response.diff_content,
                "lines_added": response.lines_added,
                "lines_removed": response.lines_removed
            }
        except grpc.RpcError as e:
            logger.error(f"gRPC error: {e.code()}: {e.details()}")
            return {"success": False, "error": str(e)}

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

