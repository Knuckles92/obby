# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚡ Recent Major Change: OpenAI → Claude Migration (October 2025)

**Status**: ✅ Core migration complete

Obby now uses **Claude Agent SDK** exclusively for AI-powered summaries. The legacy OpenAI integration has been removed. Key changes:

- **AI Approach**: Claude autonomously explores files using Read/Grep/Glob tools (vs. receiving truncated diff text)
- **Processing**: Real-time with 30s debounce (vs. 12-hour batch processing)
- **Output**: Structured markdown with 9 metadata fields (vs. simple bullets with 3 fields)
- **Configuration**: `ANTHROPIC_API_KEY` is required for all AI features

📖 See `MIGRATION_SUMMARY.md` for complete details, rollback plan, and troubleshooting.

## Essential Commands

### Backend Development
- **Start web application**: `python backend.py` (serves built frontend at :8001)
- **Install dependencies**: `pip install -r requirements.txt`

### Frontend Development
- **Install dependencies**: `cd frontend && npm install`
- **Development server**: `cd frontend && npm run dev` (serves at :5173)
- **Build for production**: `cd frontend && npm run build`
- **Lint frontend**: `cd frontend && npm run lint`

### Testing & Quality
- **No test framework currently configured** - check with user before assuming test commands
- **Linting**: Frontend has ESLint via `npm run lint` in frontend/ directory
- **No Python linting configured** - check requirements.txt and ask user for preferred tools

## Development Guidance

### Testing Assumptions
- **Environment Preparation**: For testing, always assume the user has the frontend and backend server already running in their dev environment
- Do not offer to run servers during testing or development scenarios

## Architecture Overview

### Core Application Structure
Obby is a web-based note monitoring application:

- **Primary mode**: Web application (`backend.py`) serving React frontend from `frontend/dist/`
- **Real-time monitoring**: Dual approach using `watchdog` events + optional periodic scanning
- **AI integration**: Claude Agent SDK handles summaries, monitoring context, and interactive tooling
- **Database**: SQLite with WAL mode, FTS5 search, connection pooling
- **File tracking**: Pure file-based monitoring without git dependencies

### Key Components

#### Backend (`backend.py`)
- FastAPI server with CORS middleware and modular APIRouter architecture
- SSE (Server-Sent Events) for real-time frontend updates
- Database-backed storage replacing in-memory event tracking
- Integrated file monitoring via `APIObbyMonitor` class
- Organized route modules: `monitoring`, `files`, `session_summary`, `summary_note`, `search`, `config`, `data`, `admin`, `watch_config`

#### Core Monitoring (`core/monitor.py`)
- `ObbyMonitor`: Main monitoring orchestrator
- Handles both real-time (`watchdog`) and periodic file scanning
- Sends file changes to content tracker for semantic processing
- Manages `.obbywatch` and `.obbyignore` configuration files (located in project root)

#### File Tracking (`core/file_tracker.py`)
- `FileContentTracker`: Pure file-based content tracking without git dependencies
- Content hashing and native diff generation
- File version management and change detection
- Replaces git-based tracking with file system monitoring

#### Database Layer (`database/`)
- SQLite with optimized settings (WAL mode, foreign keys, FTS5)
- File-focused query classes: `FileQueries` for API endpoints, plus legacy query classes
- Enhanced models: `FileVersionModel`, `ContentDiffModel`, `FileStateModel`, `PerformanceModel`, `SemanticModel`, `ConfigModel`, `EventModel`, `FileChangeModel`
- Schema migration system:
  - `migration.py`: Core migration utilities
  - `migration_comprehensive_summaries.py`: Summary system enhancements
  - `archive/`: Legacy migration files and schemas
- Connection pooling for thread-safe access with `DatabaseConnection` class
- File-based API integration replacing git-based diff endpoints

#### AI Integration (`ai/`)
- `claude_agent_client.py`: Claude Agent SDK integration for intelligent summaries and chat tooling
  - Autonomous file exploration using Read/Grep/Glob tools
  - Real-time processing with 30s debounce window
  - Rich metadata with 9 structured fields including Sources section
  - Supported models: haiku, sonnet, opus
  - Real-time processing with 30s debounce replacing legacy batch system

