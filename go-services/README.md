# Obby Go Microservices

This directory contains Go microservices that provide high-performance implementations of performance-critical components.

## Services

### File Watcher Service (`file-watcher/`)
- **Port**: 50051 (default)
- **Purpose**: High-performance file system event monitoring
- **Features**:
  - fsnotify-based event detection
  - Channel-based debouncing (500ms default)
  - Pattern matching (.obbywatch/.obbyignore)
  - WSL+DrvFS detection and polling fallback

### Content Tracker Service (`content-tracker/`)
- **Port**: 50052 (default)
- **Purpose**: Fast file content hashing and diff generation
- **Features**:
  - Concurrent file processing with worker pool
  - SHA-256 hashing with sync.Pool
  - Unified diff generation (Myers algorithm)
  - Direct SQLite database writes

## Building

### Prerequisites
- Go 1.21 or later
- Protocol Buffers compiler (`protoc`)
  - Windows: Download from https://github.com/protocolbuffers/protobuf/releases
  - Or use Chocolatey: `choco install protoc`

### Build File Watcher
```bash
cd go-services/file-watcher
go mod download
go build ./cmd/server
```

### Build Content Tracker
```bash
cd go-services/content-tracker
go mod download
go build ./cmd/server
```

## Protocol Buffer Generation

Before running the services, you need to generate Go code from `.proto` files:

### File Watcher
```bash
cd go-services/file-watcher
protoc --go_out=. --go-grpc_out=. --go_opt=paths=source_relative --go-grpc_opt=paths=source_relative proto/file_watcher.proto
```

### Content Tracker
```bash
cd go-services/content-tracker
protoc --go_out=. --go-grpc_out=. --go_opt=paths=source_relative --go-grpc_opt=paths=source_relative proto/content_tracker.proto
```

## Running Services

### File Watcher
```bash
cd go-services/file-watcher
./server  # or go run ./cmd/server
```

Environment variables:
- `WATCHER_PORT`: Port to listen on (default: 50051)
- `LOG_LEVEL`: Log level (default: info)
- `DEBOUNCE_MS`: Debounce delay in milliseconds (default: 500)

### Content Tracker
```bash
cd go-services/content-tracker
./server  # or go run ./cmd/server
```

Environment variables:
- `TRACKER_PORT`: Port to listen on (default: 50052)
- `DB_PATH`: Path to SQLite database (default: obby.db)

## Python Integration

Python clients are available in `backend/clients/`:
- `file_watcher_client.py`: Client for File Watcher Service
- `content_tracker_client.py`: Client for Content Tracker Service

Generate Python protobuf code:
```bash
# File Watcher
python -m grpc_tools.protoc -Igo-services/file-watcher/proto --python_out=backend/clients/generated --grpc_python_out=backend/clients/generated go-services/file-watcher/proto/file_watcher.proto

# Content Tracker
python -m grpc_tools.protoc -Igo-services/content-tracker/proto --python_out=backend/clients/generated --grpc_python_out=backend/clients/generated go-services/content-tracker/proto/content_tracker.proto
```

## Feature Flags

Enable Go services via environment variables (see `config/settings.py`):
- `USE_GO_FILE_WATCHER=true`: Enable Go file watcher
- `USE_GO_CONTENT_TRACKER=true`: Enable Go content tracker

## Status

### Phase 1: File Watcher Service
- ✅ Project structure and dependencies
- ✅ Core watcher implementation (fsnotify wrapper)
- ✅ Debouncing implementation
- ✅ Pattern matching (.obbywatch/.obbyignore)
- ✅ WSL detection
- ⏳ gRPC server (requires protobuf generation)
- ⏳ Python client integration
- ⏳ Testing and optimization

### Phase 2: Content Tracker Service
- ✅ Project structure and dependencies
- ✅ Content hashing with pooling
- ✅ Worker pool implementation
- ✅ Diff generation
- ✅ Database integration
- ⏳ gRPC server (requires protobuf generation)
- ⏳ Python client integration
- ⏳ Performance testing

### Phase 3: Query Service (Optional)
- ⏳ Not started

### Phase 4: SSE Hub (Optional)
- ⏳ Not started

## Next Steps

1. Install Protocol Buffers compiler (`protoc`)
2. Generate protobuf code for both services
3. Uncomment gRPC server implementations
4. Generate Python protobuf code
5. Implement Python integration in `core/monitor.py` and `core/file_tracker.py`
6. Add unit and integration tests
7. Performance benchmarking
8. Gradual rollout with feature flags

