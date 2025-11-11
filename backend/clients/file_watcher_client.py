"""
gRPC client for the Go File Watcher Service.

This client communicates with the Go file watcher microservice via gRPC.
"""

import grpc
import logging
from typing import Iterator, Callable, Optional, List
from pathlib import Path

from generated import file_watcher_pb2, file_watcher_pb2_grpc

logger = logging.getLogger(__name__)


class FileWatcherClient:
    """Client for communicating with the Go File Watcher Service."""

    def __init__(self, host: str = "localhost", port: int = 50051):
        """
        Initialize the file watcher client.

        Args:
            host: Hostname of the Go service
            port: Port of the Go service
        """
        self.host = host
        self.port = port
        self.channel: Optional[grpc.Channel] = None
        self.stub: Optional[file_watcher_pb2_grpc.FileWatcherStub] = None

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
            self.stub = file_watcher_pb2_grpc.FileWatcherStub(self.channel)
            logger.info(f"Connected to File Watcher Service at {self.host}:{self.port}")

    def close(self):
        """Close the connection."""
        if self.channel:
            self.channel.close()
            self.channel = None
            self.stub = None

    def start_watching(
        self,
        watch_paths: List[str],
        ignore_patterns: List[str] = None,
        debounce_ms: int = 500
    ) -> bool:
        """
        Start watching specified directories.

        Args:
            watch_paths: List of directory paths to watch
            ignore_patterns: List of ignore patterns (from .obbyignore)
            debounce_ms: Debounce delay in milliseconds

        Returns:
            True if successful, False otherwise
        """
        if ignore_patterns is None:
            ignore_patterns = []

        self.connect()

        request = file_watcher_pb2.WatchRequest(
            watch_paths=watch_paths,
            ignore_patterns=ignore_patterns,
            debounce_ms=debounce_ms
        )

        try:
            response = self.stub.StartWatching(request)
            return response.success
        except grpc.RpcError as e:
            logger.error(f"gRPC error starting watch: {e.code()}: {e.details()}")
            return False

    def stop_watching(self) -> bool:
        """
        Stop watching all directories.

        Returns:
            True if successful, False otherwise
        """
        self.connect()

        request = file_watcher_pb2.StopRequest()

        try:
            response = self.stub.StopWatching(request)
            return response.success
        except grpc.RpcError as e:
            logger.error(f"gRPC error stopping watch: {e.code()}: {e.details()}")
            return False

    def stream_events(self, callback: Callable) -> None:
        """
        Stream file events and call callback for each event.

        Args:
            callback: Function to call for each event
        """
        self.connect()

        request = file_watcher_pb2.EventRequest()

        try:
            for event in self.stub.StreamEvents(request):
                callback(event)
        except grpc.RpcError as e:
            logger.error(f"Stream error: {e.code()}: {e.details()}")

    def update_patterns(
        self,
        watch_patterns: List[str] = None,
        ignore_patterns: List[str] = None
    ) -> bool:
        """
        Update watch and ignore patterns.

        Args:
            watch_patterns: List of watch patterns (from .obbywatch)
            ignore_patterns: List of ignore patterns (from .obbyignore)

        Returns:
            True if successful, False otherwise
        """
        if watch_patterns is None:
            watch_patterns = []
        if ignore_patterns is None:
            ignore_patterns = []

        self.connect()

        request = file_watcher_pb2.PatternUpdate(
            watch_patterns=watch_patterns,
            ignore_patterns=ignore_patterns
        )

        try:
            response = self.stub.UpdatePatterns(request)
            return response.success
        except grpc.RpcError as e:
            logger.error(f"gRPC error updating patterns: {e.code()}: {e.details()}")
            return False

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

