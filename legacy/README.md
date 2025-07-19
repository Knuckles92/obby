# Legacy CLI Components

This directory contains the original command-line interface components that have been archived as part of the transition to a web-based frontend.

## Archived Files

- `main_cli.py` - Original CLI entry point with command-line interface functionality
  - Contains the original `main()` function that provided the CLI experience
  - Includes CLI-specific print statements and keyboard interrupt handling
  - The `ObbyMonitor` class has been extracted to `core/monitor.py` for use by the web API

## Why These Components Were Archived

The project has evolved from a CLI-focused tool to a web-based application with a React frontend and Flask API backend. The CLI functionality was preserved for backward compatibility but moved here to:

1. **Clean up the main project structure** - Focus on the web interface components
2. **Separate concerns** - Distinguish between legacy CLI and modern web functionality  
3. **Maintain backward compatibility** - The CLI can still be run via `python main.py`
4. **Preserve history** - Keep the original implementation for reference

## Running the Legacy CLI

The CLI functionality is still available through the main project entry point:

```bash
python main.py
```

This will run the original command-line interface for users who prefer the terminal experience.