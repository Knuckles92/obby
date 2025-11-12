"""
gRPC client for the Go SSE Hub Service.

This client communicates with the Go SSE Hub microservice via gRPC.
"""

import grpc
import logging
from typing import Iterator, List, Optional, Dict
from pathlib import Path

from generated import sse_pb2, sse_pb2_grpc

logger = logging.getLogger(__name__)


class SSEHubClient:
    """Client for communicating with the Go SSE Hub Service."""

    def __init__(self, host: str = "localhost", port: int = 50054):
        """
        Initialize the SSE Hub client.

        Args:
            host: Hostname of the Go service
            port: Port of the Go service
        """
        self.host = host
        self.port = port
        self.channel: Optional[grpc.Channel] = None
        self.stub: Optional[sse_pb2_grpc.SSEServiceStub] = None

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
            self.stub = sse_pb2_grpc.SSEServiceStub(self.channel)
            logger.info(f"Connected to SSE Hub Service at {self.host}:{self.port}")

    def close(self):
        """Close the connection."""
        if self.channel:
            self.channel.close()
            self.channel = None
            self.stub = None

    def publish(
        self,
        event: str,
        topic: str,
        data: str
    ) -> Dict:
        """
        Publish a message to the SSE hub.

        Args:
            event: Event type
            topic: Topic to publish to
            data: Message data

        Returns:
            Dictionary with success and client count
        """
        self.connect()

        request = sse_pb2.PublishRequest(
            event=event,
            topic=topic,
            data=data
        )

        try:
            response = self.stub.Publish(request)
            return {
                "success": response.success,
                "clients": response.clients
            }
        except grpc.RpcError as e:
            logger.error(f"gRPC error publishing message: {e.code()}: {e.details()}")
            return {"success": False, "error": str(e)}

    def register_client(
        self,
        topics: List[str],
        callback: callable
    ) -> None:
        """
        Register a client and stream messages.

        Args:
            topics: List of topics to subscribe to
            callback: Function to call for each received message
        """
        self.connect()

        request = sse_pb2.ClientRequest(topics=topics)

        try:
            for message in self.stub.RegisterClient(request):
                callback({
                    "event": message.event,
                    "topic": message.topic,
                    "data": message.data
                })
        except grpc.RpcError as e:
            logger.error(f"gRPC error in client registration: {e.code()}: {e.details()}")

    def broadcast_to_topic(self, topic: str, data: str, event: str = "message") -> Dict:
        """
        Convenience method to broadcast to a topic.

        Args:
            topic: Topic to broadcast to
            data: Message data
            event: Event type (default: "message")

        Returns:
            Dictionary with success and client count
        """
        return self.publish(event=event, topic=topic, data=data)

    def broadcast_update(self, data: str, topic: str = "updates") -> Dict:
        """
        Convenience method to broadcast an update.

        Args:
            data: Update data
            topic: Topic to broadcast to (default: "updates")

        Returns:
            Dictionary with success and client count
        """
        return self.publish(event="update", topic=topic, data=data)

    def broadcast_alert(self, data: str, topic: str = "alerts") -> Dict:
        """
        Convenience method to broadcast an alert.

        Args:
            data: Alert data
            topic: Topic to broadcast to (default: "alerts")

        Returns:
            Dictionary with success and client count
        """
        return self.publish(event="alert", topic=topic, data=data)

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()