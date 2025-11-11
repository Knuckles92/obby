# Quick Start Guide

## Starting the Backend

### Simple Startup (Python Only - Default)

Just run:
```bash
python backend.py
```

The backend will start on `http://localhost:8001` using Python implementations.

### With Go Services (High Performance)

Enable Go services via environment variables:

**Windows PowerShell:**
```powershell
$env:USE_GO_FILE_WATCHER="true"
$env:USE_GO_CONTENT_TRACKER="true"
python backend.py
```

**Windows CMD:**
```cmd
set USE_GO_FILE_WATCHER=true
set USE_GO_CONTENT_TRACKER=true
python backend.py
```

**Linux/Mac/WSL:**
```bash
export USE_GO_FILE_WATCHER=true
export USE_GO_CONTENT_TRACKER=true
python backend.py
```

**Using .env file:**
Create `.env` in project root:
```env
USE_GO_FILE_WATCHER=true
USE_GO_CONTENT_TRACKER=true
```

Then just run:
```bash
python backend.py
```

## What Happens Automatically

When you start `backend.py`:

1. ✅ **Go services launch automatically** (if enabled)
   - File Watcher Service (port 50051)
   - Content Tracker Service (port 50052)

2. ✅ **Services are checked** before launching
   - Won't start duplicates if already running
   - Waits for services to be ready before continuing

3. ✅ **Clean shutdown**
   - All Go services stop automatically when backend stops
   - Handles Ctrl+C gracefully

## Prerequisites

### For Python-Only Mode:
- Python 3.8+
- Dependencies: `pip install -r requirements.txt`

### For Go Services Mode:
- Python 3.8+ (as above)
- Go 1.21+ installed (`go version` to check)
- Go services source code in `go-services/` directory

## Troubleshooting

### Go Services Not Starting?

1. **Check Go is installed:**
   ```bash
   go version
   ```

2. **Check ports are free:**
   ```bash
   # Windows
   netstat -an | findstr "50051 50052"
   
   # Linux/Mac
   lsof -i :50051 -i :50052
   ```

3. **Check logs:**
   - See `obby.log` for launcher messages
   - Backend will continue even if Go services fail to start

### Services Already Running?

The launcher detects running services and won't start duplicates. If you manually started services, the backend will use them.

### Want Manual Control?

Start services manually in separate terminals, then run `python backend.py`. The launcher will detect them and skip auto-launch.

## Performance

- **Python-Only**: Good for development, handles moderate workloads
- **With Go Services**: 10x+ performance improvement for file watching and content tracking

See `GO_SERVICES_STARTUP.md` for detailed information.