## Agent Prompting: Time Query “Sources” Pattern
- Goal: Every query output includes a "Sources" section (model-rendered) listing files used and why.
- Backend responsibilities:
  - Build prompt with: time range, stats, change types, top topics/keywords.
  - Include a de‑duplicated list of candidate files from DB analysis and truncated recent diffs.
  - Do not append backend-rendered provenance to markdown; rely on model.
- Model instruction:
  - System prompt requires "Sources" section at the end with one‑sentence rationale per file.
- Filtering controls:
  - `includeDeleted` flag controls whether analysis includes deleted files; `.obbywatch` patterns constrain inputs.
  - Internal artifacts like `notes/semantic_index.json` are excluded.
- Cleanup endpoints developers may need:
  - `POST /api/files/clear-missing`, `POST /api/files/clear-semantic`, `POST /api/files/clear`, `POST /api/files/scan`.
- Code references:
  - Analysis: `database/queries.py::FileQueries.get_comprehensive_time_analysis`
  - Watch filtering: `utils/watch_handler.py`
- Example prompt outline: `example.markdownn`

## Applying This Pattern Across Features
- When adding AI-backed features:
  - Provide structured, minimal context + clear instruction to include "Sources".
  - Pass a single, deduplicated file list rather than multiple scattered mentions.
  - Let the model render the provenance section to keep output consistent.
  - Respect `.obbywatch`/`.obbyignore` and exclude internal artifacts from context.

### Session Summary
- One AI call that returns both minimal bullets and a '### Sources' section.
- Code: `ClaudeAgentClient.summarize_session(...)` provides autonomous exploration and includes Sources.
- Called by `services/session_summary_service.py` using file paths as context (not diff text).

### Comprehensive/Batch Summaries
- Batch prompt format now includes a required 'Sources' section.
- User content includes a deduplicated list of files considered for robustness.

#### File Monitoring (`utils/`)
- `file_watcher.py`: Real-time `watchdog` integration
- `ignore_handler.py`: `.obbyignore` pattern matching
- `watch_handler.py`: `.obbywatch` directory management
- `file_helpers.py`: File operation utilities

#### Frontend (`frontend/src/`)
- **React 18 + TypeScript + Tailwind CSS** for modern UI development
- **Vite build system** with hot reload development server
- **Key dependencies**:
  - `react-router-dom`: Client-side routing and navigation
  - `react-markdown` + `remark-gfm`: Markdown rendering with GitHub flavor
  - `react-syntax-highlighter`: Code syntax highlighting
  - `lucide-react`: Modern icon library
- **Real-time updates** via SSE connections:
  - `/api/session-summary/events`
  - `/api/summary-notes/events`
- **Main pages**: Dashboard, DiffViewer, SessionSummary, Settings, Administration, SummaryNotes
- **Component architecture** with reusable UI elements and contexts
- **Advanced theming system** with multiple built-in themes and dynamic switching

### Data Flow
1. **File Change** → `watchdog` events or periodic scan
2. **Event Processing** → Diff generation + content hashing via file tracker
3. **Database Storage** → SQLite with FTS5 indexing (immediate)
4. **Claude Summaries** → Autonomous session digest + topic/keyword extraction
5. **Real-time Updates** → SSE push to connected frontend clients

### Configuration Management
- **Core settings**: `config/settings.py` (file paths, intervals, AI model)
- **Runtime config**: `config.json` (managed via web interface)
- **Living note config**: `config/session_summary_settings.json` (session summary specific settings)
- **Format templates**: `config/format.md` and `config/format_current_backup.md` (AI formatting templates)
- **Watch paths**: `.obbywatch` (directories to monitor, located in project root)
- **Ignore patterns**: `.obbyignore` (glob patterns to skip, located in project root)
- **Environment**: `ANTHROPIC_API_KEY` for AI features

