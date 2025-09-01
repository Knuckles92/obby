# 📝 Obby - Intelligent Note Change Tracker & AI Memory Builder

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![React 18+](https://img.shields.io/badge/react-18+-blue.svg)](https://reactjs.org/)
[![TypeScript](https://img.shields.io/badge/typescript-5.0+-blue.svg)](https://www.typescriptlang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Obby** is a sophisticated, modern web-based note change tracker and AI-assisted memory builder that monitors your Markdown notes in real-time, maintains a high-performance SQLite database with full-text search, and uses OpenAI to create intelligent summaries of your work. Built with React, TypeScript, and a comprehensive theme system for a beautiful, accessible user experience.

## 🎯 Core Features

### ✅ **Advanced Database Architecture**
- **SQLite with FTS5**: High-performance full-text search engine for semantic content discovery
- **Normalized Schema**: Optimized database design with foreign keys and proper indexing
- **Connection Pooling**: Thread-safe database access with automatic cleanup and WAL mode
- **Migration System**: Automatic database versioning and schema updates
- **Content Deduplication**: SHA-256 hash-based duplicate detection for efficient storage
- **Performance Monitoring**: Database optimization tools with vacuum and analyze capabilities

### ✅ **Sophisticated Theme System** 
- **11 Beautiful Themes**: Professionally designed themes across 4 categories
  - **Professional**: Corporate, Minimal, Classic
  - **Creative**: Cyberpunk, Forest, Ocean  
  - **Accessible**: High Contrast, Large Text
  - **Special**: Vintage, Neon, Winter
- **Advanced Effects**: Glassmorphism, animations, particle systems, gradient overlays
- **Accessibility First**: WCAG compliance with contrast ratings, motion safety, cognitive load optimization
- **Dynamic Switching**: Auto-switch by time, category filtering, random themes
- **Custom Variables**: User-defined CSS variables for personalization

### ✅ **Intelligent Search & Discovery**
- **Semantic Search**: SQLite FTS5-powered full-text search with relevance ranking
- **Advanced Query Syntax**: Support for `topic:name`, `keyword:term`, `impact:level` filtering
- **Real-time Indexing**: Automatic content indexing with topics and keywords extraction
- **Faceted Search**: Filter by topics, keywords, impact level, date ranges
- **Search Analytics**: Query performance metrics and result optimization
- **Export Capabilities**: Save search results for further analysis

### ✅ **Real-time File Monitoring**
- **Dual Detection System**: Real-time event monitoring + periodic scanning for reliability
- **Smart File Watching**: Configurable via `.obbywatch` with glob pattern support
- **Intelligent Filtering**: Advanced `.obbyignore` patterns with recursive directory support
- **Content Change Tracking**: SHA-256 content hashing for precise change detection
- **File Tree Monitoring**: Creation, deletion, and move operations tracking
- **Performance Optimized**: Debounced events and efficient batch processing

### ✅ **AI-Enhanced Analysis**
- **Multiple Model Support**: GPT-4o, GPT-4.1, GPT-4.1-mini, O4-mini, GPT-4.1-nano
- **Semantic Metadata**: Automatic extraction of topics, keywords, and impact levels
- **Structured Summaries**: AI-generated content with configurable length and style
- **Living Note Generation**: Dynamic, evolving summaries of your work sessions
- **Context-Aware Processing**: AI understands project context and development patterns
- **Custom Prompting**: Configurable AI behavior through format templates

### ✅ **Modern Web Interface**
- **React + TypeScript**: Type-safe, component-based architecture
- **Tailwind CSS**: Utility-first styling with comprehensive design system
- **Real-time Updates**: Server-Sent Events for live data synchronization
- **Responsive Design**: Mobile-first design that works on all devices
- **Accessibility**: Screen reader support, keyboard navigation, focus management
- **Performance**: Optimized rendering with React hooks and efficient state management

### ✅ **Production-Ready Architecture**
- **Flask API Server**: RESTful API with comprehensive endpoint coverage
- **Error Handling**: Graceful error recovery with detailed logging
- **Security**: Input validation, SQL injection prevention, XSS protection
- **Monitoring**: Application health checks and performance metrics
- **Local-First**: All data stored locally with optional cloud AI integration
- **Scalable**: Designed for handling large note collections efficiently

## 🚀 Quick Start

### Prerequisites
- **Python 3.8+** with pip
- **Node.js 16+** with npm
- **OpenAI API Key** (optional, for AI features)

### Installation & Setup

1. **Clone and Setup Backend**
   ```bash
   git clone <repository-url>
   cd obby
   
   # Create virtual environment (recommended)
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

2. **Configure OpenAI API** (optional but recommended)
   ```bash
   # Option 1: Environment variable
   export OPENAI_API_KEY="your-api-key-here"
   
   # Option 2: Set via web interface after startup
   ```

3. **Install and Build Frontend**
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```

4. **Initialize Database**
   ```bash
   # Database and directories are created automatically on first run
   python backend.py
   ```

### Running the Application

**Production Mode (Recommended)**
```bash
# Start the combined API + Frontend server
python backend.py

# Open http://localhost:8001 in your browser
```

**Development Mode**
```bash
# Terminal 1: Backend API with auto-reload
python backend.py

# Terminal 2: Frontend development server with hot reload
cd frontend
npm run dev
# Access frontend at http://localhost:5173
# API available at http://localhost:8001
```

### First Run Experience
Obby automatically sets up your environment:
- Creates `notes/` and `diffs/` directories
- Generates `notes/test.md` with sample content
- Creates `.obbyignore` and `.obbywatch` configuration files
- Initializes SQLite database with optimized schema
- Starts monitoring for file changes immediately

## 📁 Project Architecture

```
obby/
├── 🔧 Backend (Python)
│   ├── backend.py                 # Flask API server + SPA host (port 8001)
│   ├── main.py                    # CLI helper / legacy entry
│   ├── config/
│   │   ├── settings.py            # Core configuration
│   │   └── living_note_settings.json # AI behavior configuration
│   ├── core/
│   │   ├── monitor.py             # File monitoring orchestration
│   │   └── file_tracker.py        # On-demand directory scanning
│   ├── ai/
│   │   ├── openai_client.py       # OpenAI integration
│   │   └── batch_processor.py     # Batch AI processing
│   ├── routes/
│   │   ├── monitoring.py          # /api/monitor/* (control, status, batch AI)
│   │   ├── files.py               # /api/files/* (events, diffs, tree, scans)
│   │   ├── living_note.py         # /api/living-note/* (content, settings, SSE)
│   │   ├── search.py              # /api/search/* (semantic, topics, keywords)
│   │   ├── config.py              # /api/config/* (settings, models)
│   │   ├── data.py                # /api/data/* (clear data)
│   │   └── admin.py               # /api/admin/* (system/db stats)
│   ├── database/
│   │   ├── models.py              # SQLite models with FTS5
│   │   ├── queries.py             # Optimized query layer
│   │   ├── migration.py           # Data migration system
│   │   ├── migration_git_to_file.py # Legacy migration helper
│   │   ├── schema.sql             # File-based database schema (current)
│   │   └── archive/               # Archived schema files
│   └── utils/
│       ├── file_helpers.py        # File system utilities
│       ├── file_watcher.py        # Real-time monitoring
│       ├── ignore_handler.py      # .obbyignore pattern matching
│       ├── watch_handler.py       # .obbywatch directory management
│       ├── migrations.py          # One-off migration tasks
│       └── living_note_path.py    # Living note path resolution
│
├── 🎨 Frontend (React + TypeScript)
│   ├── src/
│   │   ├── components/            # Reusable UI components
│   │   │   ├── Search.tsx         # Advanced search interface (386 lines)
│   │   │   ├── SearchResults.tsx  # Search results display (356 lines)
│   │   │   ├── FilterPanel.tsx    # Search filters (360 lines)
│   │   │   ├── ThemeSwitcher.tsx  # Theme selection (366 lines)
│   │   │   ├── ThemeEffects.tsx   # Visual theme effects (374 lines)
│   │   │   └── Sidebar.tsx        # Navigation sidebar (185 lines)
│   │   ├── pages/                 # Main application pages
│   │   │   ├── Dashboard.tsx      # Real-time monitoring dashboard
│   │   │   ├── SearchPage.tsx     # Semantic search interface (148 lines)
│   │   │   ├── DiffViewer.tsx     # Change history viewer
│   │   │   ├── LivingNote.tsx     # AI-generated summaries
│   │   │   └── Settings.tsx       # Configuration management
│   │   ├── contexts/
│   │   │   └── ThemeContext.tsx   # Theme state management (292 lines)
│   │   ├── themes/
│   │   │   ├── index.ts           # Theme definitions (1044 lines)
│   │   │   ├── css-variables.ts   # CSS variable management
│   │   │   └── utils.ts           # Theme utilities (244 lines)
│   │   ├── types/
│   │   │   └── index.ts           # TypeScript definitions (280 lines)
│   │   └── utils/
│   │       └── api.ts             # API client with type safety
│   └── dist/                      # Built frontend assets
│
├── 🗄️ Data Storage
│   ├── database/
│   │   └── obby.db               # Main SQLite database
│   ├── notes/                    # Watched markdown files
│   │   ├── test.md               # Sample note
│   │   └── daily/                # Daily Living Notes (default)
│   │       └── Living Note - YYYY-MM-DD.md
│   └── diffs/                   # Legacy file-based diffs (migrated to DB)
│
├── ⚙️ Configuration
│   ├── .obbyignore              # File ignore patterns
│   ├── .obbywatch               # Directory watch configuration
│   └── config.json              # Runtime settings (migrated to DB)
│
└── 🎭 Theme Previews
    └── mocks/                   # HTML theme previews (11 themes)
        ├── theme2_midnight_blue.html
        ├── theme8_cyberpunk.html
        └── ...
```

## 🌐 Advanced Web Interface

### 📊 **Real-time Dashboard**
- **Live Monitoring Status**: Current state, watched paths, active file counts
- **Activity Stream**: Real-time feed of file change events with timestamps
- **Performance Metrics**: Events today, database size, search index statistics
- **Quick Controls**: Start/stop monitoring, force refresh, system health checks

### **Professional Themes**
- **Corporate**: Clean, business-focused design with high contrast
- **Minimal**: Ultra-clean interface maximizing content focus
- **Classic**: Traditional design with warm tones and serif typography

### **Creative Themes**
- **Cyberpunk**: Futuristic neon aesthetic with glow effects and animations
- **Forest**: Nature-inspired design with organic textures and calming greens
- **Ocean**: Deep blue aquatic theme with fluid animations and wave effects

### **Accessible Themes**
- **High Contrast**: Maximum visibility with WCAG AAA compliance
- **Large Text**: Enhanced readability with larger fonts and generous spacing

### **Special Themes**
- **Vintage**: Retro design with sepia tones and nostalgic elements
- **Neon**: Vibrant electric theme with dramatic glow effects
- **Winter**: Cool theme with icy blues and snowflake animations

### **Theme Features**
- **Glassmorphism**: Modern translucent effects with backdrop blur
- **Particle Systems**: Animated backgrounds for immersive experiences
- **Accessibility Ratings**: Color contrast, motion safety, cognitive load assessments
- **Custom Effects**: Theme-specific animations and visual enhancements

## 🔍 Advanced Search Capabilities

### **Semantic Search Engine**
```javascript
// Query examples
"machine learning algorithms"           // Natural language
topic:ai AND keyword:neural            // Boolean operators  
impact:significant date:2024-01-01     // Metadata filters
"exact phrase" OR similar              // Phrase matching
```

### **Search Features**
- **FTS5 Ranking**: Relevance-based result ordering with BM25 algorithm
- **Topic Extraction**: AI-powered topic identification and categorization
- **Keyword Analysis**: Automatic keyword extraction with frequency analysis
- **Impact Assessment**: AI-generated significance levels (brief, moderate, significant)
- **Date Range Filtering**: Flexible time-based search with calendar picker
- **Export Results**: Save search results for analysis and reporting

### **Performance Optimization**
- **Index Optimization**: Automatic FTS5 index maintenance and rebuilding
- **Query Caching**: Intelligent caching of frequent search patterns
- **Result Pagination**: Efficient large result set handling
- **Search Analytics**: Query performance monitoring and optimization

## ⚙️ AI Integration

### **OpenAI Model Support**
- **GPT-4o**: Latest flagship model with enhanced capabilities
- **GPT-4.1**: Advanced reasoning and analysis
- **GPT-4.1-mini**: Optimized for speed and efficiency
- **O4-mini**: Specialized for structured analysis
- **GPT-4.1-nano**: Ultra-fast processing for real-time analysis

### **Advanced AI Features**
- **Semantic Analysis**: Automatic topic and keyword extraction
- **Impact Assessment**: AI-generated significance levels for changes
- **Structured Prompting**: Configurable AI behavior through format templates
- **Context Awareness**: AI understands project context and development patterns
- **Living Note Generation**: Dynamic, evolving summaries of work sessions

### **Customization Options**
- **Prompt Templates**: Custom AI instructions for different content types
- **Response Formatting**: Structured output with JSON schema validation
- **Focus Areas**: Configure AI attention for specific topics or technologies
- **Update Frequency**: Control how often AI analysis runs

## 🛠️ Configuration System

### **Watch Configuration (`.obbywatch`)**
```plaintext
# Directories to monitor (supports glob patterns)
notes/
documents/projects/
src/**/*.md
```

### **Ignore Patterns (`.obbyignore`)**
```plaintext
# Git-style patterns
*.tmp
*.bak
.DS_Store
node_modules/
**/archive/**
```

### **Living Note Settings**
```json
{
  "updateFrequency": "realtime",
  "summaryLength": "moderate", 
  "writingStyle": "technical",
  "includeMetrics": true,
  "maxSections": 10,
  "focusAreas": ["algorithms", "architecture", "performance"]
}
```

### **Database Configuration**
```json
{
  "checkInterval": 20,
  "periodicCheckEnabled": true,
  "openaiApiKey": "sk-...",
  "aiModel": "gpt-4.1-mini",
  "watchPaths": ["notes/", "documents/"],
  "ignorePatterns": ["*.tmp", "*.bak"]
}
```

## 📡 Complete API Reference

### **Monitoring Endpoints**
```http
GET    /api/monitor/status         # Monitoring status and statistics
POST   /api/monitor/start          # Start file monitoring
POST   /api/monitor/stop           # Stop monitoring
POST   /api/monitor/scan           # Manually scan files for changes

# Batch AI processing controls
GET    /api/monitor/batch-ai/status # Get batch AI processing status
POST   /api/monitor/batch-ai/trigger # Trigger batch AI processing (JSON: { force: boolean })
GET    /api/monitor/batch-ai/config  # Get batch AI configuration
PUT    /api/monitor/batch-ai/config  # Update batch AI configuration (enabled, interval, max_batch_size)
```

### **File Endpoints**
```http
GET    /api/files/events                 # Recent file events
GET    /api/files/diffs                  # Recent content diffs (limit, offset, file_path)
GET    /api/files/diffs/{id}             # Full diff content by ID
GET    /api/files/changes                # Recent file changes (pagination)
GET    /api/files/recent-changes         # Alias for /changes
POST   /api/files/scan                   # Manually scan files (JSON: directory, recursive)
POST   /api/files/clear                  # Clear all file tracking data
POST   /api/files/clear-unwatched        # Clear diffs for unwatched files
GET    /api/files/{path}/history         # Version history for a file
GET    /api/files/{path}/diff?version1=&version2= # Diff between versions
GET    /api/files/{path}/state           # Current state of a file
GET    /api/files/tree                   # File tree structure
GET    /api/files/watched                # Watched files with metadata
```

### **Data Management Endpoints**
```http
POST   /api/data/files/clear            # Clear file records (files, events)
POST   /api/data/events/clear           # Clear all events
POST   /api/data/diffs/clear            # Clear file-based diffs
```

### **Search Endpoints**
```http
GET    /api/search/                # Search with query params
  ?q=query                         # Required query string
  &limit=20                        # Result limit (default 20)
  &type=content|tree               # Optional change type filter

POST   /api/search/semantic        # Search via JSON body
  { "query": "text", "limit": 10 }

GET    /api/search/topics          # All topics with counts
GET    /api/search/keywords        # All keywords with frequency
```

### **Living Note Endpoints**
```http
GET    /api/living-note/           # Get current living note content (root)
GET    /api/living-note/content    # Get current living note content
POST   /api/living-note/clear      # Clear living note content
POST   /api/living-note/update     # Update/regenerate from AI (JSON: { force: boolean })
GET    /api/living-note/events     # Server-Sent Events stream for updates
GET    /api/living-note/settings   # Get living note settings
POST   /api/living-note/settings   # Save living note settings
```

### **Configuration Endpoints**
```http
GET    /api/config                 # Get current configuration
PUT    /api/config                 # Update configuration
GET    /api/config/models          # Get available AI models
```

### **Admin/System Endpoints**
```http
GET    /api/admin/system/stats      # System statistics
GET    /api/admin/system/health     # System health check
POST   /api/admin/system/clear-logs # Clear system logs (backs up first)
POST   /api/admin/database/optimize # Database maintenance
GET    /api/admin/database/stats    # Database statistics
```

## 🚀 Development & Deployment

### **Development Setup**
```bash
# Backend development with auto-reload
pip install -r requirements.txt
python backend.py

# Frontend development with hot reload
cd frontend
npm install
npm run dev

# Database development (legacy migration in archive/ if needed)
# Note: Current system uses automatic migrations via migration_git_to_file.py and migration_comprehensive_summaries.py
```

### **Testing**
```bash
# Backend testing
python -m pytest tests/

# Frontend testing  
cd frontend
npm test

# Integration testing
npm run test:e2e
```

### **Production Deployment**

**Docker Deployment**
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN cd frontend && npm install && npm run build

EXPOSE 8001
CMD ["python", "backend.py"]
```

**Manual Deployment**
```bash
# Production build
cd frontend && npm run build && cd ..

# Production server
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8001 backend:app

# Environment variables
export FLASK_ENV=production
export OPENAI_API_KEY="your-key"
```

**System Service**
```ini
[Unit]
Description=Obby Note Tracker
After=network.target

[Service]
Type=simple
User=obby
WorkingDirectory=/opt/obby
ExecStart=/opt/obby/venv/bin/python backend.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## 🔬 Advanced Usage

### **Custom AI Prompts**
Create custom format templates in `format.md`:
```markdown
# Custom Analysis Format

When analyzing code changes, focus on:
- Performance implications
- Security considerations  
- Architecture patterns
- Testing requirements

Generate structured output with:
- Summary (max 100 words)
- Key topics (max 5)
- Impact level (brief/moderate/significant)
- Recommendations (max 3)
```

### **Search Automation**
```python
# Programmatic search API usage
import requests

response = requests.get('http://localhost:8001/api/search', {
    'q': 'machine learning',
    'topics': 'ai,algorithms',
    'limit': 100
})

results = response.json()
for result in results['results']:
    print(f"{result['timestamp']}: {result['summary']}")
```

### **Database Optimization**
```python
# Manual database maintenance
from database.models import PerformanceModel

# Get statistics
stats = PerformanceModel.get_stats()
print(f"Database size: {stats['database_size_bytes']} bytes")

# Optimize database
PerformanceModel.vacuum()  # Reclaim space
PerformanceModel.analyze() # Update query planner stats
```

### **Theme Development**
```typescript
// Create custom theme
const customTheme: Theme = {
  id: 'custom-dark',
  name: 'Custom Dark',
  category: 'professional',
  description: 'My custom dark theme',
  colors: {
    primary: '#6366f1',
    background: '#0f172a',
    // ... define all required colors
  },
  // ... other theme properties
};

// Register theme
themes.push(customTheme);
```

## 🤝 Contributing

### **Development Workflow**
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests (`npm test && python -m pytest`)
4. Commit changes (`git commit -m 'Add amazing feature'`)
5. Push to branch (`git push origin feature/amazing-feature`)
6. Open Pull Request

### **Code Standards**
- **Python**: Follow PEP 8, use type hints, comprehensive docstrings
- **TypeScript**: Strict mode enabled, comprehensive interfaces
- **Testing**: Unit tests for all new features, integration tests for API endpoints
- **Documentation**: Update README for new features, inline code documentation

### **Architecture Guidelines**
- **Database**: Use normalized schema, proper indexing, type-safe queries
- **API**: RESTful design, comprehensive error handling, input validation
- **Frontend**: Component-based architecture, accessibility compliance
- **Themes**: Follow accessibility guidelines, test with screen readers

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

**Built with modern technologies:**
- **Backend**: Python, Flask, SQLite with FTS5, OpenAI
- **Frontend**: React 18, TypeScript 5, Tailwind CSS, Vite
- **Architecture**: RESTful API, real-time updates, responsive design
- **AI**: OpenAI GPT models for intelligent content analysis

**Designed for developers who value:**
- **Performance**: Optimized database queries and efficient frontend rendering
- **Accessibility**: WCAG compliance and comprehensive theme system
- **Flexibility**: Configurable monitoring, AI behavior, and visual themes
- **Reliability**: Robust error handling and production-ready architecture

---

**Transform your note-taking workflow with intelligent monitoring and AI-powered insights! 📝✨**
