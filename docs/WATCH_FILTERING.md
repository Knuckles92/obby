# Watch Filtering System - Strict Mode

## Overview

The Obby monitoring system uses **STRICT watch filtering** to ensure that only explicitly watched files are tracked, analyzed, and accessible to AI agents. This prevents unwanted files from outside your designated watch directories from being processed.

## How It Works

### Configuration File: `.obbywatch`

The `.obbywatch` file in your project root defines which directories and files should be monitored:

```
# Obby watch file
# Lines starting with # are comments

# Watch a directory (trailing slash)
notes/

# Watch files matching a pattern
*.md

# Watch a specific subdirectory
research/papers/
```

### Strict Mode Behavior

**IMPORTANT**: The system operates in STRICT MODE by default:

- ✅ **If `.obbywatch` contains patterns**: Only files matching those patterns are tracked
- ⛔ **If `.obbywatch` is empty or missing**: NO files are tracked (fail-safe mode)
- 🔒 **No fallback to "watch everything"**: Empty patterns = watch nothing

This ensures you never accidentally track files outside your intended scope.

## Fixed Components

### 1. Core Watch Logic (`utils/watch_handler.py`)

**Before**: Empty patterns defaulted to "watch everything"  
**After**: Empty patterns = watch NOTHING (strict mode)

```python
if not self.watch_patterns:
    # STRICT MODE: watch NOTHING if no patterns defined
    logging.warning(f"No watch patterns - file {file_path} ignored")
    return False
```

### 2. File Tracker (`core/file_tracker.py`)

**Before**: Watch checking was conditional/optional  
**After**: ALWAYS enforces watch patterns

```python
# STRICT: Always check if file should be watched
if not self.watch_handler.should_watch(Path(file_path)):
    logger.debug(f"Rejecting file change for {file_path}")
    return None
```

### 3. File Watcher (`utils/file_watcher.py`)

**Before**: Fell back to watching notes folder if no patterns  
**After**: Refuses to start if no watch directories defined

```python
if not watch_dirs:
    # STRICT MODE: refuse to start without watch patterns
    logging.error("No watch directories - monitoring disabled!")
    return
```

### 4. Database Queries (`database/queries.py`)

**Before**: Watch filtering was optional  
**After**: Auto-initializes watch_handler if None provided

All query methods now include:
```python
# STRICT: Always initialize watch_handler if not provided
if watch_handler is None:
    from utils.watch_handler import WatchHandler
    watch_handler = WatchHandler(Path.cwd())
```

### 5. API Endpoints (`routes/files.py`)

**Before**: Some endpoints ignored watch patterns  
**After**: ALL endpoints enforce watch filtering

- `/api/files/diffs` - ✅ Strict filtering
- `/api/files/watched` - ✅ Strict filtering  
- All other endpoints - ✅ Strict filtering

### 6. AI/Agent Queries

All AI/agent features now respect watch filtering:
- Session Summary updates
- Time-based queries
- Comprehensive analysis
- Batch processing

## Database Cleanup

### Remove Unwatched Files

If unwatched files are already in your database, use these endpoints:

**Clear unwatched file diffs:**
```bash
POST /api/files/clear-unwatched
```

**Clear diffs for non-existent files:**
```bash
POST /api/files/clear-missing
```

Both endpoints include audit logging showing which files were removed.

## Migration Guide

### Step 1: Review Your `.obbywatch` File

Ensure your `.obbywatch` file contains the patterns you want:

```bash
# Example - watch only notes directory
notes/
```

### Step 2: Check Current Tracking

View currently tracked files:
```bash
GET /api/files/watched
```

### Step 3: Clean Up Unwatched Data

Remove any unwatched files from the database:
```bash
POST /api/files/clear-unwatched
```

### Step 4: Verify System Behavior

Check logs for any watch filter rejections:
```
[DEBUG] Rejecting file change for path/to/file.md (not in watch patterns)
```

## Troubleshooting

### No Files Being Tracked

**Symptom**: Monitor starts but no files are detected

**Cause**: Empty or missing `.obbywatch` file

**Solution**: Add watch patterns to `.obbywatch`:
```
notes/
*.md
```

### Some Files Not Tracked

**Symptom**: Some files in watched directories are ignored

**Possible causes**:
1. File matches `.obbyignore` pattern
2. File doesn't match `.obbywatch` pattern
3. File is outside watched directory

**Solution**: Check both `.obbywatch` and `.obbyignore` configurations

### File Watcher Won't Start

**Symptom**: Error "No watch directories specified"

**Cause**: `.obbywatch` has no valid directory patterns

**Solution**: Add at least one directory pattern:
```
notes/
```

## Security Implications

The strict watch filtering provides security benefits:

1. **Data Isolation**: Only intended files are processed by AI
2. **Privacy Protection**: Prevents accidental tracking of sensitive files
3. **Scope Control**: Limits agent interactions to defined boundaries
4. **Audit Trail**: Logs when unwatched files are filtered out

## Testing the Fix

### Verify Strict Mode

1. Create test file OUTSIDE watched directory:
   ```bash
   echo "test" > test_unwatched.md
   ```

2. Check it's NOT in tracked files:
   ```bash
   GET /api/files/watched
   # Should NOT include test_unwatched.md
   ```

3. Verify database queries exclude it:
   ```bash
   GET /api/files/diffs
   # Should NOT show diffs for test_unwatched.md
   ```

### Verify Watch Filtering

1. Create test file INSIDE watched directory:
   ```bash
   echo "test" > notes/test_watched.md
   ```

2. Verify it IS tracked:
   ```bash
   GET /api/files/watched
   # Should include notes/test_watched.md
   ```

## Best Practices

1. **Keep `.obbywatch` Specific**: Only watch directories you need
2. **Use `.obbyignore` Liberally**: Exclude temp files, builds, etc.
3. **Regular Cleanup**: Periodically run cleanup endpoints
4. **Monitor Logs**: Watch for unexpected filter rejections
5. **Test After Changes**: Verify watch patterns after modifying `.obbywatch`

## Related Files

- `.obbywatch` - Define watch patterns
- `.obbyignore` - Define ignore patterns  
- `utils/watch_handler.py` - Watch pattern logic
- `utils/ignore_handler.py` - Ignore pattern logic
- `core/file_tracker.py` - File tracking with filtering
- `database/queries.py` - Query methods with filtering
- `routes/files.py` - API endpoints with filtering

## Summary

The watch filtering system now operates in **STRICT MODE** by default:

✅ Only explicitly watched files are tracked  
✅ Empty patterns = watch nothing (fail-safe)  
✅ All query paths enforce filtering  
✅ AI/agents respect watch boundaries  
✅ Audit logging for transparency  

This ensures complete control over which files are monitored and processed.