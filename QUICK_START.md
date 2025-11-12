# Quick Start Guide

## Prerequisites

### Required for All Modes:
- Python 3.8+
- Dependencies: `pip install -r requirements.txt`
- API Key: Add `ANTHROPIC_API_KEY` to `.env` file for AI features

### Required for Go Services (Recommended):
- Go 1.21+ installed (`go version` to check)
- Built Go service binaries (see below)

## First-Time Setup: Build Go Services

**All 4 Go services are now enabled by default** for 10x+ performance improvement. Build them once before starting:

```bash
# Linux/Mac/WSL
bash scripts/build_go_services.sh

# Windows PowerShell
# (or use WSL/Git Bash for the script above)
cd go-services/file-watcher && go build -o server.exe ./cmd/server
cd ../content-tracker && go build -o server.exe ./cmd/server
cd ../query-service && go build -o server.exe ./cmd/server
cd ../sse-hub && go build -o server.exe ./cmd/server
```

**This only needs to be done once** (or after updating Go service code).

## Starting the Backend

### Standard Startup (All Go Services Enabled)

Just run:
```bash
python backend.py
```

The backend will:
- Start on `http://localhost:8001`
- **Automatically launch all 4 Go services** (File Watcher, Content Tracker, Query Service, SSE Hub)
- Serve the built frontend from `frontend/dist/`

### Python-Only Mode (Fallback)

If Go services fail or you want to use Python implementations:

```bash
# In .env file:
EMERGENCY_ROLLBACK=true

# Or as environment variable:
export EMERGENCY_ROLLBACK=true
python backend.py
```

## What Happens Automatically

When you start `backend.py`:

1. ✅ **All 4 Go services launch automatically** (standard mode)
   - **File Watcher** (gRPC port 50051) - Real-time file monitoring
   - **Content Tracker** (gRPC port 50052) - Content hashing and diffs
   - **Query Service** (gRPC port 50053) - High-performance database queries
   - **SSE Hub** (gRPC port 50054, HTTP port 8080) - Real-time event streaming

2. ✅ **Smart service management**
   - Won't start duplicates if already running
   - Waits for services to be ready before continuing
   - Port availability checking

3. ✅ **Clean shutdown**
   - All Go services stop automatically when backend stops
   - Handles Ctrl+C gracefully
   - No orphaned processes

4. ✅ **Web-based service monitoring**
   - View service status at `http://localhost:8001/` (Services page)
   - Real-time health checks
   - Start/stop/restart individual services via UI
   - Service event logs and metrics

## Troubleshooting

### Go Services Not Starting?

1. **Build the services first:**
   ```bash
   bash scripts/build_go_services.sh
   ```
   This creates binaries in each service directory.

2. **Check Go is installed:**
   ```bash
   go version
   ```
   Should show Go 1.21 or newer.

3. **Check ports are free:**
   ```bash
   # Windows
   netstat -an | findstr "50051 50052 50053 50054 8080"

   # Linux/Mac/WSL
   lsof -i :50051 -i :50052 -i :50053 -i :50054 -i :8080
   ```

4. **Check logs:**
   - See `obby.log` for detailed launcher messages
   - Backend will continue even if Go services fail to start (uses Python fallback)

5. **View service status in UI:**
   - Navigate to Services page in the web interface
   - Check health status and event logs
   - See detailed error messages

### Services Already Running?

The launcher detects running services and won't start duplicates. If you manually started services, the backend will use them.

### Binary Not Found Errors?

If you see "service not found" warnings, the Go binaries aren't built. Run:
```bash
bash scripts/build_go_services.sh
```

### Port Conflicts?

If ports 50051-50054 or 8080 are in use:
- Stop conflicting services
- Or disable Go services with `EMERGENCY_ROLLBACK=true`

### Python Fallback Mode?

Set `EMERGENCY_ROLLBACK=true` in `.env` to disable all Go services and use Python implementations. Good for development or troubleshooting.

## Performance

- **Python-Only Mode**: Good for development, handles moderate workloads
- **Go Services Mode** (Default): 10x+ performance improvement for file operations, queries, and real-time updates

## Service Ports Reference

| Port | Service | Protocol | Purpose |
|------|---------|----------|---------|
| 8001 | Backend | HTTP | Main web server and API |
| 50051 | File Watcher | gRPC | Real-time file monitoring |
| 50052 | Content Tracker | gRPC | Content hashing and diffs |
| 50053 | Query Service | gRPC | Database queries |
| 50054 | SSE Hub | gRPC | Event ingestion |
| 8080 | SSE Hub | HTTP | Server-Sent Events |

