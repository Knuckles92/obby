# Obby
Obby is an AI agent powered by Claude Agent SDK that lives in your Obsidian notes, keeps up with every change in real time, and lets you chat, ask questions, and have it do work directly in your files. 
<img width="1920" height="925" alt="image" src="https://github.com/user-attachments/assets/27683f88-946f-4b7e-b3f3-be4591eb3bcf" />

## Architecture Snapshot
- **Backend**: `backend.py` launches the FastAPI service, the Python file watcher, diff tracker, and SSE publishers that power the UI and database synchronization.
- **Frontend**: React + TypeScript + Vite with Tailwind CSS, receiving real-time updates over SSE and hosting the Claude-driven chat summaries.
- **Data & storage**: `notes/` stores the Markdown payloads, `output/` collects AI artifacts, and `obby.db` holds SQLite FTS5 search, event history, and change metadata.
- **AI & summaries**: Claude Agent SDK (haiku/sonnet/opus) explores the repository with Read/Grep/Glob tools, respecting `.obbywatch`/`.obbyignore`, to produce structured metadata with a Sources section.
- **No Go services**: The Go microservices referenced in older docs have been removed; all APIs and watchers now run in Python (see `.env.example` for the current environment variables).

## Features

### File Monitoring
- Real-time file watching with `watchdog` library
- Periodic scanning as backup detection
- Configurable watch paths via `.obbywatch`
- Ignore patterns via `.obbyignore`
- SHA-256 content hashing for change detection
- Tracks file creation, deletion, and moves

### Database
- SQLite with FTS5 full-text search
- Connection pooling for thread safety
- WAL mode enabled
- Schema migration system
- Stores file versions, diffs, and metadata

### AI Integration
- Claude Agent SDK for summaries and chat
- Interactive chat with tool access (Read, Grep, Glob, Bash, Edit, Write)
- Models: haiku, sonnet, opus
- 30-second debounce for real-time processing
- Claude autonomously explores files using tools
- Structured output with metadata fields

### Search
- FTS5 full-text search
- Query syntax: `topic:name`, `keyword:term`, `impact:level`
- Topic and keyword extraction
- Date range filtering
- Export results

### Web Interface
- React 18 + TypeScript + Tailwind CSS
- Real-time updates via Server-Sent Events
- Interactive chat interface with Claude
- 11 themes with accessibility options
- Responsive design
- Markdown rendering with syntax highlighting

## Installation

### Prerequisites
- Python 3.x
- Node.js 16+
- Anthropic API Key (for AI features)

### Setup

1. Clone and install backend:
   ```bash
   git clone <repository-url>
   cd obby

   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Configure API key:
   ```bash
   export ANTHROPIC_API_KEY="your-key-here"
   ```

3. Build frontend:
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

4. Start the server:
   ```bash
   python backend.py
   ```

   Open http://localhost:8001

### Development Mode

Run backend and frontend separately for hot reload:

```bash
# Terminal 1
python backend.py

# Terminal 2
cd frontend
npm run dev
```

Frontend: http://localhost:5173
Backend API: http://localhost:8001

### First Run

On first startup, Obby creates:
- `notes/` directory for Markdown files
- `output/` directory for summaries
- SQLite database with FTS5 search enabled
- Default watch patterns (configurable via web interface)

## Configuration

### Watch Configuration
Configure via web interface or API:
- `.obbywatch`: Define directories to monitor
- `.obbyignore`: Define patterns to exclude
- Environment config is now limited to the Python stack; the Go microservice flags in earlier versions were removed (see `.env.example` for the current keys).

### AI Configuration
- Model selection: haiku, sonnet, opus
- Debounce window: Default 30 seconds
- API key: Set via environment or web interface

### Session Summary Settings
```json
{
  "updateFrequency": "realtime",
  "summaryLength": "moderate",
  "writingStyle": "technical",
  "includeMetrics": true,
  "maxSections": 10
}
```

## Search

Query examples:
```
"machine learning algorithms"           # Natural language
topic:ai AND keyword:neural            # Boolean operators
impact:significant date:2024-01-01     # Metadata filters
"exact phrase" OR similar              # Phrase matching
```

Features:
- FTS5 full-text search with BM25 ranking
- Topic and keyword extraction
- Impact level filtering (brief, moderate, significant)
- Date range filtering
- Export results

## Performance & Scalability
- Backend dashboards now cache expensive filesystem stats, add targeted indexes, and apply watch filters earlier to keep `/api/monitor/status` and related endpoints responsive (see `docs/PERFORMANCE_IMPROVEMENT_PLAN.md` for the current strategy).
- Frontend dashboards progressively load critical sections, debounce repeated polling, and avoid blocking rendering until high-priority data arrives.
- Keep the watch configuration lean via `.obbywatch` and TTL-based caching to stay within the 500 ms time-to-interactive goal outlined in the plan.

## AI Integration

Uses Claude Agent SDK for summaries, analysis, and interactive chat.

Available models:
- haiku: Fast summaries
- sonnet: Balanced analysis
- opus: Detailed summaries

### Summaries
1. File change detected
2. 30-second debounce window
3. Claude explores files using Read/Grep/Glob tools
4. Generates structured summary with metadata
5. Saves to database

### Chat
- Interactive conversations with Claude
- Claude has access to Read, Grep, Glob, Bash, Edit, Write tools
- Can explore codebase and answer questions
- Real-time progress updates via SSE

Setup:
```bash
export ANTHROPIC_API_KEY="your-key-here"
```

## API Reference

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

Both include all endpoints, request/response schemas, and allow you to test the API directly from your browser.

## Development

### Testing

Backend (pytest):
```bash
pytest
pytest --cov=. --cov-report=html
pytest -m unit          # Unit tests
pytest -m api           # API tests
pytest -m database      # Database tests
```

Frontend (Vitest):
```bash
cd frontend
npm test                # Watch mode
npm run test:run        # Run once
npm run test:coverage   # Coverage report
```

### Deployment

Production server:
```bash
cd frontend && npm run build && cd ..
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8001 backend:app
```

Systemd service:
```ini
[Unit]
Description=Obby
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/obby
ExecStart=/opt/obby/venv/bin/python backend.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## License

do whatever you want

## Tech Stack

- Backend: Python, FastAPI, SQLite
- Frontend: React, TypeScript, Tailwind CSS, Vite
- AI: Claude Agent SDK
