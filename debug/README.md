# Debug Scripts

This directory contains investigation and debugging utilities for Obby development.

## Scripts

- **`database_diff_investigation.py`** - Analyzes +0/-0 diff entries in the database
- **`diff_analysis.py`** - Tests difflib.unified_diff edge cases and logic
- **`duplicate_processing_simulation.py`** - Simulates duplicate processing issues

## Usage

These are standalone debugging tools. Run directly with Python:

```bash
python debug/database_diff_investigation.py
python debug/diff_analysis.py
python debug/duplicate_processing_simulation.py
```

## Note

These are development tools, not automated tests. For formal testing, see the `/tests/` directory.