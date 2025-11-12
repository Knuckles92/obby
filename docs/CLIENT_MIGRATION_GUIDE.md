# Python Clients Migration Guide

This guide shows how to update Python code to use the new Go services clients.

## Available Go Services

| Service | Port | Purpose | Status |
|---------|------|---------|--------|
| File Watcher | 50051 | File system monitoring | ✅ Ready |
| Content Tracker | 50052 | Content tracking & diff generation | ✅ Ready |
| Query Service | 50053 | Database queries & analytics | ✅ Ready |
| SSE Hub | 50054 (gRPC), 8080 (HTTP) | Real-time events | ✅ Ready |

## Updated Client Usage

### 1. Query Service Client

```python
from backend.clients import QueryServiceClient

# Initialize client
query_client = QueryServiceClient(host="localhost", port=50053)

# Get recent diffs
with query_client:
    for diff in query_client.get_recent_diffs(limit=20):
        print(f"File: {diff['file_path']}, Type: {diff['change_type']}")

# Search content
with query_client:
    for result in query_client.search_content("python", limit=10):
        print(f"File: {result['file_path']}, Content: {result['highlighted']}")

# Get time analysis
with query_client:
    analysis = query_client.get_time_analysis(start_timestamp, end_timestamp)
    print(f"Files changed: {analysis['total_files_changed']}")
```

### 2. SSE Hub Client (gRPC)

```python
from backend.clients import SSEHubClient

# Initialize gRPC client
sse_client = SSEHubClient(host="localhost", port=50054)

# Publish message
with sse_client:
    result = sse_client.publish(event="update", topic="updates", data="New data")
    print(f"Published to {result['clients']} clients")

# Register for streaming (using callback)
def message_handler(message):
    print(f"Received: {message}")

with sse_client:
    sse_client.register_client(topics=["updates"], callback=message_handler)
```

### 3. SSE Hub HTTP Client (for frontend)

```python
from backend.clients import SSEHubHTTPClient
import asyncio

async def handle_sse_event(event):
    print(f"SSE Event: {event}")

async def setup_sse():
    # Create HTTP client
    http_client = SSEHubHTTPClient(base_url="http://localhost:8080")
    
    try:
        # Check health
        health = await http_client.health_check()
        print(f"SSE Hub health: {health}")
        
        # Subscribe to events
        await http_client.subscribe_to_sse(["updates"], handle_sse_event)
        
    finally:
        await http_client.close()

# Run the SSE setup
asyncio.run(setup_sse())
```

## Service Configuration Updates

### Backend Configuration (config/settings.py)

Update service endpoints:

```python
# Go services configuration
GO_SERVICES = {
    "file_watcher": {
        "host": "localhost",
        "port": 50051,
        "enabled": True
    },
    "content_tracker": {
        "host": "localhost", 
        "port": 50052,
        "enabled": True
    },
    "query_service": {
        "host": "localhost",
        "port": 50053,
        "enabled": True
    },
    "sse_hub": {
        "grpc": {
            "host": "localhost",
            "port": 50054
        },
        "http": {
            "base_url": "http://localhost:8080"
        }
    }
}
```

### Environment Variables

```bash
# Add to .env file or environment
export FILE_WATCHER_HOST=localhost
export FILE_WATCHER_PORT=50051
export CONTENT_TRACKER_HOST=localhost
export CONTENT_TRACKER_PORT=50052
export QUERY_SERVICE_HOST=localhost
export QUERY_SERVICE_PORT=50053
export SSE_HUB_GRPC_HOST=localhost
export SSE_HUB_GRPC_PORT=50054
export SSE_HUB_HTTP_URL=http://localhost:8080
```

## Integration Examples

### 1. Backend Routes Update

```python
# routes/files.py - Update file queries
from backend.clients import QueryServiceClient, SSEHubClient

@api.route('/files/recent')
def get_recent_files():
    query_client = QueryServiceClient()
    with query_client:
        diffs = list(query_client.get_recent_diffs(limit=50))
    return {"diffs": diffs}

# Update frontend with real-time events
@api.route('/files/watch-start', methods=['POST'])
def start_file_watching():
    # Notify frontend of file changes
    sse_client = SSEHubClient()
    with sse_client:
        sse_client.broadcast_update("File watching started", "updates")
    
    return {"status": "started"}
```

