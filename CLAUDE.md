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

- **Primary mode**: Web application (`api_server.py`) serving React frontend from `frontend/dist/`
- **Legacy mode**: CLI monitoring via `main.py` (redirects to usage instructions)
- **Real-time monitoring**: Dual approach using `watchdog` events + optional periodic scanning
- **AI integration**: OpenAI client for content summarization and semantic analysis
- **Database**: SQLite with WAL mode, FTS5 search, connection pooling

### Key Components

#### Backend (`backend.py`)
- Flask REST API server with CORS support
- SSE (Server-Sent Events) for real-time frontend updates
- Database-backed storage replacing in-memory event tracking
- Integrated file monitoring via `ObbyMonitor` class

#### Core Monitoring (`core/monitor.py`)
- `ObbyMonitor`: Main monitoring orchestrator
- Handles both real-time (`watchdog`) and periodic file scanning
- Integrates with AI client for content analysis
- Manages `.obbywatch` and `.obbyignore` configuration files

#### Database Layer (`database/`)
- SQLite with optimized settings (WAL mode, foreign keys, FTS5)
- Separate query classes: `DiffQueries`, `EventQueries`, `SemanticQueries`, `ConfigQueries`, `AnalyticsQueries`
- Schema migration system via `migration.py`
- Connection pooling for thread-safe access

#### AI Integration (`ai/openai_client.py`)
- OpenAI API integration for content summarization
- Structured JSON responses with topics, keywords, impact levels
- Configurable models (default: `gpt-4.1-mini`)
- Graceful degradation when API unavailable

#### File Monitoring (`utils/`)
- `file_watcher.py`: Real-time `watchdog` integration
- `ignore_handler.py`: `.obbyignore` pattern matching
- `watch_handler.py`: `.obbywatch` directory management
- `file_helpers.py`: File operation utilities

#### Frontend (`frontend/src/`)
- React 18 + TypeScript + Tailwind CSS
- Vite build system with development server
- Real-time updates via SSE connection to backend
- Main pages: Dashboard, Search, DiffViewer, LivingNote, Settings
- Component-based architecture with reusable UI elements

### Data Flow
1. **File Change** → `watchdog` events or periodic scan
2. **Event Processing** → Diff generation + content hashing
3. **AI Analysis** → OpenAI summarization + topic/keyword extraction
4. **Database Storage** → SQLite with FTS5 indexing
5. **Real-time Updates** → SSE push to connected frontend clients

### Configuration Management
- **Core settings**: `config/settings.py` (file paths, intervals, AI model)
- **Runtime config**: `config.json` (managed via web interface)
- **Watch paths**: `.obbywatch` (directories to monitor)
- **Ignore patterns**: `.obbyignore` (glob patterns to skip)
- **Environment**: `OPENAI_API_KEY` for AI features

### Search & Semantic Features
- **Full-text search**: SQLite FTS5 for fast content matching
- **Semantic search**: Topic and keyword extraction via AI
- **Special query syntax**: `topic:name`, `keyword:term` filters
- **Real-time results**: Debounced search with instant updates

## Development Notes

### Database Operations
- All database queries go through dedicated query classes in `database/queries.py`
- Connection pooling handles thread safety automatically
- Schema migrations run automatically on startup
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
- Structured prompts generate JSON with topics, keywords, summaries
- Multiple OpenAI models supported (configured via settings)
- Graceful fallback when AI services unavailable