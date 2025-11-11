# Obby Go Migration Plan
**Complete Migration Strategy for Python → Go Hybrid Architecture**

---

## Executive Summary

### Overview
This document outlines a comprehensive plan to migrate performance-critical components of Obby from Python to Go while maintaining Python for AI integration and business logic. The hybrid architecture approach balances performance gains with development velocity and ecosystem advantages.

### Goals
- **10x improvement** in file event processing throughput
- **5-10x reduction** in latency for file change detection
- **3-6x reduction** in memory usage
- **50-100x increase** in concurrent SSE connection capacity
- **Maintain** rapid development velocity for AI features

### Timeline
- **Phase 1**: Go File Watcher Service (3-4 weeks)
- **Phase 2**: Go Content Tracker Service (2-3 weeks)
- **Phase 3**: Go Database Layer (2-3 weeks, optional)
- **Phase 4**: Go SSE Hub (2 weeks, optional)
- **Total**: 9-11 weeks for core migration (can be extended to 15 weeks with all optional phases)

### Expected Outcomes
- File watching: 1,000 → 10,000+ events/sec
- Content hashing: 50 → 500 MB/s
- Database queries: 1,000 → 5,000+ queries/sec
- SSE connections: 100-200 → 10,000+ concurrent clients
- Memory baseline: 150-300 MB → 50 MB

---

## Architecture Design

### Current Architecture (Python-Only)
```
┌─────────────────────────────────────────────────┐
│            FastAPI Backend (Python)             │
│  ┌──────────────────────────────────────────┐   │
│  │ Routes Layer (APIRouter modules)         │   │
│  └──────────────────┬───────────────────────┘   │
│                     │                            │
│  ┌──────────────────┴───────────────────────┐   │
│  │ Services Layer                           │   │
│  │ - SessionSummaryService                  │   │
│  │ - SummaryNoteService                     │   │
│  │ - AgentLoggingService                    │   │
│  └──────────┬───────────────────────────────┘   │
│             │                                    │
│  ┌──────────┴───────────┬─────────────────┐     │
│  │ Core Monitoring      │ AI Integration  │     │
│  │ - ObbyMonitor        │ - ClaudeAgent   │     │
│  │ - FileContentTracker │ - Agent SDK     │     │
│  │ - FileWatcher        │                 │     │
│  └──────────┬───────────┴─────────────────┘     │
│             │                                    │
│  ┌──────────┴───────────────────────────────┐   │
│  │ Database Layer (SQLite)                  │   │
│  │ - Thread-local connection pooling        │   │
│  │ - FileQueries, EventQueries              │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

### Target Hybrid Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (Python)                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Routes Layer - HTTP/REST API                             │   │
│  │ - /api/files, /api/session-summary, /api/summary-notes   │   │
│  │ - /api/search, /api/config, /api/admin                   │   │
│  └────────────────────┬─────────────────────────────────────┘   │
│                       │                                          │
│  ┌────────────────────┴─────────────────────────────────────┐   │
│  │ Services Layer - Business Logic                          │   │
│  │ - Session summaries, format templates                    │   │
│  └────────────────────┬─────────────────────────────────────┘   │
│                       │                                          │
│  ┌────────────────────┴─────────────────────────────────────┐   │
│  │ AI Integration Layer                                     │   │
│  │ - Claude Agent SDK (Python-only)                         │   │
│  │ - Autonomous file exploration                            │   │
│  │ - Summary generation                                     │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────┬──────────────────────────────────────────────┘
                    │
                    │ gRPC (Protocol Buffers)
                    │
┌───────────────────┴──────────────────────────────────────────────┐
│                    Go Microservices Layer                        │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ File Watcher Service (:50051)                             │  │
│  │ - fsnotify-based event detection                          │  │
│  │ - Channel-based debouncing (500ms)                        │  │
│  │ - .obbywatch/.obbyignore pattern matching                 │  │
│  │ - WSL+DrvFS polling fallback detection                    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Content Tracker Service (:50052)                          │  │
│  │ - Concurrent file reading with goroutine pool             │  │
│  │ - SHA-256 content hashing with sync.Pool                  │  │
│  │ - Diff generation (Myers algorithm)                       │  │
│  │ - Direct SQLite database writes                           │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Query Service (:50053) [OPTIONAL]                         │  │
│  │ - Optimized connection pooling (25 max, 5 idle)           │  │
│  │ - Prepared statement caching                              │  │
│  │ - Hot path query optimization                             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ SSE Hub Service (:50054) [OPTIONAL]                       │  │
│  │ - Goroutine-per-client architecture                       │  │
│  │ - Channel-based broadcasting                              │  │
│  │ - Context-based client lifecycle                          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Shared Database Layer                                     │  │
│  │ - SQLite with WAL mode, foreign keys                      │  │
│  │ - Connection pooling via database/sql                     │  │
│  └───────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### Communication Protocol

#### gRPC Service Definitions
All Python ↔ Go communication uses gRPC with Protocol Buffers for type safety and performance.

**File Watcher Service** (`file_watcher.proto`):
```protobuf
syntax = "proto3";

package obby.filewatcher;

service FileWatcher {
  // Start watching specified directories
  rpc StartWatching(WatchRequest) returns (WatchResponse);

  // Stop watching
  rpc StopWatching(StopRequest) returns (StopResponse);

  // Stream file events
  rpc StreamEvents(EventRequest) returns (stream FileEvent);

  // Update ignore/watch patterns
  rpc UpdatePatterns(PatternUpdate) returns (PatternResponse);
}

message WatchRequest {
  repeated string watch_paths = 1;
  repeated string ignore_patterns = 2;
  int32 debounce_ms = 3;
}

message FileEvent {
  string path = 1;
  string event_type = 2; // created, modified, deleted, renamed
  int64 timestamp = 3;
  string old_path = 4; // for rename events
}
```

**Content Tracker Service** (`content_tracker.proto`):
```protobuf
syntax = "proto3";

package obby.contenttracker;

service ContentTracker {
  // Track a single file change
  rpc TrackChange(TrackRequest) returns (TrackResponse);

  // Track multiple files concurrently
  rpc TrackBatch(BatchRequest) returns (stream TrackProgress);

  // Get content hash without storing
  rpc GetContentHash(HashRequest) returns (HashResponse);

  // Generate diff between two files
  rpc GenerateDiff(DiffRequest) returns (DiffResponse);
}

message TrackRequest {
  string file_path = 1;
  string change_type = 2;
  string project_root = 3;
}

message TrackResponse {
  bool success = 1;
  string error = 2;
  string content_hash = 3;
  int64 file_size = 4;
  int64 version_id = 5;
}
```

**Query Service** (`query.proto`):
```protobuf
syntax = "proto3";

package obby.query;

