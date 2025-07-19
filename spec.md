# 📝 Obby – Project Spec (v0.2)

## 📌 Summary

**Obby** is a Python-based note change tracker and AI-assisted memory builder.

It watches a Markdown note file, tracks what has changed, and uses OpenAI to maintain a living summary of your work. Obby will eventually grow into a knowledge tool that builds a profile of you — capturing the topics you care about, how they evolve, and what relationships emerge between them.

The project is intentionally **simple and local-first**, so it’s easy to learn from and expand over time.

---

## 🧱 Features

### ✅ Real-time Change Detection & Diffs

- Obby monitors markdown files in the `notes/` folder using real-time file system events.
- When a file changes:
  - The diff is printed to the terminal using `difflib`.
  - A human-readable, timestamped diff is saved to `diffs/`.

### ✅ AI-Managed Living Note

- After a change, Obby sends the **diff** (not the whole note) to the **OpenAI API**.
- The response is a short, clean summary of what was added, removed, or changed.
- This summary is appended to a **living Markdown file**: `notes/living_note.md`.
- The LLM also helps keep this living note **organized and concise** over time.

### ✅ Human-Readable Output

- All diffs are printed in a clear `+ added / - removed` style using Python's standard `difflib` module.
- Everything is readable and portable — just text files.

### ✅ Web Interface & API

- Flask API server (`api_server.py`) provides REST endpoints for monitoring and data access
- React-based web frontend for modern UI experience
- Legacy CLI interface preserved in `legacy/` directory for backward compatibility
- All data still lives in the local filesystem (`notes/`, `diffs/`)
- The only external call is to the OpenAI API

---

## 🧠 Planned: User Profile & Topic Tree

As you build and write, Obby will also start building a **profile** of you and your work:

### 👤 User Profile

Stored in `config/profile.json`:

```json
{
  "name": "Dylan Fiori",
  "role": "Water Resources Engineer",
  "topics": {}
}
```

This profile will expand over time with:
- Tags, project names, keywords
- Topic frequencies
- Recent activity windows

### 🌲 Topic Tree (WIP)

- Tracks recurring topics across notes and diffs.
- Topics gain **weight** based on frequency and recency.
- Eventually builds a **semantic graph** of your work life.
- Can be used to cluster notes, generate summaries, or recommend context.

