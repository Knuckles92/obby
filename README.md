# 📝 Obby - Note Change Tracker & AI Memory Builder

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Obby** is a Python-based note change tracker and AI-assisted memory builder that watches your Markdown notes, tracks changes, and uses OpenAI to maintain a living summary of your work.

## 🎯 Features

### ✅ Automated Note Tracking
- Monitors `notes/test.md` every 20 seconds for changes
- Creates timestamped snapshots on every change
- Generates human-readable diffs using Python's `difflib`

### ✅ AI-Managed Living Note
- Sends diffs (not full notes) to OpenAI API for summarization
- Maintains a living summary in `notes/living_note.md`
- Keeps your knowledge organized and concise over time

### ✅ Local-First & Minimal
- No server, no database, no web UI
- All data stored locally in text files
- Only external dependency is OpenAI API
- Clean, readable terminal output

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
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

4. **Run Obby**
   ```bash
   python main.py
   ```

### First Run
On first run, Obby will:
- Create necessary directories (`notes/`, `snapshots/`, `diffs/`)
- Generate a test file at `notes/test.md`
- Start monitoring for changes

## 📁 Project Structure

```
obby/
├── main.py                 # Entry point
├── config/
│   └── settings.py         # Configuration settings
├── ai/
│   └── openai_client.py    # OpenAI integration
├── diffing/
│   └── diff_tracker.py     # Diff generation and tracking
├── utils/
│   └── file_helpers.py     # File utilities
├── notes/
│   ├── test.md            # Your note file (created on first run)
│   └── living_note.md     # AI-generated summary
├── snapshots/             # Timestamped snapshots
├── diffs/                 # Human-readable diffs
└── README.md
```

## ⚙️ Configuration

Edit `config/settings.py` to customize:

```python
# File paths
NOTE_PATH = Path("notes/test.md")
SNAPSHOT_PATH = Path("snapshots")
DIFF_PATH = Path("diffs")
LIVING_NOTE_PATH = Path("notes/living_note.md")

# Timing settings
CHECK_INTERVAL = 20  # seconds

# OpenAI settings
OPENAI_MODEL = "gpt-4.1-mini"
```

## 🎮 Usage

1. **Start Obby**
   ```bash
   python main.py
   ```

2. **Edit your notes**
   - Open `notes/test.md` in your favorite editor
   - Make changes and save
   - Obby will automatically detect changes and create summaries

3. **Monitor output**
   - Terminal shows real-time diff output
   - Check `notes/living_note.md` for AI-generated summaries
   - Browse `snapshots/` for historical versions

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
⏰ Check interval: 20 seconds
📁 Snapshots: snapshots
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
