# 📝 Obby - Note Change Tracker & AI Memory Builder

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Obby** is a modern web-based note change tracker and AI-assisted memory builder that watches your Markdown notes, tracks changes in real-time, and uses OpenAI to maintain a living summary of your work.

## 🎯 Features

### ✅ Modern Web Interface
- **Beautiful dashboard**: Real-time monitoring status and activity feed
- **File explorer**: Tree view of watched directories with live updates
- **Diff viewer**: Timeline of changes with side-by-side visualization
- **Living note interface**: Rich display of AI-generated summaries
- **Settings management**: Visual configuration editor with live validation

### ✅ Comprehensive File Monitoring
- **Dual monitoring modes**: Combines real-time event detection with periodic scanning
- **Real-time tracking**: Instant detection of file changes using `watchdog`
- **Periodic checking**: Optional interval-based scanning for comprehensive coverage
- **File content changes**: Monitors markdown files for content modifications
- **File tree changes**: Tracks file/directory creation, deletion, and moves
- **Smart filtering**: Configurable ignore patterns via `.obbyignore`
- **Custom watch paths**: Configure specific directories to monitor via `.obbywatch`

### ✅ AI-Enhanced Summaries
- **Content summaries**: AI-generated summaries of file content changes
- **Tree change summaries**: AI analysis of file structure changes
- **Context-aware**: AI understands it's part of a comprehensive monitoring system
- **Multiple models**: Support for various OpenAI models (GPT-4o, GPT-4.1, GPT-4.1-mini, etc.)
- **Structured metadata**: AI extracts topics, keywords, and impact assessments
- **Session organization**: Groups related changes into development sessions

### ✅ Advanced Search & Discovery
- **Semantic search**: Full-text search with SQLite FTS5 integration
- **Topic-based filtering**: Search by automatically extracted AI topics
- **Keyword search**: Find content by relevant keywords
- **Date range filtering**: Time-based search capabilities
- **Impact level filtering**: Search by change significance (brief, moderate, significant)
- **Search syntax**: Support for special queries (`topic:name`, `keyword:term`, etc.)
- **Real-time results**: Instant search with debounced input

### ✅ High-Performance Database
- **SQLite with WAL mode**: High-performance storage with write-ahead logging
- **Connection pooling**: Thread-safe database access with automatic cleanup
- **Optimized schema**: Normalized tables with performance indexes
- **Content deduplication**: Hash-based duplicate detection for efficient storage
- **Migration system**: Database versioning and automatic schema updates

### ✅ Production Ready
- **Robust error handling**: Comprehensive logging and graceful error recovery
- **Performance optimized**: Efficient API endpoints with caching and limits
- **Security focused**: Input validation and proper error boundaries
- **Local-first**: All data stored locally with optional cloud AI integration

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Node.js 16+ and npm (for frontend)
- OpenAI API key (optional, for AI features)

### Installation & Setup

1. **Clone and install backend**
   ```bash
   git clone <repository-url>
   cd obby
   pip install -r requirements.txt
   ```

2. **Set up OpenAI API key** (optional)
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

3. **Install and build frontend**
   ```bash
   cd frontend
   npm install
   npm run build
   ```

### Running the Application

**Production Mode (Recommended)**
```bash
# Start the API server
python api_server.py

# Open http://localhost:8000 in your browser
```

**Development Mode**
```bash
# Terminal 1: Backend API
python api_server.py

# Terminal 2: Frontend development server
cd frontend
npm run dev
# Open http://localhost:5173
```

### First Run
On first run, Obby will:
- Create necessary directories (`notes/`, `diffs/`)
- Generate a test file at `notes/test.md`
- Create configuration files (`.obbyignore`, `.obbywatch`)
- Start monitoring for changes

## 📁 Project Structure

```
obby/
├── main.py                 # Application entry point
├── api_server.py           # Flask API server for web interface
├── config/
│   └── settings.py         # Core configuration settings
├── core/
│   └── monitor.py          # Core monitoring logic
├── ai/
│   └── openai_client.py    # OpenAI integration
├── diffing/
│   └── diff_tracker.py     # Diff generation and tracking
├── utils/
│   ├── file_helpers.py     # File utilities
│   ├── file_watcher.py     # Real-time file monitoring
│   ├── ignore_handler.py   # .obbyignore pattern matching
│   └── watch_handler.py    # .obbywatch directory management
├── frontend/               # React + TypeScript + Tailwind web UI
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   │   ├── Search.tsx  # Search interface component
│   │   │   ├── SearchResults.tsx # Search results display
│   │   │   └── ...         # Other UI components
│   │   ├── pages/          # Main application pages
│   │   │   ├── SearchPage.tsx # Semantic search page
│   │   │   └── ...         # Dashboard, settings, etc.
│   │   ├── hooks/          # Custom React hooks
│   │   ├── types/          # TypeScript type definitions
│   │   └── utils/          # Frontend utilities (API client, etc.)
│   ├── dist/              # Built frontend files
│   └── package.json
├── database/               # SQLite database storage
│   └── obby.db            # Main database file (auto-created)
├── notes/
│   ├── test.md            # Sample note file
│   └── living_note.md     # AI-generated summary
├── diffs/                 # Change history files (legacy)
├── .obbyignore            # File ignore patterns
├── .obbywatch             # Directory watch configuration
└── config.json            # Runtime configuration
```