service QueryService {
  // Get recent diffs
  rpc GetRecentDiffs(DiffQuery) returns (DiffResult);

  // Get diffs since timestamp
  rpc GetDiffsSince(SinceQuery) returns (DiffResult);

  // Execute custom SQL query
  rpc ExecuteQuery(SQLQuery) returns (QueryResult);
}
```

---

## Phase 1: Go File Watcher Service

### Duration: 3-4 weeks

### Objectives
- Replace Python `watchdog` library with Go `fsnotify`
- Implement high-performance event debouncing using channels
- Port `.obbywatch` and `.obbyignore` pattern matching
- Integrate with Python FastAPI backend via gRPC

### Week 1: Foundation & Setup

#### Tasks
1. **Project Initialization**
   ```bash
   mkdir -p go-services/file-watcher
   cd go-services/file-watcher
   go mod init github.com/yourusername/obby-file-watcher
   ```

2. **Dependency Setup**
   ```bash
   go get github.com/fsnotify/fsnotify
   go get google.golang.org/grpc
   go get google.golang.org/protobuf
   go get github.com/gobwas/glob
   ```

3. **Protocol Buffer Definitions**
   - Create `proto/file_watcher.proto`
   - Generate Go code: `protoc --go_out=. --go-grpc_out=. proto/file_watcher.proto`

4. **Directory Structure**
   ```
   go-services/file-watcher/
   ├── proto/
   │   ├── file_watcher.proto
   │   └── generated/
   ├── internal/
   │   ├── watcher/
   │   │   ├── watcher.go          # Main fsnotify wrapper
   │   │   ├── debouncer.go        # Channel-based debouncing
   │   │   └── coordinator.go      # Event coordination
   │   ├── patterns/
   │   │   ├── ignore_handler.go   # .obbyignore matching
   │   │   ├── watch_handler.go    # .obbywatch parsing
   │   │   └── matcher.go          # Pattern matching logic
   │   └── server/
   │       └── grpc_server.go      # gRPC service implementation
   ├── cmd/
   │   └── server/
   │       └── main.go             # Entry point
   ├── config/
   │   └── config.go               # Configuration management
   ├── go.mod
   └── go.sum
   ```

#### Deliverables
- [ ] Project structure created
- [ ] Protocol buffers defined and generated
- [ ] Dependencies installed
- [ ] Basic gRPC server skeleton

### Week 2: Core Watcher Implementation

#### Tasks
1. **Implement fsnotify Wrapper** (`internal/watcher/watcher.go`)
   ```go
   package watcher

   import (
       "context"
       "log"
       "sync"
       "time"

       "github.com/fsnotify/fsnotify"
   )

   type FileWatcher struct {
       watcher   *fsnotify.Watcher
       debouncer *Debouncer
       patterns  *patterns.Matcher
       events    chan FileEvent
       errors    chan error
       mu        sync.RWMutex
       watching  map[string]bool
   }

   func NewFileWatcher(debounceMs int, patterns *patterns.Matcher) (*FileWatcher, error) {
       w, err := fsnotify.NewWatcher()
       if err != nil {
           return nil, err
       }

       return &FileWatcher{
           watcher:   w,
           debouncer: NewDebouncer(time.Duration(debounceMs) * time.Millisecond),
           patterns:  patterns,
           events:    make(chan FileEvent, 1000),
           errors:    make(chan error, 10),
           watching:  make(map[string]bool),
       }, nil
   }

   func (fw *FileWatcher) Start(ctx context.Context) error {
       go fw.processEvents(ctx)
       return nil
   }

   func (fw *FileWatcher) processEvents(ctx context.Context) {
       for {
           select {
           case event := <-fw.watcher.Events:
               if fw.shouldProcess(event.Name) {
                   fw.debouncer.Process(event.Name, func() {
                       fw.events <- fw.convertEvent(event)
                   })
               }
           case err := <-fw.watcher.Errors:
               log.Printf("watcher error: %v", err)
               fw.errors <- err
           case <-ctx.Done():
               fw.watcher.Close()
               close(fw.events)
               close(fw.errors)
               return
           }
       }
   }

   func (fw *FileWatcher) shouldProcess(path string) bool {
       // Check against .obbyignore patterns
       if fw.patterns.IsIgnored(path) {
           return false
       }
       // Check against .obbywatch patterns
       if !fw.patterns.IsWatched(path) {
           return false
       }
       return true
   }
   ```

2. **Implement Channel-Based Debouncer** (`internal/watcher/debouncer.go`)
   ```go
   package watcher

   import (
       "sync"
       "time"
   )

   type Debouncer struct {
       delay   time.Duration
       timers  map[string]*time.Timer
       mu      sync.Mutex
   }

   func NewDebouncer(delay time.Duration) *Debouncer {
       return &Debouncer{
           delay:  delay,
           timers: make(map[string]*time.Timer),
       }
   }

   func (d *Debouncer) Process(key string, fn func()) {
       d.mu.Lock()
       defer d.mu.Unlock()

       // Cancel existing timer
       if timer, exists := d.timers[key]; exists {
           timer.Stop()
       }

       // Create new timer
       d.timers[key] = time.AfterFunc(d.delay, func() {
           fn()
           d.mu.Lock()
           delete(d.timers, key)
           d.mu.Unlock()
       })
   }
   ```

3. **Pattern Matching Implementation** (`internal/patterns/`)
   - Port Python's `ignore_handler.py` logic
   - Port Python's `watch_handler.py` logic
   - Use `github.com/gobwas/glob` for pattern matching

#### Deliverables
- [ ] fsnotify wrapper with event processing
- [ ] Channel-based debouncing implementation
- [ ] Pattern matching (ignore/watch) ported
- [ ] Unit tests for core watcher logic

### Week 3: gRPC Integration & Pattern Handling

#### Tasks
1. **gRPC Server Implementation** (`internal/server/grpc_server.go`)
   ```go
   package server

   import (
       "context"
       "log"

       pb "github.com/yourusername/obby-file-watcher/proto/generated"
       "github.com/yourusername/obby-file-watcher/internal/watcher"
   )

   type FileWatcherServer struct {
       pb.UnimplementedFileWatcherServer
       watcher *watcher.FileWatcher
   }

   func (s *FileWatcherServer) StartWatching(ctx context.Context, req *pb.WatchRequest) (*pb.WatchResponse, error) {
       log.Printf("Starting watch on %d paths", len(req.WatchPaths))

       for _, path := range req.WatchPaths {
           if err := s.watcher.AddPath(path); err != nil {
               return &pb.WatchResponse{Success: false, Error: err.Error()}, nil
           }
       }

       return &pb.WatchResponse{Success: true}, nil
   }

   func (s *FileWatcherServer) StreamEvents(req *pb.EventRequest, stream pb.FileWatcher_StreamEventsServer) error {
       eventChan := s.watcher.Events()

       for {
           select {
           case event := <-eventChan:
               pbEvent := &pb.FileEvent{
                   Path:      event.Path,
                   EventType: event.Type,
                   Timestamp: event.Timestamp.Unix(),
               }
               if err := stream.Send(pbEvent); err != nil {
                   return err
               }
           case <-stream.Context().Done():
               return stream.Context().Err()
           }
       }
   }
   ```

2. **Python Client Implementation** (`backend/clients/file_watcher_client.py`)
   ```python
   import grpc
   from generated import file_watcher_pb2, file_watcher_pb2_grpc
   from typing import Iterator, Callable
   import logging

   logger = logging.getLogger(__name__)

   class FileWatcherClient:
       def __init__(self, host: str = "localhost", port: int = 50051):
           self.channel = grpc.insecure_channel(f"{host}:{port}")
           self.stub = file_watcher_pb2_grpc.FileWatcherStub(self.channel)

       def start_watching(self, watch_paths: list[str], ignore_patterns: list[str], debounce_ms: int = 500) -> bool:
           request = file_watcher_pb2.WatchRequest(
               watch_paths=watch_paths,
               ignore_patterns=ignore_patterns,
               debounce_ms=debounce_ms
           )

           try:
               response = self.stub.StartWatching(request)
               return response.success
           except grpc.RpcError as e:
               logger.error(f"gRPC error: {e}")
               return False

       def stream_events(self, callback: Callable) -> None:
           request = file_watcher_pb2.EventRequest()

           try:
               for event in self.stub.StreamEvents(request):
                   callback(event)
           except grpc.RpcError as e:
               logger.error(f"Stream error: {e}")
   ```

3. **WSL Detection & Polling Fallback**
   ```go
   func detectWSL() bool {
       // Check for WSL indicators
       if _, err := os.Stat("/proc/version"); err == nil {
           data, _ := os.ReadFile("/proc/version")
           return strings.Contains(strings.ToLower(string(data)), "microsoft")
       }
       return false
   }

   func (fw *FileWatcher) initWatcher() error {
       if detectWSL() && isDrvFsPath(fw.rootPath) {
           log.Println("WSL+DrvFS detected, using polling observer")
           return fw.initPollingWatcher()
       }
       return fw.initFsnotifyWatcher()
   }
   ```

#### Deliverables
- [ ] gRPC server fully functional
- [ ] Python client library
- [ ] WSL+DrvFS detection and polling fallback
- [ ] Integration tests (Go service + Python client)

### Week 4: Testing, Optimization & Integration

#### Tasks
1. **Performance Testing**
   - Benchmark event throughput (target: 10,000+ events/sec)
   - Measure debouncing accuracy
   - Memory profiling
   - Latency measurements

2. **Integration with FastAPI Backend**
   - Modify `backend.py` to start Go service on startup
   - Update `core/monitor.py` to use gRPC client instead of direct watchdog
   - Maintain backward compatibility with feature flag

3. **Feature Flag Implementation** (`config/settings.py`)
   ```python
   # Feature flags for gradual rollout
   USE_GO_FILE_WATCHER = os.getenv("USE_GO_FILE_WATCHER", "false").lower() == "true"
   GO_FILE_WATCHER_HOST = os.getenv("GO_FILE_WATCHER_HOST", "localhost")
   GO_FILE_WATCHER_PORT = int(os.getenv("GO_FILE_WATCHER_PORT", "50051"))
   ```

4. **Deployment Configuration**
   - Systemd service file for Go watcher
   - Docker container (optional)
   - Health check endpoints

#### Deliverables
- [ ] Performance benchmarks documented
- [ ] FastAPI integration complete
- [ ] Feature flag system operational
- [ ] Deployment documentation

### Success Criteria
- [ ] 10,000+ events/sec throughput achieved
- [ ] <1ms event processing latency
- [ ] <5ms debouncing latency (500ms window)
- [ ] Zero data loss in event processing
- [ ] Successful integration with Python backend
- [ ] All existing tests pass with Go watcher enabled

---

## Phase 2: Go Content Tracker Service

### Duration: 2-3 weeks

### Objectives
- Replace Python file reading and hashing with Go implementation
- Implement concurrent diff generation
- Optimize database write operations
- Maintain compatibility with existing `FileContentTracker` interface

### Week 1: Content Hashing & File Operations

#### Tasks
1. **Project Setup**
   ```bash
   mkdir -p go-services/content-tracker
   cd go-services/content-tracker
   go mod init github.com/yourusername/obby-content-tracker
   ```

2. **Protocol Buffer Definition** (`proto/content_tracker.proto`)
   - Define service interface (see Architecture section above)
   - Generate Go code

3. **Core Content Tracker Implementation** (`internal/tracker/tracker.go`)
   ```go
   package tracker

   import (
       "crypto/sha256"
       "encoding/hex"
       "io"
       "os"
       "sync"
       "bytes"
   )

   var hashPool = sync.Pool{
       New: func() interface{} {
           return sha256.New()
       },
   }

   type ContentTracker struct {
       db          *database.DB
       workerPool  *WorkerPool
       diffChan    chan DiffTask
       ignorePath  string
       watchPath   string
   }

   func (ct *ContentTracker) CalculateHash(filePath string) (string, error) {
       // Open file with buffered reading
       f, err := os.Open(filePath)
       if err != nil {
           return "", err
       }
       defer f.Close()

       // Get hash instance from pool
       h := hashPool.Get().(hash.Hash)
       defer func() {
           h.Reset()
           hashPool.Put(h)
       }()

       // Read and normalize line endings on the fly
       buf := make([]byte, 32*1024) // 32KB buffer
       for {
           n, err := f.Read(buf)
           if n > 0 {
               // Normalize line endings: \r\n and \r → \n
               normalized := normalizeLineEndings(buf[:n])
               h.Write(normalized)
           }
           if err == io.EOF {
               break
           }
           if err != nil {
               return "", err
           }
       }

       return hex.EncodeToString(h.Sum(nil)), nil
   }

   func normalizeLineEndings(data []byte) []byte {
       // Replace \r\n with \n
       data = bytes.ReplaceAll(data, []byte("\r\n"), []byte("\n"))
       // Replace \r with \n
       data = bytes.ReplaceAll(data, []byte("\r"), []byte("\n"))
       return data
   }
   ```

4. **Worker Pool for Concurrent Processing**
   ```go
   type WorkerPool struct {
       workers   int
       taskQueue chan Task
       wg        sync.WaitGroup
   }

   func NewWorkerPool(workers int) *WorkerPool {
       return &WorkerPool{
           workers:   workers,
           taskQueue: make(chan Task, workers*2),
       }
   }

   func (wp *WorkerPool) Start(ctx context.Context) {
       for i := 0; i < wp.workers; i++ {
           wp.wg.Add(1)
           go wp.worker(ctx)
       }
   }

   func (wp *WorkerPool) worker(ctx context.Context) {
       defer wp.wg.Done()
       for {
           select {
           case task := <-wp.taskQueue:
               task.Execute()
           case <-ctx.Done():
               return
           }
       }
   }
   ```

#### Deliverables
- [ ] Content hashing with pooling
- [ ] Streaming file I/O
- [ ] Worker pool implementation
- [ ] Unit tests for hashing (verify matches Python output)

### Week 2: Diff Generation & Database Integration

#### Tasks
1. **Diff Generation** (`internal/diff/generator.go`)
   ```go
   package diff

   import (
       "github.com/sergi/go-diff/diffmatchpatch"
   )

   type DiffGenerator struct {
       dmp *diffmatchpatch.DiffMatchPatch
   }

   func NewDiffGenerator() *DiffGenerator {
       dmp := diffmatchpatch.New()
       return &DiffGenerator{dmp: dmp}
   }

   func (dg *DiffGenerator) GenerateUnifiedDiff(oldContent, newContent, oldPath, newPath string) (string, error) {
       diffs := dg.dmp.DiffMain(oldContent, newContent, false)

       // Convert to unified diff format
       patch := dg.dmp.PatchMake(oldContent, diffs)
       return dg.dmp.PatchToText(patch), nil
   }
   ```

2. **Database Layer** (`internal/database/db.go`)
   ```go
   package database

   import (
       "database/sql"
       _ "github.com/mattn/go-sqlite3"
       "time"
   )

   type DB struct {
       conn *sql.DB
   }

   func NewDB(path string) (*DB, error) {
       conn, err := sql.Open("sqlite3", path+"?_journal_mode=WAL&_foreign_keys=ON&_busy_timeout=5000")
       if err != nil {
           return nil, err
       }

       // Configure connection pool
       conn.SetMaxOpenConns(25)
       conn.SetMaxIdleConns(5)
       conn.SetConnMaxLifetime(time.Hour)

       return &DB{conn: conn}, nil
   }

   func (db *DB) InsertFileVersion(ctx context.Context, path, hash, content string, size int64) (int64, error) {
       stmt, err := db.conn.PrepareContext(ctx, `
           INSERT INTO file_versions (file_path, content_hash, content, size, timestamp)
           VALUES (?, ?, ?, ?, ?)
       `)
       if err != nil {
           return 0, err
       }
       defer stmt.Close()

       result, err := stmt.ExecContext(ctx, path, hash, content, size, time.Now().Unix())
       if err != nil {
           return 0, err
       }

       return result.LastInsertId()
   }
   ```

3. **gRPC Service Implementation**
   ```go
   func (s *ContentTrackerServer) TrackChange(ctx context.Context, req *pb.TrackRequest) (*pb.TrackResponse, error) {
       // Read file
       content, err := s.tracker.ReadFile(req.FilePath)
       if err != nil {
           return &pb.TrackResponse{Success: false, Error: err.Error()}, nil
       }

       // Calculate hash
       hash, err := s.tracker.CalculateHash(req.FilePath)
       if err != nil {
           return &pb.TrackResponse{Success: false, Error: err.Error()}, nil
       }

       // Check if content changed
       prevHash, _ := s.tracker.GetPreviousHash(req.FilePath)
       if hash == prevHash {
           return &pb.TrackResponse{Success: true, ContentHash: hash}, nil
       }

       // Store version
       versionID, err := s.tracker.StoreVersion(ctx, req.FilePath, hash, content)
       if err != nil {
           return &pb.TrackResponse{Success: false, Error: err.Error()}, nil
       }

       // Generate diff asynchronously
       if prevHash != "" {
           go s.tracker.GenerateDiffAsync(req.FilePath, prevHash, hash)
       }

       return &pb.TrackResponse{
           Success:     true,
           ContentHash: hash,
           FileSize:    int64(len(content)),
           VersionId:   versionID,
       }, nil
   }
   ```

#### Deliverables
- [ ] Diff generation matching Python format
- [ ] SQLite integration with connection pooling
- [ ] gRPC service implementation
- [ ] Integration tests

### Week 3: Python Integration & Performance Testing

#### Tasks
1. **Python Client** (`backend/clients/content_tracker_client.py`)
   ```python
   class ContentTrackerClient:
       def __init__(self, host: str = "localhost", port: int = 50052):
           self.channel = grpc.insecure_channel(f"{host}:{port}")
           self.stub = content_tracker_pb2_grpc.ContentTrackerStub(self.channel)

       def track_change(self, file_path: str, change_type: str, project_root: str) -> dict:
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
               logger.error(f"gRPC error: {e}")
               return {"success": False, "error": str(e)}
   ```

2. **Integration with FileContentTracker**
   - Add feature flag: `USE_GO_CONTENT_TRACKER`
   - Modify `core/file_tracker.py` to conditionally use gRPC client
   - Maintain backward compatibility

3. **Performance Benchmarks**
   - File reading: Target 500 MB/s throughput
   - Hashing: Target 10x improvement over Python
   - Diff generation: Target 5x improvement
   - Concurrent operations: Test with 100+ files

#### Deliverables
- [ ] Python client integration
- [ ] Feature flag system
- [ ] Performance benchmarks documented
- [ ] All tests passing

### Success Criteria
- [ ] 10x faster content hashing (50 MB/s → 500 MB/s)
- [ ] 5x faster diff generation
- [ ] Concurrent processing of 100+ files
- [ ] Database writes complete in <10ms
- [ ] Zero data loss or corruption
- [ ] Diff format matches Python exactly

---

## Phase 3: Go Database Layer (Optional)

### Duration: 2-3 weeks

### Objectives
- Centralize database access in Go service
- Optimize hot-path queries
- Implement advanced connection pooling
- Provide high-performance query API to Python

### Week 1: Query Service Foundation

#### Tasks
1. **Protocol Buffer Definition**
   ```protobuf
   service QueryService {
       // File queries
       rpc GetRecentDiffs(DiffQuery) returns (stream DiffRecord);
       rpc GetDiffsSince(SinceQuery) returns (stream DiffRecord);
       rpc GetFileVersions(FileQuery) returns (stream FileVersion);

       // Semantic queries
       rpc SearchContent(SearchQuery) returns (stream SearchResult);
       rpc GetTopicFiles(TopicQuery) returns (stream FileRecord);

       // Analytics
       rpc GetTimeAnalysis(TimeQuery) returns (TimeAnalysisResult);
       rpc GetActivityStats(StatsQuery) returns (ActivityStats);
   }
   ```

2. **Query Implementation** (`internal/queries/file_queries.go`)
   ```go
   type FileQueries struct {
       db *sql.DB
       preparedStmts map[string]*sql.Stmt
       mu sync.RWMutex
   }

   func (fq *FileQueries) GetRecentDiffs(ctx context.Context, limit int) ([]*DiffRecord, error) {
       stmt, err := fq.getOrPrepare("recent_diffs", `
           SELECT
               d.id, d.file_path, d.change_type, d.diff_content,
               d.lines_added, d.lines_removed, d.timestamp,
               v.content_hash, v.size
           FROM content_diffs d
           JOIN file_versions v ON d.new_version_id = v.id
           ORDER BY d.timestamp DESC
           LIMIT ?
       `)
       if err != nil {
           return nil, err
       }

       rows, err := stmt.QueryContext(ctx, limit)
       if err != nil {
           return nil, err
       }
       defer rows.Close()

       var results []*DiffRecord
       for rows.Next() {
           var dr DiffRecord
           err := rows.Scan(
               &dr.ID, &dr.FilePath, &dr.ChangeType, &dr.DiffContent,
               &dr.LinesAdded, &dr.LinesRemoved, &dr.Timestamp,
               &dr.ContentHash, &dr.Size,
           )
           if err != nil {
               return nil, err
           }
           results = append(results, &dr)
       }

       return results, nil
   }

   func (fq *FileQueries) getOrPrepare(name, query string) (*sql.Stmt, error) {
       fq.mu.RLock()
       stmt, exists := fq.preparedStmts[name]
       fq.mu.RUnlock()

       if exists {
           return stmt, nil
       }

       fq.mu.Lock()
       defer fq.mu.Unlock()

       // Double-check after acquiring write lock
       if stmt, exists := fq.preparedStmts[name]; exists {
           return stmt, nil
       }

       stmt, err := fq.db.Prepare(query)
       if err != nil {
           return nil, err
       }

       fq.preparedStmts[name] = stmt
       return stmt, nil
   }
   ```

3. **Connection Pool Optimization**
   ```go
   func (qs *QueryService) initDB(path string) error {
       db, err := sql.Open("sqlite3", path+"?_journal_mode=WAL&_foreign_keys=ON&_busy_timeout=5000")
       if err != nil {
           return err
       }

       // Aggressive connection pooling for read-heavy workload
       db.SetMaxOpenConns(50)
       db.SetMaxIdleConns(10)
       db.SetConnMaxLifetime(2 * time.Hour)
       db.SetConnMaxIdleTime(30 * time.Minute)

       // Pre-warm connection pool
       for i := 0; i < 10; i++ {
           conn, err := db.Conn(context.Background())
           if err != nil {
               return err
           }
           conn.Close()
       }

       qs.db = db
       return nil
   }
   ```

#### Deliverables
- [ ] Core query service structure
- [ ] Prepared statement caching
- [ ] Connection pool optimization
- [ ] Basic gRPC service

### Week 2: Query Optimization & FTS5

#### Tasks
1. **Full-Text Search Integration**
   ```go
   func (fq *FileQueries) SearchContent(ctx context.Context, query string, limit int) ([]*SearchResult, error) {
       stmt, err := fq.getOrPrepare("fts_search", `
           SELECT
               file_path, content, highlight(file_content_fts, 2, '<mark>', '</mark>') as highlighted,
               rank
           FROM file_content_fts
           WHERE file_content_fts MATCH ?
           ORDER BY rank
           LIMIT ?
       `)
       if err != nil {
           return nil, err
       }

       rows, err := stmt.QueryContext(ctx, query, limit)
       if err != nil {
           return nil, err
       }
       defer rows.Close()

       var results []*SearchResult
       for rows.Next() {
           var sr SearchResult
           err := rows.Scan(&sr.FilePath, &sr.Content, &sr.Highlighted, &sr.Rank)
           if err != nil {
               return nil, err
           }
           results = append(results, &sr)
       }

       return results, nil
   }
   ```

2. **Complex Aggregation Queries**
   - Port `get_comprehensive_time_analysis` from Python
   - Optimize with indexes and query planning
   - Use CTEs for complex joins

3. **Query Result Streaming**
   ```go
   func (s *QueryServer) GetRecentDiffs(req *pb.DiffQuery, stream pb.QueryService_GetRecentDiffsServer) error {
       diffs, err := s.queries.GetRecentDiffs(stream.Context(), int(req.Limit))
       if err != nil {
           return err
       }

       for _, diff := range diffs {
           pbDiff := &pb.DiffRecord{
               Id:          diff.ID,
               FilePath:    diff.FilePath,
               ChangeType:  diff.ChangeType,
               DiffContent: diff.DiffContent,
               LinesAdded:  diff.LinesAdded,
               LinesRemoved: diff.LinesRemoved,
               Timestamp:   diff.Timestamp,
           }
           if err := stream.Send(pbDiff); err != nil {
               return err
           }
       }

       return nil
   }
   ```

#### Deliverables
- [ ] FTS5 search implementation
- [ ] Complex query optimization
- [ ] Streaming query results
- [ ] Performance benchmarks

### Week 3: Python Integration & Migration

#### Tasks
1. **Python Client Library**
   ```python
   class QueryClient:
       def __init__(self, host: str = "localhost", port: int = 50053):
           self.channel = grpc.insecure_channel(f"{host}:{port}")
           self.stub = query_pb2_grpc.QueryServiceStub(self.channel)

       def get_recent_diffs(self, limit: int = 50) -> list[dict]:
           request = query_pb2.DiffQuery(limit=limit)
           results = []

           for diff in self.stub.GetRecentDiffs(request):
               results.append({
                   "id": diff.id,
                   "file_path": diff.file_path,
                   "change_type": diff.change_type,
                   "diff_content": diff.diff_content,
                   "lines_added": diff.lines_added,
                   "lines_removed": diff.lines_removed,
                   "timestamp": diff.timestamp
               })

           return results
   ```

2. **Gradual Migration Strategy**
   - Keep Python `FileQueries` class as adapter
   - Route calls to Go service when enabled
   - Fall back to Python for unsupported queries
   - Feature flag per query type

3. **Performance Comparison**
   - Benchmark Python vs Go for all query types
   - Document performance gains
   - Identify bottlenecks

#### Deliverables
- [ ] Python client complete
- [ ] Migration adapter layer
- [ ] Performance comparison report
- [ ] Documentation

### Success Criteria
- [ ] 5x faster query execution
- [ ] 100+ queries/sec throughput
- [ ] <10ms p99 latency for hot queries
- [ ] Zero data inconsistencies
- [ ] All FileQueries methods supported

---

## Phase 4: Go SSE Hub (Optional)

### Duration: 2 weeks

### Objectives
- Replace Python SSE client management with Go
- Implement high-performance broadcasting
- Support 10,000+ concurrent connections
- Maintain API compatibility

### Week 1: SSE Hub Implementation

#### Tasks
1. **Hub Architecture** (`internal/hub/hub.go`)
   ```go
   type SSEHub struct {
       clients    map[string]*Client
       broadcast  chan Message
       register   chan *Client
       unregister chan *Client
       mu         sync.RWMutex
   }

   type Client struct {
       id      string
       hub     *SSEHub
       send    chan Message
       topics  map[string]bool
       mu      sync.RWMutex
   }

   func (h *SSEHub) Run(ctx context.Context) {
       for {
           select {
           case client := <-h.register:
               h.mu.Lock()
               h.clients[client.id] = client
               h.mu.Unlock()
               log.Printf("Client registered: %s (total: %d)", client.id, len(h.clients))

           case client := <-h.unregister:
               h.mu.Lock()
               if _, exists := h.clients[client.id]; exists {
                   delete(h.clients, client.id)
                   close(client.send)
               }
               h.mu.Unlock()
               log.Printf("Client unregistered: %s", client.id)

           case message := <-h.broadcast:
               h.mu.RLock()
               for _, client := range h.clients {
                   if client.isSubscribed(message.Topic) {
                       select {
                       case client.send <- message:
                       default:
                           // Client buffer full, disconnect slow client
                           go h.unregisterClient(client)
                       }
                   }
               }
               h.mu.RUnlock()

           case <-ctx.Done():
               h.shutdown()
               return
           }
       }
   }
   ```

2. **HTTP Handler** (`internal/http/sse_handler.go`)
   ```go
   func (h *SSEHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
       // Set SSE headers
       w.Header().Set("Content-Type", "text/event-stream")
       w.Header().Set("Cache-Control", "no-cache")
       w.Header().Set("Connection", "keep-alive")
       w.Header().Set("Access-Control-Allow-Origin", "*")

       flusher, ok := w.(http.Flusher)
       if !ok {
           http.Error(w, "SSE not supported", http.StatusInternalServerError)
           return
       }

       client := h.hub.NewClient(r.Context())
       h.hub.Register(client)
       defer h.hub.Unregister(client)

       // Subscribe to topics from query params
       topics := r.URL.Query()["topic"]
       for _, topic := range topics {
           client.Subscribe(topic)
       }

       // Send events to client
       for {
           select {
           case msg := <-client.send:
               fmt.Fprintf(w, "event: %s\n", msg.Event)
               fmt.Fprintf(w, "data: %s\n\n", msg.Data)
               flusher.Flush()

           case <-r.Context().Done():
               return
           }
       }
   }
   ```

3. **gRPC Service for Publishing**
   ```go
   service SSEService {
       rpc Publish(PublishRequest) returns (PublishResponse);
       rpc RegisterClient(ClientRequest) returns (stream SSEMessage);
   }

   func (s *SSEServer) Publish(ctx context.Context, req *pb.PublishRequest) (*pb.PublishResponse, error) {
       msg := hub.Message{
           Event: req.Event,
           Topic: req.Topic,
           Data:  req.Data,
       }

       s.hub.Broadcast(msg)

       return &pb.PublishResponse{
           Success: true,
           Clients: int32(s.hub.ClientCount()),
       }, nil
   }
   ```

#### Deliverables
- [ ] SSE hub with broadcasting
- [ ] HTTP handler for SSE connections
- [ ] gRPC service for publishing
- [ ] Topic-based subscriptions

### Week 2: Integration & Load Testing

#### Tasks
1. **Python Integration**
   ```python
   class SSEPublisher:
       def __init__(self, host: str = "localhost", port: int = 50054):
           self.channel = grpc.insecure_channel(f"{host}:{port}")
           self.stub = sse_pb2_grpc.SSEServiceStub(self.channel)

       def publish(self, event: str, topic: str, data: dict):
           request = sse_pb2.PublishRequest(
               event=event,
               topic=topic,
               data=json.dumps(data)
           )

           response = self.stub.Publish(request)
           return response.success
   ```

2. **Frontend Integration**
   - Update SSE endpoints to point to Go service
   - Maintain event format compatibility
   - Test all event types (session-summary, summary-notes, etc.)

3. **Load Testing**
   ```bash
   # Test with 10,000 concurrent connections
   go run loadtest/sse_loadtest.go --connections 10000 --duration 5m
   ```

4. **Monitoring & Metrics**
   ```go
   type Metrics struct {
       TotalClients     int64
       MessagesPerSec   int64
       BroadcastLatency time.Duration
       DroppedClients   int64
   }

   func (h *SSEHub) RecordMetrics() {
       ticker := time.NewTicker(10 * time.Second)
       for range ticker.C {
           metrics := h.GetMetrics()
           log.Printf("SSE Metrics: clients=%d, msg/s=%d, latency=%v",
               metrics.TotalClients,
               metrics.MessagesPerSec,
               metrics.BroadcastLatency)
       }
   }
   ```

#### Deliverables
- [ ] Python publisher client
- [ ] Frontend integration complete
- [ ] Load test results (10,000+ connections)
- [ ] Monitoring and metrics

### Success Criteria
- [ ] 10,000+ concurrent connections supported
- [ ] <5ms broadcast latency
- [ ] <1% client disconnections under load
- [ ] Zero message loss
- [ ] Full backward compatibility with Python SSE

---

## Testing Strategy

### Unit Testing

#### Go Services
Each Go service requires comprehensive unit tests:

```go
// file_watcher_test.go
func TestDebouncer(t *testing.T) {
    d := NewDebouncer(100 * time.Millisecond)

    var callCount int32
    d.Process("test", func() {
        atomic.AddInt32(&callCount, 1)
    })

    // Rapid fire - should debounce
    for i := 0; i < 10; i++ {
        d.Process("test", func() {
            atomic.AddInt32(&callCount, 1)
        })
        time.Sleep(10 * time.Millisecond)
    }

    time.Sleep(200 * time.Millisecond)

    if callCount != 1 {
        t.Errorf("Expected 1 call, got %d", callCount)
    }
}

