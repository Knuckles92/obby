# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Essential Commands

### Backend Development
- **Start web application**: `python backend.py` (serves built frontend at :8001)
- **Start CLI monitoring**: `python main.py` (displays usage instructions)
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
- Flask REST API server with CORS support and modular blueprint architecture
- SSE (Server-Sent Events) for real-time frontend updates
- Database-backed storage replacing in-memory event tracking
- Integrated file monitoring via `APIObbyMonitor` class
- Organized route modules: `monitoring`, `files`, `living_note`, `search`, `config`, `data`, `admin`

#### Core Monitoring (`core/monitor.py`)
- `ObbyMonitor`: Main monitoring orchestrator
- Handles both real-time (`watchdog`) and periodic file scanning
- Integrates with AI client for content analysis
- Manages `.obbywatch` and `.obbyignore` configuration files

#### File Tracking (`core/file_tracker.py`)
- `FileContentTracker`: Pure file-based content tracking without git dependencies
- Content hashing and native diff generation
- File version management and change detection
- Replaces git-based tracking with file system monitoring

#### Database Layer (`database/`)
- SQLite with optimized settings (WAL mode, foreign keys, FTS5)
- File-focused query classes: `FileQueries` for API endpoints, plus legacy query classes
- Enhanced models: `FileVersionModel`, `ContentDiffModel`, `FileStateModel`, `PerformanceModel`
- Schema migration system via `migration.py` and `migration_git_to_file.py`
- Connection pooling for thread-safe access
- File-based API integration replacing git-based diff endpoints

#### AI Integration (`ai/`)
- `openai_client.py`: OpenAI API integration for content summarization
- `batch_processor.py`: Scheduled batch processing replacing individual AI calls per file change
- Structured JSON responses with topics, keywords, impact levels
- Configurable models (default: `gpt-4.1-mini`)
- Graceful degradation when API unavailable
- Efficient batch processing for improved performance and reduced API costs

#### File Monitoring (`utils/`)
- `file_watcher.py`: Real-time `watchdog` integration
- `ignore_handler.py`: `.obbyignore` pattern matching
- `watch_handler.py`: `.obbywatch` directory management
- `file_helpers.py`: File operation utilities

#### Frontend (`frontend/src/`)
- React 18 + TypeScript + Tailwind CSS
- Vite build system with development server
- Real-time updates via SSE connection to backend
- Main pages: Dashboard, DiffViewer, LivingNote, Settings, Administration
- Component-based architecture with reusable UI elements
- Advanced theming system with multiple built-in themes

### Data Flow
1. **File Change** → `watchdog` events or periodic scan
2. **Event Processing** → Diff generation + content hashing via file tracker
3. **Database Storage** → SQLite with FTS5 indexing (immediate)
4. **Batch AI Analysis** → Scheduled OpenAI summarization + topic/keyword extraction
5. **Real-time Updates** → SSE push to connected frontend clients

### Configuration Management
- **Core settings**: `config/settings.py` (file paths, intervals, AI model)
- **Runtime config**: `config.json` (managed via web interface)
- **Watch paths**: `.obbywatch` (directories to monitor)
- **Ignore patterns**: `.obbyignore` (glob patterns to skip)
- **Environment**: `OPENAI_API_KEY` for AI features

#### Route Organization (`routes/`)
- **Modular blueprint architecture** for clean API organization
- `monitoring.py`: File monitoring and system status endpoints
- `files.py`: File operations and content management
- `living_note.py`: Living note functionality and management
- `search.py`: Search and semantic query endpoints
- `config.py`: Configuration management endpoints
- `data.py`: Data export and analytics endpoints
- `admin.py`: Administrative functions and system management

### Search & Semantic Features
- **Full-text search**: SQLite FTS5 for fast content matching
- **Semantic search**: Topic and keyword extraction via AI
- **Special query syntax**: `topic:name`, `keyword:term` filters
- **Real-time results**: Debounced search with instant updates

## Development Notes

### Database Operations
- File-focused queries via `FileQueries` class for API endpoints in `database/queries.py`
- Legacy query classes maintained for backward compatibility
- Enhanced models for file versions, content diffs, and performance tracking
- Connection pooling handles thread safety automatically
- Schema migrations run automatically on startup (including git-to-file migration)
- FTS5 virtual tables enable fast content search

### File Monitoring Modes
- **Real-time**: Primary monitoring via `watchdog` library (zero latency)
- **Periodic**: Secondary scanning at configurable intervals (catches missed events)
- Both modes can run simultaneously for maximum reliability

### Frontend Integration
- Production mode serves built frontend from `frontend/dist/`
- Development uses separate Vite server at :5173
- SSE endpoint `/api/events/stream` provides real-time updates
- All API endpoints prefixed with `/api/`

### AI Processing
- AI analysis is optional (requires `OPENAI_API_KEY`)
- Batch processing replaces individual AI calls for improved efficiency
- Structured prompts generate JSON with topics, keywords, summaries
- Multiple OpenAI models supported (configured via settings)
- Graceful fallback when AI services unavailable

### Testing & Development
- Test files: `test_batch_ai.py`, `test_file_tracking.py`, `test_file_watcher_fixes.py`
- No formal test framework configured - tests are standalone Python scripts
- Living Note functionality available via `notes/living_note.md`
- Mock themes available in `mocks/` directory for UI development