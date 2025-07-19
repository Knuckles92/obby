# 📝 Obby - Note Change Tracker & AI Memory Builder

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Obby** is a Python-based note change tracker and AI-assisted memory builder that watches your Markdown notes, tracks changes, and uses OpenAI to maintain a living summary of your work.

## 🎯 Features

### ✅ Comprehensive File Monitoring
- **Real-time tracking**: Instant detection of file changes using `watchdog`
- **File content changes**: Monitors markdown files for content modifications
- **File tree changes**: Tracks file/directory creation, deletion, and moves
- **Smart filtering**: Configurable ignore patterns via `.obbyignore`
- **Prevents feedback loops**: Automatically ignores living note updates

### ✅ AI-Enhanced Summaries
- **Content summaries**: AI-generated summaries of file content changes
- **Tree change summaries**: AI analysis of file structure changes
- **Context-aware**: AI understands it's part of a comprehensive monitoring system
- **Dual tracking**: Maintains complete picture of both content and organizational changes

### ✅ Flexible Ignore System
- **`.obbyignore` file**: Gitignore-style pattern matching
- **Glob patterns**: Support for wildcards (`*`, `?`) and directory patterns
- **Default protection**: Automatically ignores common temp files and living note
- **User customizable**: Easy to add/remove ignore patterns

### ✅ Local-First & Minimal
- All data stored locally in text files
- Only external dependency is OpenAI API
- Clean, readable terminal output
- Optional web UI for enhanced user experience

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Node.js 16+ and npm (for web UI)
- OpenAI API key (optional, for AI features)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd obby
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up OpenAI API key** (optional)
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

4. **Run Obby (CLI)**
   ```bash
   python main.py
   ```

5. **Run Obby with Web UI**
   ```bash
   # Terminal 1: Backend API
   python api_server.py
   
   # Terminal 2: Frontend UI
   cd frontend
   npm install
   npm start
   ```
   
   Then open http://localhost:3000 for the web interface.

### First Run
On first run, Obby will:
- Create necessary directories (`notes/`, `diffs/`)
- Generate a test file at `notes/test.md`
- Start monitoring for changes

## 📁 Project Structure

```
obby/
├── main.py                 # CLI entry point
├── api_server.py           # Flask API server for web UI
├── config/
│   └── settings.py         # Configuration settings
├── ai/
│   └── openai_client.py    # OpenAI integration with dual summary support
├── diffing/
│   └── diff_tracker.py     # Diff generation and tracking
├── utils/
│   ├── file_helpers.py     # File utilities
│   ├── file_watcher.py     # Real-time file monitoring
│   └── ignore_handler.py   # .obbyignore pattern matching
├── frontend/               # React + Tailwind web UI
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # Main page components
│   │   └── types/          # TypeScript type definitions
│   ├── package.json
│   └── vite.config.ts
├── notes/
│   ├── test.md            # Your note file (created on first run)
│   └── living_note.md     # AI-generated summary
├── diffs/                 # Human-readable diffs
├── .obbyignore            # File ignore patterns
└── README.md
```

## ⚙️ Configuration

Edit `config/settings.py` to customize:

```python
# File paths
NOTE_PATH = Path("notes/test.md")
DIFF_PATH = Path("diffs")
LIVING_NOTE_PATH = Path("notes/living_note.md")

# Timing settings
CHECK_INTERVAL = 20  # seconds

# OpenAI settings
OPENAI_MODEL = "gpt-4.1-mini"
```

## 🌐 Web UI Features

The React + Tailwind web interface provides:

### 📊 Dashboard
- Real-time monitoring status and controls
- File change statistics and activity feed
- Recent diffs and AI summaries
- Start/stop monitoring with one click

### 📁 File Explorer
- Tree view of watched directories
- Visual indicators for monitored files
- File browsing and navigation

### 🔍 Diff Viewer
- Timeline of all file changes
- Side-by-side diff visualization
- Search and filter capabilities
- Export diff reports

### 📝 Living Note Interface
- Rich display of AI-generated summaries
- Word count and update statistics
- Easy content browsing

### ⚙️ Settings Management
- Visual configuration editor
- Watch path management
- Ignore pattern configuration
- OpenAI settings and model selection

## 🎮 Usage

1. **Start Obby (CLI)**
   ```bash
   python main.py
   ```

2. **Start Obby (Web UI)**
   ```bash
   # Terminal 1: Backend
   python api_server.py
   
   # Terminal 2: Frontend
   cd frontend
   npm start
   ```

3. **Edit your notes**
   - Open `notes/test.md` in your favorite editor
   - Make changes and save
   - Obby will automatically detect changes and create summaries

4. **Manage file structure**
   - Create new files and directories
   - Move or rename files
   - Delete files
   - Obby tracks all file tree changes automatically

5. **Customize ignore patterns**
   - Edit `.obbyignore` to specify files/patterns to ignore
   - Use glob patterns like `*.tmp`, `draft_*.md`, `archive/`
   - Comments supported with `#` prefix

6. **Monitor output**
   - Terminal shows real-time monitoring of both content and tree changes
   - Check `notes/living_note.md` for AI-generated summaries
   - Browse `diffs/` for change history

## 🧠 Planned Features

### User Profile & Topic Tree
- **User Profile**: Stored in `config/profile.json` with topics, frequencies, and activity patterns
- **Topic Tree**: Semantic graph of your work life based on recurring themes
- **Smart Recommendations**: Context-aware suggestions based on your knowledge graph

## 🔧 Development

### Adding New Features
1. **AI Providers**: Extend `ai/` directory for additional LLM providers
2. **File Formats**: Add support for different note formats beyond Markdown
3. **Integrations**: Connect with popular note-taking apps

### Testing
```bash
# Run the application in development mode
python main.py
```

## 📝 Example Output

```
🔍 Starting Obby - Note Change Tracker
========================================
📝 Watching: notes/test.md
⚡ Detection: Real-time file system events
📄 Diffs: diffs
🤖 Living Note: notes/living_note.md

🎯 Ready! Edit the note file to see changes...
Press Ctrl+C to stop

[!] Change detected in test.md
--- previous
+++ current
@@ -1,4 +1,5 @@
 # My Notes
 
 This is a test file for obby to watch.
+Added a new line here!
 Try editing this file to see obby in action!
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

- Built with Python's standard library and minimal dependencies
- Inspired by the need for better note-taking and knowledge management
- Designed to be simple, local-first, and extensible

---

**Happy note-taking! 📝✨**
