"""gRPC clients for Go microservices."""

# Make generated modules available
import sys
from pathlib import Path

# Add generated directory to path if not already there
generated_path = Path(__file__).parent / "generated"
if str(generated_path) not in sys.path:
    sys.path.insert(0, str(generated_path))

# Export all client classes
from .content_tracker_client import ContentTrackerClient
from .file_watcher_client import FileWatcherClient
from .query_service_client import QueryServiceClient
from .sse_hub_client import SSEHubClient
from .sse_http_client import SSEHubHTTPClient

__all__ = [
    "ContentTrackerClient",
    "FileWatcherClient",
    "QueryServiceClient",
    "SSEHubClient",
    "SSEHubHTTPClient"
]