### 2. Frontend SSE Integration

```python
# backend/websocket_handlers.py - Update for SSE Hub
from backend.clients import SSEHubHTTPClient

async def setup_frontend_sse():
    """Set up SSE for frontend real-time updates."""
    client = SSEHubHTTPClient()
    
    async def on_session_update(event):
        # Send to frontend WebSocket
        await broadcast_to_frontend("session_update", event["data"])
    
    async def on_file_change(event):
        # Send to frontend WebSocket  
        await broadcast_to_frontend("file_change", event["data"])
    
    # Subscribe to relevant topics
    await client.subscribe_to_updates(on_session_update)
    await client.subscribe_to_notifications(on_file_change)
```

### 3. Error Handling

```python
from backend.clients import QueryServiceClient, grpc
import logging

logger = logging.getLogger(__name__)

def safe_query_service_call(func, *args, **kwargs):
    """Safe wrapper for query service calls with fallback."""
    try:
        with QueryServiceClient() as client:
            return func(client, *args, **kwargs)
    except grpc.RpcError as e:
        if e.code() == grpc.StatusCode.UNAVAILABLE:
            logger.warning("Query Service unavailable, using fallback")
            return get_fallback_data()
        else:
            logger.error(f"Query Service error: {e}")
            return {}
    except Exception as e:
        logger.error(f"Unexpected error in query service: {e}")
        return {}
```

## Migration Checklist

- [ ] Update imports to use new client classes
- [ ] Update port numbers in configuration
- [ ] Add proper error handling for service unavailability
- [ ] Test all service integrations
- [ ] Update environment variables
- [ ] Verify frontend SSE connections work
- [ ] Test health check endpoints
- [ ] Update documentation and deployment scripts

## Health Check Integration

```python
# backend/services/health_checker.py
from backend.clients import QueryServiceClient, SSEHubClient, SSEHubHTTPClient
import asyncio

async def check_all_services():
    """Check health of all Go services."""
    results = {}
    
    # Check Query Service
    try:
        with QueryServiceClient() as client:
            # Simple test call
            analysis = client.get_time_analysis(time.time() - 3600, time.time())
            results["query_service"] = "healthy" if analysis else "unhealthy"
    except Exception as e:
        results["query_service"] = f"error: {e}"
    
    # Check SSE Hub gRPC
    try:
        with SSEHubClient() as client:
            result = client.publish("health_check", "system", "ping")
            results["sse_hub_grpc"] = "healthy" if result["success"] else "unhealthy"
    except Exception as e:
        results["sse_hub_grpc"] = f"error: {e}"
    
    # Check SSE Hub HTTP
    try:
        client = SSEHubHTTPClient()
        health = await client.health_check()
        results["sse_hub_http"] = health.get("status", "unknown")
        await client.close()
    except Exception as e:
        results["sse_hub_http"] = f"error: {e}"
    
    return results
```

## Performance Considerations

1. **Connection Pooling**: Use context managers to ensure proper connection cleanup
2. **Streaming Responses**: For large datasets, use streaming methods (GetRecentDiffs, SearchContent, etc.)
3. **Health Monitoring**: Implement regular health checks to detect service issues
4. **Fallback Mechanisms**: Implement fallbacks when services are temporarily unavailable
5. **Caching**: Cache frequent query results to reduce service load

## Troubleshooting

### Service Connection Issues

```python
# Check if services are running
import grpc

def check_service_health(host, port):
    """Simple service health check."""
    try:
        channel = grpc.insecure_channel(f"{host}:{port}")
        # Try to establish connection without making calls
        channel._connectivity_watch.__next__()  # Check connectivity
        channel.close()
        return True
    except Exception:
        return False

# Usage
services = [
    ("query_service", "localhost", 50053),
    ("sse_hub", "localhost", 50054)
]

for name, host, port in services:
    if check_service_health(host, port):
        print(f"✅ {name} is running")
    else:
        print(f"❌ {name} is not running")
```

### Common Issues

1. **Port Conflicts**: Ensure ports 50051-50054 and 8080 are available
2. **Protobuf Generation**: Regenerate Python protobuf files if Go proto files changed
3. **SSL/TLS**: Update client connections if services use secure channels
4. **Network Issues**: Check firewall rules for service communication