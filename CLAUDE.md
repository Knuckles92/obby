# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Backend Development
- **Start web application**: `python backend.py` (serves built frontend at :8001)
- **Start CLI monitoring**: `python main.py` (displays usage instructions and redirects to web mode)
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
Obby is a dual-mode note monitoring application with both web and CLI interfaces:

- **Primary mode**: Web application (`backend.py`) serving React frontend from `frontend/dist/`
- **Legacy mode**: CLI monitoring via `main.py` (redirects to usage instructions)
- **Real-time monitoring**: Dual approach using `watchdog` events + optional periodic scanning
- **AI integration**: OpenAI client with batch processing for content summarization and semantic analysis
- **Database**: SQLite with WAL mode, FTS5 search, connection pooling
- **File tracking**: Pure file-based monitoring without git dependencies

### Key Components

#### Backend (`backend.py`)
- FastAPI server with CORS middleware and modular APIRouter architecture
- SSE (Server-Sent Events) for real-time frontend updates
- Database-backed storage replacing in-memory event tracking
- Integrated file monitoring via `APIObbyMonitor` class
- Organized route modules: `monitoring`, `files`, `living_note`, `summary_note`, `search`, `config`, `data`, `admin`, `watch_config`

#### Core Monitoring (`core/monitor.py`)
- `ObbyMonitor`: Main monitoring orchestrator
- Handles both real-time (`watchdog`) and periodic file scanning
- Integrates with AI client for content analysis
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
  - `migration_git_to_file.py`: Git-to-file system migration
  - `migration_comprehensive_summaries.py`: Summary system enhancements
  - `archive/`: Legacy migration files and schemas
- Connection pooling for thread-safe access with `DatabaseConnection` class
- File-based API integration replacing git-based diff endpoints

#### AI Integration (`ai/`)
- `openai_client.py`: OpenAI API integration for content summarization and semantic analysis
  - Supported models: `gpt-4o`, `gpt-4.1`, `gpt-4.1-mini` (default), `o4-mini`, `gpt-4.1-nano`
  - Automatic format configuration loading from `config/format.md`
  - Structured JSON responses with topics, keywords, impact levels
- `batch_processor.py`: Scheduled batch processing system for efficient AI analysis
  - Replaces individual AI calls per file change with batch operations
  - Configurable batch size and processing intervals
  - Database-stored configuration for batch settings and last update tracking
- Graceful degradation when API unavailable
- Multiple processing modes: immediate processing and scheduled batch processing

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
- **Real-time updates** via SSE connection to backend at `/api/events/stream`
- **Main pages**: Dashboard, DiffViewer, LivingNote, Settings, Administration, SummaryNotes
- **Component architecture** with reusable UI elements and contexts
- **Advanced theming system** with multiple built-in themes and dynamic switching

### Data Flow
1. **File Change** → `watchdog` events or periodic scan
2. **Event Processing** → Diff generation + content hashing via file tracker
3. **Database Storage** → SQLite with FTS5 indexing (immediate)
4. **Batch AI Analysis** → Scheduled OpenAI summarization + topic/keyword extraction
5. **Real-time Updates** → SSE push to connected frontend clients

### Configuration Management
- **Core settings**: `config/settings.py` (file paths, intervals, AI model)
- **Runtime config**: `config.json` (managed via web interface)
- **Living note config**: `config/living_note_settings.json` (living note specific settings)
- **Format templates**: `config/format.md` and `config/format_current_backup.md` (AI formatting templates)
- **Watch paths**: `.obbywatch` (directories to monitor, located in project root)
- **Ignore patterns**: `.obbyignore` (glob patterns to skip, located in project root)
- **Environment**: `OPENAI_API_KEY` for AI features

#### Route Organization (`routes/`)
- **Modular blueprint architecture** for clean API organization
- `monitoring.py`: File monitoring and system status endpoints
- `files.py`: File operations and content management
- `living_note.py`: Living note functionality and management
- `summary_note.py`: Summary note generation and management endpoints
- `search.py`: Search and semantic query endpoints
- `config.py`: Configuration management endpoints
- `data.py`: Data export and analytics endpoints
- `admin.py`: Administrative functions and system management
- `watch_config.py`: Watch configuration management (obbywatch/obbyignore files)
- `api_monitor.py`: API-aware monitoring classes extending core monitoring

#### Services Layer (`services/`)
- **Business logic abstraction** providing core functionality for routes
- `living_note_service.py`: Living note creation, update, and management logic
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
- **Automatic migrations** run on startup including:
  - Git-to-file system migration for legacy installations
  - Comprehensive summaries migration for enhanced AI features
- **FTS5 full-text search** virtual tables for fast content indexing and search

### File Monitoring Modes
- **Real-time**: Primary monitoring via `watchdog` library (zero latency)
- **Periodic**: Secondary scanning at configurable intervals (catches missed events)
- Both modes can run simultaneously for maximum reliability

### Frontend Integration
- Production mode serves built frontend from `frontend/dist/`
- Development uses separate Vite server at :5173
- SSE endpoints provide real-time updates:
  - `/api/living-note/events`
  - `/api/summary-notes/events`
- All API endpoints are prefixed with `/api/`

### AI Processing
- AI analysis is optional (requires `OPENAI_API_KEY`)
- **Dual processing modes**: Immediate processing for real-time updates and scheduled batch processing for efficiency
- **Model selection**: Supports latest OpenAI models including gpt-4o, gpt-4.1 series, and o4-mini
- **Semantic analysis**: Structured prompts generate JSON with topics, keywords, summaries, and impact levels
- **Format templating**: AI responses use configurable format templates from `config/format.md`
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
- Living Note: Daily mode enabled by default. Notes are written to `output/daily/Living Note - YYYY-MM-DD.md` (configurable in `config/settings.py`). Single-file mode `output/living_note.md` remains available if explicitly configured.
- Summary Notes: Generated summaries are stored in `output/summaries/` directory with timestamped filenames
