-- 🗄️ **FILE-BASED OBBY DATABASE SCHEMA**
-- Complete migration from git-based to pure file system monitoring
-- Uses watchdog events, file content hashing, and native diff generation

-- Enable foreign key constraints and performance optimizations
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = 10000;

-- 📋 **FILE-FOCUSED CORE TABLES**

-- File Versions: Store complete file snapshots with content
CREATE TABLE file_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    content TEXT,
    line_count INTEGER DEFAULT 0,
    timestamp DATETIME NOT NULL,
    change_description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(file_path, content_hash)
);

-- Content Diffs: Store differences between file versions
CREATE TABLE content_diffs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    old_version_id INTEGER REFERENCES file_versions(id) ON DELETE CASCADE,
    new_version_id INTEGER REFERENCES file_versions(id) ON DELETE CASCADE,
    change_type TEXT NOT NULL CHECK (change_type IN ('created', 'modified', 'deleted', 'moved')),
    diff_content TEXT,
    lines_added INTEGER DEFAULT 0,
    lines_removed INTEGER DEFAULT 0,
    timestamp DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- File Changes: Simple change event tracking
CREATE TABLE file_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    change_type TEXT NOT NULL CHECK (change_type IN ('created', 'modified', 'deleted', 'moved')),
    old_content_hash TEXT,
    new_content_hash TEXT,
    timestamp DATETIME NOT NULL,
    content_hash TEXT, -- For deduplication
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(content_hash)
);

-- Events: File system events (enhanced for pure file monitoring)
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK (type IN ('created', 'modified', 'deleted', 'moved')),
    path TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    size INTEGER DEFAULT 0,
    processed BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Semantic Entries: AI-powered change analysis (updated for file-based)
CREATE TABLE semantic_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id INTEGER REFERENCES file_versions(id) ON DELETE CASCADE,
    timestamp DATETIME NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    type TEXT NOT NULL,
    summary TEXT NOT NULL,
    impact TEXT NOT NULL CHECK (impact IN ('minor', 'moderate', 'significant')),
    file_path TEXT NOT NULL,
    searchable_text TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Semantic Topics: Normalized topic storage
CREATE TABLE semantic_topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL REFERENCES semantic_entries(id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    UNIQUE(entry_id, topic)
);

-- Semantic Keywords: Normalized keyword storage  
CREATE TABLE semantic_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_id INTEGER NOT NULL REFERENCES semantic_entries(id) ON DELETE CASCADE,
    keyword TEXT NOT NULL,
    UNIQUE(entry_id, keyword)
);

-- Configuration: System configuration storage
CREATE TABLE config_values (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('int', 'str', 'bool', 'json')),
    description TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Living Note Sessions: Versioned living note storage
CREATE TABLE living_note_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,
    focus TEXT,
    changes_count INTEGER DEFAULT 0,
    insights TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Living Note Entries: Individual living note entries
CREATE TABLE living_note_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES living_note_sessions(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    word_count INTEGER NOT NULL,
    timestamp DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- File States: Enhanced file state tracking with content hashing
CREATE TABLE file_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,
    content_hash TEXT,
    last_modified DATETIME NOT NULL,
    line_count INTEGER NOT NULL DEFAULT 0,
    file_size INTEGER DEFAULT 0,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Watch Patterns: Database-managed watch configuration
CREATE TABLE watch_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('include', 'exclude')),
    enabled BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 🔍 **PERFORMANCE INDEXES**

-- File versions optimization
CREATE INDEX idx_file_versions_path ON file_versions(file_path);
CREATE INDEX idx_file_versions_hash ON file_versions(content_hash);
CREATE INDEX idx_file_versions_timestamp ON file_versions(timestamp DESC);

-- Content diffs optimization  
CREATE INDEX idx_content_diffs_path ON content_diffs(file_path);
CREATE INDEX idx_content_diffs_old_version ON content_diffs(old_version_id);
CREATE INDEX idx_content_diffs_new_version ON content_diffs(new_version_id);
CREATE INDEX idx_content_diffs_timestamp ON content_diffs(timestamp DESC);

-- File changes optimization
CREATE INDEX idx_file_changes_path ON file_changes(file_path);
CREATE INDEX idx_file_changes_type ON file_changes(change_type);
CREATE INDEX idx_file_changes_timestamp ON file_changes(timestamp DESC);

-- Events optimization  
CREATE INDEX idx_events_timestamp ON events(timestamp DESC);
CREATE INDEX idx_events_type ON events(type);
CREATE INDEX idx_events_path ON events(path);
CREATE INDEX idx_events_processed ON events(processed);

-- Semantic search optimization
CREATE INDEX idx_semantic_timestamp ON semantic_entries(timestamp DESC);
CREATE INDEX idx_semantic_version ON semantic_entries(version_id);
CREATE INDEX idx_semantic_type ON semantic_entries(type);
CREATE INDEX idx_semantic_impact ON semantic_entries(impact);