## 🌐 Web Interface

### 📊 Dashboard
- **Real-time status**: Current monitoring state and file counts
- **Activity feed**: Live stream of file change events
- **Quick stats**: Events today, watched paths, total files
- **Control center**: Start/stop monitoring with one click

### 📁 File Explorer
- **Interactive tree**: Browse watched directories
- **File details**: Size, modification time, and status
- **Real-time updates**: Tree reflects changes instantly

### 🔍 Diff Viewer
- **Change timeline**: Chronological list of all modifications
- **Content preview**: Truncated diff content with full view option
- **Search & filter**: Find specific changes quickly
- **Metadata**: File paths, timestamps, and change sizes

### 📝 Living Note
- **AI summaries**: Rich display of generated content
- **Statistics**: Word count and last update time
- **Auto-refresh**: Content updates as changes occur

### ⚙️ Settings
- **Watch paths**: Add/remove directories to monitor
- **Ignore patterns**: Configure files and directories to skip
- **AI configuration**: OpenAI API key and model selection
- **Monitoring modes**: Toggle real-time and periodic checking
- **System settings**: Check interval for periodic scanning and other preferences

## 🔄 Backend Workflow

Understanding how Obby processes file changes internally:

### 1. File Change Detection
```
File System → watchdog Events → Event Queue → Processing Pipeline
```
- **Real-time monitoring**: `watchdog` library detects file system events instantly
- **Event debouncing**: Rapid successive changes are batched to prevent duplicate processing
- **Fallback scanning**: Periodic checks ensure no events are missed

### 2. Content Processing Pipeline
```
File Change → Diff Generation → AI Analysis → Database Storage → Frontend Update
```

**Step-by-step process:**
1. **Change Detection**: File modification triggers event
2. **Diff Creation**: Content comparison generates unified diff
3. **Content Hashing**: Duplicate detection prevents redundant storage
4. **AI Processing**: OpenAI analyzes content for:
   - Summary generation
   - Topic extraction
   - Keyword identification
   - Impact assessment (brief/moderate/significant)
5. **Database Storage**: Structured data saved to SQLite with proper indexing
6. **Real-time Updates**: Server-Sent Events (SSE) push changes to connected clients

### 3. Database Operations
```
Events Table ← → Diffs Table ← → Semantic Entries ← → Topics/Keywords
```
- **Normalized schema**: Separate tables for events, diffs, semantic data, topics, keywords
- **Foreign key constraints**: Maintain data integrity across related tables
- **Full-text search**: FTS5 virtual tables enable fast content search
- **Connection pooling**: Thread-safe access with automatic cleanup

### 4. AI Integration Flow
```
Content → OpenAI API → Structured Response → Database → Living Note Update
```
- **Conditional processing**: AI analysis only when API key is configured
- **Structured prompts**: AI generates JSON responses with topics, keywords, summaries
- **Error handling**: Graceful degradation when AI services are unavailable
- **Model flexibility**: Support for multiple OpenAI models with different capabilities

### 5. Real-time Frontend Updates
```
Database Change → SSE Stream → Frontend State → UI Update
```
- **Server-Sent Events**: Persistent connection for live updates
- **Event streaming**: Dashboard, living note, and search results update in real-time
- **Efficient updates**: Only changed data is transmitted to reduce bandwidth

### 6. Search Processing
```
User Query → Query Parser → FTS5 Search → Result Ranking → Response
```
- **Query parsing**: Special syntax for topic/keyword filters (`topic:ai`, `keyword:function`)
- **Full-text search**: SQLite FTS5 provides fast content matching
- **Semantic filtering**: Topic and keyword extraction enables precise filtering
- **Result ranking**: Relevance scoring based on content match and recency

## ⚙️ Configuration

### Core Settings (`config/settings.py`)
```python
# File paths
NOTES_FOLDER = Path("notes")
DIFF_PATH = Path("diffs")
LIVING_NOTE_PATH = Path("notes/living_note.md")

# Timing settings
CHECK_INTERVAL = 20  # seconds (for periodic checking)

# OpenAI settings
OPENAI_MODEL = "gpt-4o-mini"  # Default AI model
```

### Monitoring Modes
Obby uses a dual monitoring approach for maximum reliability:

1. **Real-time Event Detection** (Primary)
   - Instant file system event detection using `watchdog`
   - Zero-latency response to file changes
   - Handles create, modify, delete, and move operations

2. **Periodic Scanning** (Secondary)
   - Optional interval-based checking of all watched files
   - Catches any changes that might be missed by event detection
   - Configurable interval (default: 20 seconds)
   - Can be enabled/disabled via settings

This dual approach ensures no changes are missed while maintaining efficient performance.