func BenchmarkContentHash(b *testing.B) {
    content := strings.Repeat("test content\n", 1000)
    ct := NewContentTracker(nil)

    b.ResetTimer()
    for i := 0; i < b.N; i++ {
        _, _ = ct.HashContent([]byte(content))
    }
}
```

**Coverage Requirements:**
- Minimum 80% code coverage
- All edge cases tested
- Performance benchmarks for critical paths

#### Python Integration
```python
# test_go_integration.py
import pytest
from backend.clients.file_watcher_client import FileWatcherClient

@pytest.fixture
def go_watcher_client():
    client = FileWatcherClient()
    yield client
    client.close()

def test_file_watcher_basic(go_watcher_client, tmp_path):
    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("initial content")

    # Start watching
    success = go_watcher_client.start_watching(
        watch_paths=[str(tmp_path)],
        ignore_patterns=[]
    )
    assert success

    # Modify file
    test_file.write_text("modified content")

    # Verify event received
    event = go_watcher_client.get_next_event(timeout=2.0)
    assert event.path == str(test_file)
    assert event.event_type == "modified"
```

### Integration Testing

#### End-to-End Flow Tests
```python
# test_e2e_go_services.py
def test_full_file_change_flow(tmp_path):
    """Test complete flow: file change → watcher → tracker → database"""

    # 1. Setup services
    watcher = FileWatcherClient()
    tracker = ContentTrackerClient()
    db = DatabaseConnection()

    # 2. Start monitoring
    watcher.start_watching([str(tmp_path)])

    # 3. Create file
    test_file = tmp_path / "example.py"
    test_file.write_text("print('hello')")

    # 4. Wait for watcher event
    event = watcher.get_next_event(timeout=2.0)
    assert event.path == str(test_file)

    # 5. Trigger tracking
    result = tracker.track_change(
        file_path=str(test_file),
        change_type="created",
        project_root=str(tmp_path)
    )
    assert result["success"]

    # 6. Verify database
    version = db.get_latest_version(str(test_file))
    assert version is not None
    assert version.content_hash == result["content_hash"]