-- Topics and keywords optimization
CREATE INDEX idx_topics_entry ON semantic_topics(entry_id);
CREATE INDEX idx_topics_topic ON semantic_topics(topic);
CREATE INDEX idx_keywords_entry ON semantic_keywords(entry_id);
CREATE INDEX idx_keywords_keyword ON semantic_keywords(keyword);

-- File states optimization
CREATE INDEX idx_file_states_path ON file_states(file_path);
CREATE INDEX idx_file_states_modified ON file_states(last_modified);
CREATE INDEX idx_file_states_hash ON file_states(content_hash);

-- 🔍 **FULL-TEXT SEARCH**

-- Enable FTS5 for semantic search
CREATE VIRTUAL TABLE semantic_search USING fts5(
    summary, 
    searchable_text,
    content='semantic_entries',
    content_rowid='id'
);

-- Triggers to maintain FTS indexes
CREATE TRIGGER semantic_search_insert AFTER INSERT ON semantic_entries BEGIN
    INSERT INTO semantic_search(rowid, summary, searchable_text) 
    VALUES (new.id, new.summary, new.searchable_text);
END;

CREATE TRIGGER semantic_search_delete AFTER DELETE ON semantic_entries BEGIN
    DELETE FROM semantic_search WHERE rowid = old.id;
END;

CREATE TRIGGER semantic_search_update AFTER UPDATE ON semantic_entries BEGIN
    DELETE FROM semantic_search WHERE rowid = old.id;
    INSERT INTO semantic_search(rowid, summary, searchable_text) 
    VALUES (new.id, new.summary, new.searchable_text);
END;

-- 📊 **FILE-BASED ANALYTICS VIEWS**

-- Daily file activity statistics
CREATE VIEW daily_file_stats AS
SELECT 
    DATE(timestamp) as date,
    COUNT(*) as change_count,
    COUNT(DISTINCT file_path) as files_affected,
    COUNT(DISTINCT change_type) as change_types
FROM file_changes 
GROUP BY DATE(timestamp)
ORDER BY date DESC;

-- File change frequency
CREATE VIEW file_change_frequency AS  
SELECT 
    file_path,
    COUNT(*) as change_count,
    MAX(timestamp) as last_changed,
    MIN(timestamp) as first_changed
FROM file_changes
GROUP BY file_path
ORDER BY change_count DESC;

-- Recent file activity summary
CREATE VIEW recent_file_activity AS
SELECT 
    'file_change' as type,
    file_path as identifier,
    change_type as action,
    'system' as actor,
    timestamp,
    NULL as context
FROM file_changes
UNION ALL
SELECT 
    'event' as type,
    path as identifier,
    type as action,
    'watchdog' as actor,
    timestamp,
    CAST(size AS TEXT) as context
FROM events
ORDER BY timestamp DESC
LIMIT 100;

-- 🛡️ **DATA INTEGRITY**

-- Ensure timestamps are valid
CREATE TRIGGER validate_timestamps_file_versions 
BEFORE INSERT ON file_versions
WHEN NEW.timestamp > datetime('now', '+1 day')
BEGIN
    SELECT RAISE(ABORT, 'Future timestamps not allowed');
END;

CREATE TRIGGER validate_timestamps_events
BEFORE INSERT ON events  
WHEN NEW.timestamp > datetime('now', '+1 day')
BEGIN
    SELECT RAISE(ABORT, 'Future timestamps not allowed');
END;

-- Ensure content hashes are valid format (64-char hex for SHA-256)
CREATE TRIGGER validate_content_hash 
BEFORE INSERT ON file_versions
WHEN length(NEW.content_hash) != 64 OR NEW.content_hash NOT GLOB '[0-9a-f]*'
BEGIN
    SELECT RAISE(ABORT, 'Invalid content hash format');
END;

-- 📝 **DEFAULT CONFIGURATION**

INSERT INTO config_values (key, value, type, description) VALUES
('checkInterval', '20', 'int', 'File checking interval in seconds'),
('openaiModel', 'gpt-4.1-mini', 'str', 'Default OpenAI model for AI operations'),
('maxFileVersions', '100', 'int', 'Maximum number of versions to retain per file'),
('enableRealTimeUpdates', 'true', 'bool', 'Enable real-time WebSocket updates'),
('fileMonitoringEnabled', 'true', 'bool', 'Enable file-based change tracking'),
('dbVersion', '3.0.0-file-based', 'str', 'Database schema version');

-- 📋 **MIGRATION METADATA**

CREATE TABLE migration_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_name TEXT NOT NULL,
    executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    records_migrated INTEGER DEFAULT 0
);