### Watch Configuration (`.obbywatch`)
```
# Directories to monitor (one per line)
notes/
documents/work/
projects/active/
```

### Ignore Patterns (`.obbyignore`)
```
# Ignore temporary files
*.tmp
*.bak
~*

# Ignore system files
.DS_Store
Thumbs.db

# Ignore specific directories
archive/
drafts/
```

### Runtime Configuration (`config.json`)
Automatically managed through the web interface:
```json
{
  "checkInterval": 20,
  "openaiApiKey": "sk-...",
  "aiModel": "gpt-4.1-mini",
  "watchPaths": ["notes/", "documents/"],
  "ignorePatterns": ["*.tmp", "*.bak"],
  "periodicCheckEnabled": true
}
```

### Database Configuration
The SQLite database is automatically configured with optimized settings:
- **WAL Mode**: Write-Ahead Logging for better concurrency
- **Connection Pooling**: Thread-safe access with automatic cleanup
- **Foreign Keys**: Enabled for data integrity
- **Full-Text Search**: FTS5 virtual tables for content search
- **Auto-migration**: Schema updates applied automatically on startup

## 🎮 Usage

### Basic Workflow

1. **Start the application**
   ```bash
   python api_server.py
   ```

2. **Open the web interface**
   - Navigate to http://localhost:8000
   - Review the dashboard and current settings

3. **Configure monitoring**
   - Go to Settings page
   - Add directories to watch
   - Set up ignore patterns
   - Configure OpenAI API key (optional)

4. **Start monitoring**
   - Click "Start Monitoring" on the dashboard
   - Watch the activity feed for real-time events

5. **Edit your notes**
   - Create or modify markdown files in watched directories
   - See changes appear instantly in the web interface
   - Check the Living Note for AI-generated summaries

6. **Review history**
   - Use the Diff Viewer to see all changes over time
   - Export change reports
   - Search for specific modifications

### Advanced Features

- **Custom watch paths**: Use `.obbywatch` to monitor specific directories
- **Intelligent ignoring**: Configure `.obbyignore` with glob patterns
- **Multiple models**: Switch between different OpenAI models
- **API integration**: Use the REST API for programmatic access

### Search Functionality

**Semantic Search Examples:**
- **General search**: Enter any text to find related content across all notes
- **Topic filtering**: Use `topic:ai` to find content related to artificial intelligence
- **Keyword search**: Use `keyword:function` to find content with specific keywords
- **Combined queries**: `topic:python keyword:class` to find Python class-related content
- **Date filtering**: Use the date picker to search within specific time ranges
- **Impact filtering**: Filter by change significance (brief, moderate, significant)

**Search Workflow:**
1. Navigate to the Search page from the sidebar
2. Enter your search query using natural language or special syntax
3. Use filters to narrow down results by topic, keyword, or date
4. Click on results to view full content and context
5. Export search results for further analysis

## 🔧 API Reference

The application provides a REST API for programmatic access:

### Core Endpoints
- `GET /api/status` - Get monitoring status
- `POST /api/monitor/start` - Start file monitoring
- `POST /api/monitor/stop` - Stop monitoring

### Data Endpoints
- `GET /api/events` - Get recent file events
- `DELETE /api/events` - Clear all events
- `GET /api/diffs` - Get recent diff files
- `GET /api/living-note` - Get living note content
- `DELETE /api/living-note` - Clear living note content
- `GET /api/files/tree` - Get file tree structure

### Search Endpoints
- `GET /api/search` - Perform semantic search with query parameters
  - `q` - Search query (supports topic:name, keyword:term syntax)
  - `limit` - Number of results (default: 50)
  - `offset` - Pagination offset
- `GET /api/search/topics` - Get all available topics with counts
- `GET /api/search/keywords` - Get all available keywords with counts

### Configuration
- `GET /api/config` - Get current configuration
- `PUT /api/config` - Update configuration
- `GET /api/models` - Get available AI models

## 🛠️ Development

### Backend Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run in development mode
python api_server.py
```

### Frontend Development
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

### Adding Features
1. **New API endpoints**: Add routes to `api_server.py`
2. **Frontend pages**: Create components in `frontend/src/pages/`
3. **AI providers**: Extend the `ai/` module
4. **File handlers**: Modify `utils/` modules

## 📋 Production Deployment

### Environment Setup
```bash
# Set production environment
export FLASK_ENV=production
export OPENAI_API_KEY="your-api-key"

# Install dependencies
pip install -r requirements.txt

# Build frontend
cd frontend && npm install && npm run build
```

### Running in Production
```bash
# Use a production WSGI server
pip install gunicorn

# Start the application
gunicorn -w 4 -b 0.0.0.0:8000 api_server:app
```

### Docker Deployment
```dockerfile
FROM python:3.8-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN cd frontend && npm install && npm run build
EXPOSE 8000
CMD ["python", "api_server.py"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with Python Flask and React
- Uses OpenAI API for intelligent summarization
- Inspired by the need for better note-taking and knowledge management
- Designed to be simple, local-first, and extensible

---

**Happy note-taking! 📝✨**