```

#### Performance Tests
```python
def test_high_volume_events():
    """Test system under high event volume"""

    watcher = FileWatcherClient()
    tracker = ContentTrackerClient()

    # Create 1000 files rapidly
    start = time.time()
    for i in range(1000):
        path = f"/tmp/test_{i}.txt"
        with open(path, 'w') as f:
            f.write(f"content {i}")

    # Verify all events processed
    events = []
    timeout = time.time() + 10
    while len(events) < 1000 and time.time() < timeout:
        event = watcher.get_next_event(timeout=0.1)
        if event:
            events.append(event)

    duration = time.time() - start
    assert len(events) == 1000
    assert duration < 5.0  # Should process in <5 seconds
    print(f"Processed {len(events)} events in {duration:.2f}s ({len(events)/duration:.0f} events/s)")
```

### Load Testing

#### SSE Connection Load Test
```go
// loadtest/sse_loadtest.go
func main() {
    connections := flag.Int("connections", 1000, "Number of concurrent connections")
    duration := flag.Duration("duration", 1*time.Minute, "Test duration")
    flag.Parse()

    var wg sync.WaitGroup
    start := time.Now()

    for i := 0; i < *connections; i++ {
        wg.Add(1)
        go func(id int) {
            defer wg.Done()

            client := &http.Client{Timeout: 0}
            req, _ := http.NewRequest("GET", "http://localhost:8001/api/sse/events", nil)
            resp, err := client.Do(req)
            if err != nil {
                log.Printf("Connection %d failed: %v", id, err)
                return
            }
            defer resp.Body.Close()

            scanner := bufio.NewScanner(resp.Body)
            timeout := time.After(*duration)

            for {
                select {
                case <-timeout:
                    return
                default:
                    if !scanner.Scan() {
                        return
                    }
                }
            }
        }(i)

        time.Sleep(time.Millisecond) // Stagger connections
    }

    wg.Wait()
    fmt.Printf("Load test completed: %d connections for %v\n", *connections, time.Since(start))
}
```

#### File Processing Benchmark
```bash
#!/bin/bash
# benchmark_file_processing.sh