#### Route Organization (`routes/`)
- **Modular blueprint architecture** for clean API organization
- `monitoring.py`: File monitoring and system status endpoints
- `files.py`: File operations and content management
- `session_summary.py`: Living note functionality and management
- `summary_note.py`: Summary note generation and management endpoints
- `search.py`: Search and semantic query endpoints
- `config.py`: Configuration management endpoints
- `data.py`: Data export and analytics endpoints
- `admin.py`: Administrative functions and system management
- `watch_config.py`: Watch configuration management (obbywatch/obbyignore files)
- `api_monitor.py`: API-aware monitoring classes extending core monitoring

#### Services Layer (`services/`)
- **Business logic abstraction** providing core functionality for routes
- `session_summary_service.py`: Living note creation, update, and management logic
- `summary_note_service.py`: Summary note generation and processing services
- Services handle complex operations and integrate with multiple data models
- Provides reusable business logic across different API endpoints

### Search & Semantic Features
- **Full-text search**: SQLite FTS5 for fast content matching
- **Semantic search**: Topic and keyword extraction via AI
- **Special query syntax**: `topic:name`, `keyword:term` filters
- **Real-time results**: Debounced search with instant updates

## Development Notes

### Database Operations
- **File-focused queries** via `FileQueries` class for API endpoints in `database/queries.py`
- **Legacy compatibility** with EventQueries, ConfigQueries for backward compatibility
- **Enhanced models** for comprehensive file tracking:
  - File versions, content diffs, file state tracking
  - Performance monitoring and semantic analysis
  - Configuration management and event logging
- **Thread-safe operations** with connection pooling via `DatabaseConnection` class
- **Automatic migrations** run on startup including comprehensive summaries migration for enhanced AI features
- **FTS5 full-text search** virtual tables for fast content indexing and search

### File Monitoring Modes
- **Real-time**: Primary monitoring via `watchdog` library (zero latency)
- **Periodic**: Secondary scanning at configurable intervals (catches missed events)
- Both modes can run simultaneously for maximum reliability

### Frontend Integration
- Production mode serves built frontend from `frontend/dist/`
- Development uses separate Vite server at :5173
- SSE endpoints provide real-time updates:
  - `/api/session-summary/events`
  - `/api/summary-notes/events`
- All API endpoints are prefixed with `/api/`

### AI Processing
- AI analysis uses the Claude Agent SDK (requires `ANTHROPIC_API_KEY`)
- Real-time summaries generated with a 30s debounce window to batch rapid edits
- Supported models: Claude haiku, sonnet, opus (configurable via `/api/config/models`)
- Semantic analysis: Structured prompts capture topics, keywords, summaries, and impact levels
- Format templating: AI responses use configurable format templates from `config/format.md`
- **Batch optimization**: Configurable batch sizes and intervals reduce API costs and improve performance
- Graceful fallback when AI services unavailable

### Testing & Development
- **Debug scripts**: Located in `debug/` directory with specialized tools:
  - `database_diff_investigation.py`: Database diff analysis and debugging
  - `diff_analysis.py`: Content diff investigation utilities
  - `duplicate_processing_simulation.py`: Processing simulation and testing
- **Mock resources**: `mocks/` directory contains theme development files for UI testing
  - Multiple theme HTML files for frontend theme development and testing
  - Helps developers test theming system without full application setup
- **Formal tests**: `tests/` directory reserved for future unit/integration tests
- **No formal test framework configured** - debugging uses standalone Python scripts

### Backup & Log Management
- **Database backups**: Automatic retention policy (7 days) via `utils/backup_retention.py`
- **Log files**: Automatic cleanup for log backups (3 days) and general logs (14 days)
- **Manual cleanup**: Run `python utils/backup_retention.py` for dry-run analysis
- Session Summary: Daily mode enabled by default. Notes are written to `output/daily/Session Summary - YYYY-MM-DD.md` (configurable in `config/settings.py`). Single-file mode `output/session_summary.md` remains available if explicitly configured.
- Summary Notes: Generated summaries are stored in `output/summaries/` directory with timestamped filenames
