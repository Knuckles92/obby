# Go Services Auto-Startup Guide

## Overview

The backend now automatically launches Go microservices when enabled via feature flags. No manual startup required!

## How It Works

When you run `python backend.py`, the system will:

1. Check if Go services are enabled via environment variables
2. Automatically launch the required Go services as subprocesses
3. Wait for services to become available before continuing
4. Automatically stop services on shutdown

## Usage

### Option 1: Enable Go Services (Recommended)

Set environment variables before starting:

```bash
# Windows PowerShell
$env:USE_GO_FILE_WATCHER="true"
$env:USE_GO_CONTENT_TRACKER="true"
python backend.py

# Windows CMD
set USE_GO_FILE_WATCHER=true
set USE_GO_CONTENT_TRACKER=true
python backend.py

# Linux/Mac/WSL
export USE_GO_FILE_WATCHER=true
export USE_GO_CONTENT_TRACKER=true
python backend.py
```

### Option 2: Use .env File

Create or update `.env` file in project root:

```env
USE_GO_FILE_WATCHER=true
USE_GO_CONTENT_TRACKER=true
GO_FILE_WATCHER_HOST=localhost
GO_FILE_WATCHER_PORT=50051
GO_CONTENT_TRACKER_HOST=localhost
GO_CONTENT_TRACKER_PORT=50052
```

Then just run:
```bash
python backend.py
```

### Option 3: Python-Only (Default)

If you don't set the flags, the system uses Python implementations:

```bash
python backend.py
```

## Service Detection

The launcher automatically:
- ✅ Checks if services are already running (won't start duplicates)
- ✅ Uses built binaries if available (`go-services/*/server` or `server.exe`)
- ✅ Falls back to `go run` if binaries don't exist
- ✅ Waits for services to become available before continuing
- ✅ Logs startup status and any errors

## Manual Control

If you prefer to start services manually:

```bash
# Terminal 1: File Watcher
cd go-services/file-watcher
go run ./cmd/server

# Terminal 2: Content Tracker  
cd go-services/content-tracker
go run ./cmd/server

# Terminal 3: Python Backend
python backend.py
```

The auto-launcher will detect running services and skip launching duplicates.

## Troubleshooting

### Services Not Starting

1. **Check Go is installed:**
   ```bash
   go version
   ```

2. **Check ports are available:**
   ```bash
   # Windows
   netstat -an | findstr "50051 50052"
   
   # Linux/Mac
   lsof -i :50051 -i :50052
   ```

3. **Check logs:**
   - Go service output is captured but not displayed by default
   - Check `obby.log` for launcher messages
   - Check Go service logs if running manually

### Build Binaries for Faster Startup

Build Go services once for faster startup:

```bash
# File Watcher
cd go-services/file-watcher
go build -o server.exe ./cmd/server  # Windows
go build -o server ./cmd/server      # Linux/Mac

# Content Tracker
cd go-services/content-tracker
go build -o server.exe ./cmd/server  # Windows
go build -o server ./cmd/server      # Linux/Mac
```

The launcher will use these binaries instead of `go run`.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `USE_GO_FILE_WATCHER` | `false` | Enable Go file watcher |
| `USE_GO_CONTENT_TRACKER` | `false` | Enable Go content tracker |
| `GO_FILE_WATCHER_HOST` | `localhost` | File watcher host |
| `GO_FILE_WATCHER_PORT` | `50051` | File watcher port |
| `GO_CONTENT_TRACKER_HOST` | `localhost` | Content tracker host |
| `GO_CONTENT_TRACKER_PORT` | `50052` | Content tracker port |
| `EMERGENCY_ROLLBACK` | `false` | Force Python implementations |

## Emergency Rollback

If Go services cause issues, force Python implementations:

```bash
export EMERGENCY_ROLLBACK=true
python backend.py
```

This will use Python implementations even if Go services are enabled.