# Generate test files
mkdir -p /tmp/obby-test
for i in {1..1000}; do
  dd if=/dev/urandom of=/tmp/obby-test/file_$i.bin bs=1M count=1 2>/dev/null
done

# Benchmark Python implementation
echo "Python implementation:"
time python -c "
from core.file_tracker import FileContentTracker
tracker = FileContentTracker('/tmp/test.db', '.', '.')
for i in range(1, 1001):
    tracker.track_file_change(f'/tmp/obby-test/file_{i}.bin', 'created')
"

# Benchmark Go implementation
echo "Go implementation:"
time go run cmd/benchmark/main.go --files /tmp/obby-test/*.bin

# Cleanup
rm -rf /tmp/obby-test
```

---

## Deployment & Rollout Plan

### Infrastructure Setup

#### Systemd Services
Create service files for each Go microservice:

```ini
# /etc/systemd/system/obby-file-watcher.service
[Unit]
Description=Obby File Watcher Service
After=network.target

[Service]
Type=simple
User=obby
WorkingDirectory=/opt/obby/go-services/file-watcher
ExecStart=/opt/obby/go-services/file-watcher/bin/file-watcher
Restart=on-failure
RestartSec=5s
Environment="WATCHER_PORT=50051"
Environment="LOG_LEVEL=info"

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/obby-content-tracker.service
[Unit]
Description=Obby Content Tracker Service
After=network.target obby-file-watcher.service

[Service]
Type=simple
User=obby
WorkingDirectory=/opt/obby/go-services/content-tracker
ExecStart=/opt/obby/go-services/content-tracker/bin/content-tracker
Restart=on-failure
RestartSec=5s
Environment="TRACKER_PORT=50052"
Environment="DB_PATH=/var/lib/obby/obby.db"

[Install]
WantedBy=multi-user.target
```

#### Docker Compose (Alternative)
```yaml
# docker-compose.yml
version: '3.8'

services:
  file-watcher:
    build:
      context: ./go-services/file-watcher
      dockerfile: Dockerfile
    ports:
      - "50051:50051"
    volumes:
      - ./watched-files:/watched-files:ro
    environment:
      - WATCHER_PORT=50051
      - LOG_LEVEL=info
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "grpc_health_probe", "-addr=:50051"]
      interval: 30s
      timeout: 10s
      retries: 3

  content-tracker:
    build:
      context: ./go-services/content-tracker
      dockerfile: Dockerfile
    ports:
      - "50052:50052"
    volumes:
      - ./watched-files:/watched-files:ro
      - obby-db:/data
    environment:
      - TRACKER_PORT=50052
      - DB_PATH=/data/obby.db
    depends_on:
      - file-watcher
    restart: unless-stopped

  backend:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8001:8001"
    volumes:
      - ./watched-files:/watched-files
      - obby-db:/data
    environment:
      - USE_GO_FILE_WATCHER=true
      - USE_GO_CONTENT_TRACKER=true
      - GO_FILE_WATCHER_HOST=file-watcher
      - GO_CONTENT_TRACKER_HOST=content-tracker
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      - file-watcher
      - content-tracker

volumes:
  obby-db:
```

### Gradual Rollout Strategy

#### Phase 1: Canary Deployment (Week 1)
1. **Deploy to Development**
   - Enable Go services in dev environment
   - Run alongside Python implementation
   - Monitor for errors and performance

2. **Feature Flags**
   ```python
   # config/settings.py

   # Rollout percentage (0-100)
   GO_WATCHER_ROLLOUT_PERCENTAGE = int(os.getenv("GO_WATCHER_ROLLOUT_PERCENTAGE", "0"))
   GO_TRACKER_ROLLOUT_PERCENTAGE = int(os.getenv("GO_TRACKER_ROLLOUT_PERCENTAGE", "0"))

   import random

   def should_use_go_watcher() -> bool:
       if GO_WATCHER_ROLLOUT_PERCENTAGE == 100:
           return True
       if GO_WATCHER_ROLLOUT_PERCENTAGE == 0:
           return False
       return random.randint(1, 100) <= GO_WATCHER_ROLLOUT_PERCENTAGE
   ```

3. **Monitoring Setup**
   - Prometheus metrics for Go services
   - Grafana dashboards
   - Error tracking with Sentry
   - Performance comparison logs

#### Phase 2: Beta Testing (Week 2-3)
1. **10% Rollout**
   - Set `GO_WATCHER_ROLLOUT_PERCENTAGE=10`
   - Monitor error rates, performance metrics
   - Collect user feedback

2. **50% Rollout**
   - Increase to 50% after 1 week of stable 10% rollout
   - Continue monitoring
   - Compare Python vs Go performance side-by-side

#### Phase 3: Full Rollout (Week 4)
1. **100% Go Services**
   - Set rollout percentage to 100%
   - Disable Python implementations
   - Monitor for regressions

2. **Deprecation Timeline**
   - Keep Python code for 2 weeks as rollback option
   - Document migration in changelog
   - Remove Python implementations after stable period

### Monitoring & Metrics

#### Key Metrics to Track
```go
// metrics/metrics.go
type ServiceMetrics struct {
    // File Watcher
    EventsProcessed     int64
    EventsDebounced     int64
    ProcessingLatency   time.Duration
    QueueDepth          int64

    // Content Tracker
    FilesHashed         int64
    DiffsGenerated      int64
    HashThroughput      float64  // MB/s
    DatabaseWrites      int64

    // Query Service
    QueriesExecuted     int64
    QueryLatencyP50     time.Duration
    QueryLatencyP99     time.Duration
    CacheHitRate        float64

    // SSE Hub
    ActiveClients       int64
    MessagesBroadcast   int64
    BroadcastLatency    time.Duration
    DroppedConnections  int64
}
```

#### Prometheus Integration
```go
import (
    "github.com/prometheus/client_golang/prometheus"
    "github.com/prometheus/client_golang/prometheus/promauto"
)

var (
    eventsProcessed = promauto.NewCounter(prometheus.CounterOpts{
        Name: "obby_watcher_events_processed_total",
        Help: "Total number of file events processed",
    })

    processingLatency = promauto.NewHistogram(prometheus.HistogramOpts{
        Name:    "obby_watcher_processing_latency_seconds",
        Help:    "Event processing latency",
        Buckets: prometheus.DefBuckets,
    })

    activeClients = promauto.NewGauge(prometheus.GaugeOpts{
        Name: "obby_sse_active_clients",
        Help: "Number of active SSE clients",
    })
)
```

#### Grafana Dashboard
```json
{
  "dashboard": {
    "title": "Obby Go Services",
    "panels": [
      {
        "title": "Event Processing Rate",
        "targets": [
          {
            "expr": "rate(obby_watcher_events_processed_total[1m])"
          }
        ]
      },
      {
        "title": "Processing Latency (p99)",
        "targets": [
          {
            "expr": "histogram_quantile(0.99, obby_watcher_processing_latency_seconds)"
          }
        ]
      },
      {
        "title": "Active SSE Clients",
        "targets": [
          {
            "expr": "obby_sse_active_clients"
          }
        ]
      }
    ]
  }
}
```

### Health Checks

#### gRPC Health Check Protocol
```go
import "google.golang.org/grpc/health/grpc_health_v1"

type HealthServer struct {
    grpc_health_v1.UnimplementedHealthServer
    service *FileWatcherService
}

func (h *HealthServer) Check(ctx context.Context, req *grpc_health_v1.HealthCheckRequest) (*grpc_health_v1.HealthCheckResponse, error) {
    // Check service health
    if h.service.IsHealthy() {
        return &grpc_health_v1.HealthCheckResponse{
            Status: grpc_health_v1.HealthCheckResponse_SERVING,
        }, nil
    }

    return &grpc_health_v1.HealthCheckResponse{
        Status: grpc_health_v1.HealthCheckResponse_NOT_SERVING,
    }, nil
}
```

#### HTTP Health Endpoint
```go
func (s *Server) healthHandler(w http.ResponseWriter, r *http.Request) {
    health := s.checkHealth()

    status := http.StatusOK
    if !health.Healthy {
        status = http.StatusServiceUnavailable
    }

    w.WriteHeader(status)
    json.NewEncoder(w).Encode(health)
}

type HealthStatus struct {
    Healthy   bool              `json:"healthy"`
    Services  map[string]bool   `json:"services"`
    Uptime    time.Duration     `json:"uptime"`
    Version   string            `json:"version"`
}
```

---

## Risk Management

### Identified Risks

#### 1. Data Loss or Corruption
**Risk**: Database writes from Go service fail or corrupt data

**Mitigation**:
- Comprehensive transaction handling with rollback
- Database integrity checks before/after migration
- Shadow mode: Write to both Python and Go, compare results
- Automated backup before each deployment
- Checksum validation for all stored content

**Rollback**:
```python
# Emergency rollback flag
EMERGENCY_ROLLBACK_TO_PYTHON = os.getenv("EMERGENCY_ROLLBACK", "false").lower() == "true"

if EMERGENCY_ROLLBACK_TO_PYTHON:
    logger.critical("EMERGENCY ROLLBACK ACTIVATED - Using Python implementations")
    USE_GO_FILE_WATCHER = False
    USE_GO_CONTENT_TRACKER = False
```

#### 2. Performance Regression
**Risk**: Go services perform worse than Python in production

**Mitigation**:
- Extensive benchmarking before rollout
- A/B testing with metrics collection
- Automated performance regression tests
- Gradual rollout with instant rollback capability

**Rollback**:
- Single environment variable flip: `USE_GO_SERVICES=false`
- No data migration required (shared database)
- <5 minute rollback time

#### 3. Integration Failures
**Risk**: gRPC communication failures, protocol mismatches

**Mitigation**:
- Comprehensive integration tests
- Contract testing with Protocol Buffers
- Graceful degradation (fallback to Python)
- Connection retry logic with exponential backoff
- Circuit breaker pattern for gRPC calls

**Example**:
```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
def call_go_service(client, method, *args):
    try:
        return getattr(client, method)(*args)
    except grpc.RpcError as e:
        logger.error(f"gRPC error: {e}, falling back to Python")
        raise  # Circuit breaker will open after threshold
```

#### 4. Memory Leaks
**Risk**: Go services leak memory over time

**Mitigation**:
- Continuous memory profiling in production
- Automated leak detection in CI/CD
- Connection pool limits and timeouts
- Regular service restarts (graceful)
- pprof integration for runtime analysis

```go
import _ "net/http/pprof"

func main() {
    // Enable profiling endpoint
    go func() {
        log.Println(http.ListenAndServe("localhost:6060", nil))
    }()

    // Main service...
}
```

#### 5. Deployment Complexity
**Risk**: Multiple services complicate deployment

**Mitigation**:
- Automated deployment scripts
- Health check dependencies in systemd/docker-compose
- Single deployment command for all services
- Automated rollback on health check failure

```bash
#!/bin/bash
# deploy.sh

set -e

# Deploy all services
systemctl start obby-file-watcher
systemctl start obby-content-tracker
systemctl start obby-backend

# Wait for health checks
sleep 5

# Verify all healthy
if ! curl -f http://localhost:50051/health; then
    echo "File watcher health check failed, rolling back"
    systemctl stop obby-file-watcher
    exit 1
fi

if ! curl -f http://localhost:50052/health; then
    echo "Content tracker health check failed, rolling back"
    systemctl stop obby-content-tracker obby-file-watcher
    exit 1
fi

echo "Deployment successful"
```

### Rollback Procedures

#### Immediate Rollback (Production Issues)
```bash
# 1. Disable Go services via environment variable
export USE_GO_FILE_WATCHER=false
export USE_GO_CONTENT_TRACKER=false
export USE_GO_QUERY_SERVICE=false
export USE_GO_SSE_HUB=false

# 2. Restart Python backend
systemctl restart obby-backend

# 3. Stop Go services
systemctl stop obby-file-watcher obby-content-tracker

# 4. Verify Python services operational
curl http://localhost:8001/api/health
```

#### Database Rollback
```bash
# Restore from pre-migration backup
sqlite3 /var/lib/obby/obby.db ".restore /var/lib/obby/backups/obby_pre_migration.db"

# Verify integrity
sqlite3 /var/lib/obby/obby.db "PRAGMA integrity_check;"
```

#### Partial Rollback (Single Service)
```python
# Rollback only file watcher, keep content tracker
USE_GO_FILE_WATCHER = False
USE_GO_CONTENT_TRACKER = True  # Still using Go
```

---

## Performance Benchmarks

### Baseline (Python Implementation)

#### File Watcher
- **Event throughput**: ~1,000 events/sec (polling mode)
- **Latency**: ~5ms per event
- **Debouncing**: 500ms window, ~50-100ms overhead
- **Memory**: ~150MB baseline + ~8MB per thread

#### Content Tracker
- **File reading**: ~50 MB/s (single-threaded)
- **Hashing**: ~50 MB/s (SHA-256)
- **Diff generation**: ~20 MB/s (difflib)
- **Database writes**: ~500 writes/sec

#### Database Queries
- **Recent diffs**: ~50ms (50 records)
- **Search**: ~100ms (FTS5)
- **Time analysis**: ~200ms (complex aggregation)
- **Throughput**: ~1,000 queries/sec

#### SSE
- **Concurrent clients**: 100-200 before degradation
- **Broadcast latency**: ~10-20ms
- **Memory per client**: ~8MB (Python thread)

### Target (Go Implementation)

#### File Watcher
- **Event throughput**: 10,000+ events/sec
- **Latency**: <1ms per event
- **Debouncing**: 500ms window, <5ms overhead
- **Memory**: ~50MB baseline + 2KB per goroutine

#### Content Tracker
- **File reading**: 500 MB/s (concurrent)
- **Hashing**: 500 MB/s (pooled)
- **Diff generation**: 100 MB/s (Myers algorithm)
- **Database writes**: 5,000+ writes/sec

#### Database Queries
- **Recent diffs**: <10ms (50 records)
- **Search**: <20ms (FTS5)
- **Time analysis**: <40ms (optimized)
- **Throughput**: 5,000+ queries/sec

#### SSE
- **Concurrent clients**: 10,000+ connections
- **Broadcast latency**: <5ms
- **Memory per client**: ~2KB (goroutine)

### Benchmark Methodology

#### Automated Benchmarking Suite
```bash
#!/bin/bash
# run_benchmarks.sh

echo "Running performance benchmarks..."

# File watcher throughput
go test -bench=BenchmarkEventThroughput -benchtime=10s ./internal/watcher

# Content hashing
go test -bench=BenchmarkHashLargeFile -benchtime=10s ./internal/tracker

# Database operations
go test -bench=BenchmarkDatabaseWrites -benchtime=10s ./internal/database

# SSE broadcasting
go test -bench=BenchmarkSSEBroadcast -benchtime=10s ./internal/hub

# Generate report
go run cmd/benchmark-report/main.go > benchmark_results.md
```

#### Continuous Benchmarking
```yaml
# .github/workflows/benchmark.yml
name: Performance Benchmarks

on:
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 0 * * *'  # Daily

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Go
        uses: actions/setup-go@v4
        with:
          go-version: '1.21'

      - name: Run benchmarks
        run: ./scripts/run_benchmarks.sh

      - name: Compare with baseline
        run: |
          benchstat baseline.txt new.txt > comparison.txt
          cat comparison.txt

      - name: Fail on regression
        run: |
          if grep -q "slower" comparison.txt; then
            echo "Performance regression detected!"
            exit 1
          fi
```

---

## Documentation & Knowledge Transfer

### Documentation Deliverables

#### 1. Architecture Documentation
- **File**: `docs/ARCHITECTURE_GO_SERVICES.md`
- **Content**:
  - Service architecture diagrams
  - gRPC API reference
  - Data flow diagrams
  - Decision log (why Go, why hybrid, etc.)

#### 2. Development Guide
- **File**: `docs/DEVELOPMENT_GO_SERVICES.md`
- **Content**:
  - Local development setup
  - Building and testing Go services
  - Debugging techniques
  - Common issues and solutions

#### 3. Operations Manual
- **File**: `docs/OPERATIONS_GO_SERVICES.md`
- **Content**:
  - Deployment procedures
  - Monitoring and alerting
  - Troubleshooting guide
  - Rollback procedures

#### 4. API Documentation
- **File**: `docs/API_GRPC.md`
- **Content**:
  - Protocol buffer definitions
  - Service method reference
  - Usage examples
  - Error codes and handling

### Knowledge Transfer Plan

#### Week 1-2: Core Team Training
- Overview presentation (2 hours)
- Hands-on workshop (4 hours)
- Code walkthrough sessions
- Q&A sessions

#### Week 3-4: Documentation & Self-Service
- Complete all documentation
- Video tutorials (screen recordings)
- Internal wiki updates
- FAQ compilation

#### Ongoing: Office Hours
- Weekly office hours for questions
- Slack channel for Go services
- Code review sessions
- Pair programming opportunities

---

## Appendices

### Appendix A: Technology Stack

#### Go Dependencies
```
github.com/fsnotify/fsnotify v1.7.0           # File system notifications
google.golang.org/grpc v1.59.0                # gRPC framework
google.golang.org/protobuf v1.31.0            # Protocol buffers
github.com/mattn/go-sqlite3 v1.14.18          # SQLite driver
github.com/gobwas/glob v0.2.3                 # Glob pattern matching
github.com/sergi/go-diff v1.3.1               # Diff generation
github.com/prometheus/client_golang v1.17.0   # Metrics
go.uber.org/zap v1.26.0                       # Structured logging
```

#### Python Dependencies (New)
```
grpcio==1.59.0              # gRPC client
grpcio-tools==1.59.0        # Protobuf code generation
circuitbreaker==1.4.0       # Circuit breaker pattern
```

### Appendix B: Code Examples

#### Complete gRPC Client (Python)
```python
# backend/clients/base_grpc_client.py
import grpc
import logging
from typing import Optional
from circuitbreaker import circuit

logger = logging.getLogger(__name__)

class BaseGRPCClient:
    def __init__(self, host: str, port: int, service_name: str):
        self.host = host
        self.port = port
        self.service_name = service_name
        self.channel: Optional[grpc.Channel] = None

    def connect(self):
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
            logger.info(f"Connected to {self.service_name} at {self.host}:{self.port}")

    def close(self):
        if self.channel:
            self.channel.close()
            self.channel = None

    @circuit(failure_threshold=5, recovery_timeout=60)
    def call_with_retry(self, method, *args, **kwargs):
        """Call gRPC method with circuit breaker"""
        try:
            self.connect()
            return method(*args, **kwargs)
        except grpc.RpcError as e:
            logger.error(f"{self.service_name} error: {e.code()}: {e.details()}")
            raise
```

### Appendix C: Deployment Checklist

#### Pre-Deployment
- [ ] All tests passing (unit, integration, performance)
- [ ] Documentation complete and reviewed
- [ ] Database backup created
- [ ] Rollback procedure tested
- [ ] Monitoring dashboards configured
- [ ] Health check endpoints verified
- [ ] Feature flags configured
- [ ] Team trained on new architecture

#### Deployment
- [ ] Build Go binaries for target platform
- [ ] Deploy to staging environment
- [ ] Run smoke tests on staging
- [ ] Deploy to production (gradual rollout)
- [ ] Monitor metrics for 24 hours
- [ ] Verify no error rate increase
- [ ] Verify performance improvements

#### Post-Deployment
- [ ] Document lessons learned
- [ ] Update runbooks
- [ ] Archive old Python code
- [ ] Celebrate success! 🎉

### Appendix D: Cost Analysis

#### Development Costs
- **Phase 1**: 3-4 weeks × 1 developer = 3-4 developer-weeks
- **Phase 2**: 2-3 weeks × 1 developer = 2-3 developer-weeks
- **Phase 3**: 2-3 weeks × 1 developer = 2-3 developer-weeks (optional)
- **Phase 4**: 2 weeks × 1 developer = 2 developer-weeks (optional)
- **Total**: 9-15 developer-weeks

#### Infrastructure Costs
- **Additional Compute**: Minimal (Go services are lightweight)
- **Memory Savings**: 3-6x reduction = cost savings
- **Database**: No change (shared SQLite)
- **Monitoring**: Prometheus + Grafana (open source, free)

#### Maintenance Costs
- **Reduced**: Fewer performance issues, simpler concurrency
- **Learning Curve**: Initial investment, long-term benefit
- **Tooling**: Excellent Go tooling (free)

#### ROI Estimate
- **Performance Gains**: 5-10x = handle 10x more files without scaling
- **Resource Savings**: 3x less memory = cheaper hosting
- **Developer Productivity**: Simpler concurrency = faster features
- **Estimated Payback**: 3-6 months

---

## Conclusion

This migration plan provides a comprehensive roadmap for transitioning Obby's performance-critical components from Python to Go while maintaining the advantages of Python for AI integration and rapid development.

### Key Takeaways
1. **Hybrid architecture** balances performance with development velocity
2. **Incremental migration** reduces risk and enables continuous delivery
3. **Feature flags** enable safe, gradual rollout
4. **Comprehensive testing** ensures reliability
5. **Clear rollback procedures** provide safety net

### Success Metrics
- 10x improvement in file event processing
- 5x faster database operations
- 50-100x more concurrent SSE connections
- 3-6x lower memory usage
- Zero data loss or corruption

### Next Steps
1. Review and approve this plan
2. Set up development environment for Go services
3. Begin Phase 1: File Watcher Service
4. Iterate based on learnings

**Timeline**: 9-15 weeks to complete migration
**Effort**: 1 developer full-time
**Risk**: Low (incremental, reversible)
**Impact**: High (significant performance gains)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-10
**Author**: Claude (AI Assistant)
**Status**: Draft - Pending Approval
