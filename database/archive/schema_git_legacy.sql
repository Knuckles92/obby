-- 🗄️ **GIT-NATIVE OBBY DATABASE SCHEMA**
-- Complete refactor for git-based change tracking
-- Eliminates custom diff system in favor of native git operations

-- Enable foreign key constraints and performance optimizations
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = 10000;

-- 📋 **GIT-FOCUSED CORE TABLES**

-- Git Commits: Central commit tracking
CREATE TABLE git_commits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    commit_hash TEXT UNIQUE NOT NULL,
    short_hash TEXT NOT NULL,
    author_name TEXT NOT NULL,
    author_email TEXT NOT NULL,
    message TEXT NOT NULL,
    branch_name TEXT,
    timestamp DATETIME NOT NULL,
    files_changed_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Git File Changes: Track file-level changes per commit
CREATE TABLE git_file_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    commit_id INTEGER NOT NULL REFERENCES git_commits(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    change_type TEXT NOT NULL CHECK (change_type IN ('added', 'modified', 'deleted', 'renamed', 'copied')),
    diff_content TEXT,
    lines_added INTEGER DEFAULT 0,
    lines_removed INTEGER DEFAULT 0,
    old_path TEXT,  -- For renames/moves
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Git Working Changes: Track uncommitted changes (staged + unstaged)
CREATE TABLE git_working_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT NOT NULL,
    change_type TEXT NOT NULL CHECK (change_type IN ('added', 'modified', 'deleted', 'renamed', 'untracked')),
    status TEXT NOT NULL CHECK (status IN ('staged', 'unstaged', 'untracked')),
    diff_content TEXT,
    timestamp DATETIME NOT NULL,
    branch_name TEXT,
    content_hash TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Git Repository State: Track overall repository information
CREATE TABLE git_repository_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    current_branch TEXT NOT NULL,
    head_commit TEXT NOT NULL,
    is_dirty BOOLEAN NOT NULL,
    staged_files_count INTEGER DEFAULT 0,
    unstaged_files_count INTEGER DEFAULT 0,
    untracked_files_count INTEGER DEFAULT 0,
    timestamp DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Events: File system events (still needed for real-time monitoring)
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK (type IN ('created', 'modified', 'deleted', 'moved')),
    path TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    size INTEGER DEFAULT 0,
    git_status TEXT,  -- Git status when event occurred
    processed BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Semantic Entries: AI-powered change analysis (enhanced with git context)
CREATE TABLE semantic_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    commit_hash TEXT REFERENCES git_commits(commit_hash),
    timestamp DATETIME NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    type TEXT NOT NULL,
    summary TEXT NOT NULL,
    impact TEXT NOT NULL CHECK (impact IN ('minor', 'moderate', 'significant')),
    file_path TEXT NOT NULL,
    searchable_text TEXT NOT NULL,
    author_name TEXT,
    branch_name TEXT,
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
    git_branch TEXT,
    git_commit_range TEXT,  -- From commit to commit for session
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Living Note Entries: Individual living note entries
CREATE TABLE living_note_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES living_note_sessions(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    word_count INTEGER NOT NULL,
    timestamp DATETIME NOT NULL,
    git_context TEXT,  -- Associated git information
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- File States: Track file states for efficient change detection
CREATE TABLE file_states (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path TEXT UNIQUE NOT NULL,
    git_hash TEXT,  -- Git object hash
    last_modified DATETIME NOT NULL,
    line_count INTEGER NOT NULL,
    is_tracked BOOLEAN NOT NULL DEFAULT FALSE,
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

-- Git commits optimization
CREATE INDEX idx_git_commits_hash ON git_commits(commit_hash);
CREATE INDEX idx_git_commits_timestamp ON git_commits(timestamp DESC);
CREATE INDEX idx_git_commits_author ON git_commits(author_name);
CREATE INDEX idx_git_commits_branch ON git_commits(branch_name);

-- Git file changes optimization
CREATE INDEX idx_git_file_changes_commit ON git_file_changes(commit_id);
CREATE INDEX idx_git_file_changes_path ON git_file_changes(file_path);
CREATE INDEX idx_git_file_changes_type ON git_file_changes(change_type);

-- Git working changes optimization
CREATE INDEX idx_git_working_path ON git_working_changes(file_path);
CREATE INDEX idx_git_working_status ON git_working_changes(status);
CREATE INDEX idx_git_working_timestamp ON git_working_changes(timestamp DESC);

-- Repository state optimization
CREATE INDEX idx_git_repo_state_timestamp ON git_repository_state(timestamp DESC);

-- Events optimization  
CREATE INDEX idx_events_timestamp ON events(timestamp DESC);
CREATE INDEX idx_events_type ON events(type);
CREATE INDEX idx_events_path ON events(path);
CREATE INDEX idx_events_processed ON events(processed);

-- Semantic search optimization
CREATE INDEX idx_semantic_timestamp ON semantic_entries(timestamp DESC);
CREATE INDEX idx_semantic_commit ON semantic_entries(commit_hash);
CREATE INDEX idx_semantic_type ON semantic_entries(type);
CREATE INDEX idx_semantic_impact ON semantic_entries(impact);
CREATE INDEX idx_semantic_author ON semantic_entries(author_name);
CREATE INDEX idx_semantic_branch ON semantic_entries(branch_name);

-- Topics and keywords optimization
CREATE INDEX idx_topics_entry ON semantic_topics(entry_id);
CREATE INDEX idx_topics_topic ON semantic_topics(topic);
CREATE INDEX idx_keywords_entry ON semantic_keywords(entry_id);
CREATE INDEX idx_keywords_keyword ON semantic_keywords(keyword);

-- File states optimization
CREATE INDEX idx_file_states_path ON file_states(file_path);
CREATE INDEX idx_file_states_modified ON file_states(last_modified);
CREATE INDEX idx_file_states_tracked ON file_states(is_tracked);

-- 🔍 **FULL-TEXT SEARCH**

-- Enable FTS5 for semantic search
CREATE VIRTUAL TABLE semantic_search USING fts5(
    summary, 
    searchable_text,
    content='semantic_entries',
    content_rowid='id'
);

-- Enable FTS5 for git commit messages
CREATE VIRTUAL TABLE commit_search USING fts5(
    message,
    author_name,
    content='git_commits',
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

CREATE TRIGGER commit_search_insert AFTER INSERT ON git_commits BEGIN
    INSERT INTO commit_search(rowid, message, author_name) 
    VALUES (new.id, new.message, new.author_name);
END;

CREATE TRIGGER commit_search_delete AFTER DELETE ON git_commits BEGIN
    DELETE FROM commit_search WHERE rowid = old.id;
END;

CREATE TRIGGER commit_search_update AFTER UPDATE ON git_commits BEGIN
    DELETE FROM commit_search WHERE rowid = old.id;
    INSERT INTO commit_search(rowid, message, author_name) 
    VALUES (new.id, new.message, new.author_name);
END;

-- 📊 **GIT-NATIVE ANALYTICS VIEWS**

-- Daily commit statistics
CREATE VIEW daily_commit_stats AS
SELECT 
    DATE(timestamp) as date,
    COUNT(*) as commit_count,
    COUNT(DISTINCT author_name) as authors,
    COUNT(DISTINCT branch_name) as branches,
    SUM(files_changed_count) as total_files_changed
FROM git_commits 
GROUP BY DATE(timestamp)
ORDER BY date DESC;

-- File change frequency
CREATE VIEW file_change_frequency AS  
SELECT 
    file_path,
    COUNT(*) as change_count,
    COUNT(DISTINCT fc.commit_id) as commit_count,
    MAX(gc.timestamp) as last_changed,
    COUNT(DISTINCT gc.author_name) as authors
FROM git_file_changes fc
JOIN git_commits gc ON fc.commit_id = gc.id
GROUP BY file_path
ORDER BY change_count DESC;

-- Author activity
CREATE VIEW author_activity AS
SELECT 
    author_name,
    author_email,
    COUNT(*) as commit_count,
    COUNT(DISTINCT DATE(timestamp)) as active_days,
    MAX(timestamp) as last_commit,
    MIN(timestamp) as first_commit
FROM git_commits
GROUP BY author_name, author_email
ORDER BY commit_count DESC;

-- Recent git activity summary
CREATE VIEW recent_git_activity AS
SELECT 
    'commit' as type,
    commit_hash as identifier,
    author_name as actor,
    message as description,
    timestamp,
    branch_name as context
FROM git_commits
UNION ALL
SELECT 
    'working_change' as type,
    file_path as identifier,
    'system' as actor,
    change_type || ' (' || status || ')' as description,
    timestamp,
    branch_name as context
FROM git_working_changes
ORDER BY timestamp DESC
LIMIT 100;

-- 🛡️ **DATA INTEGRITY**

-- Ensure git hashes are valid format
CREATE TRIGGER validate_commit_hash 
BEFORE INSERT ON git_commits
WHEN length(NEW.commit_hash) != 40 OR NEW.commit_hash NOT GLOB '[0-9a-f]*'
BEGIN
    SELECT RAISE(ABORT, 'Invalid commit hash format');
END;

-- Ensure timestamps are valid
CREATE TRIGGER validate_timestamps_commits 
BEFORE INSERT ON git_commits
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

-- Update files_changed_count when file_changes are added
CREATE TRIGGER update_files_changed_count
AFTER INSERT ON git_file_changes
BEGIN
    UPDATE git_commits 
    SET files_changed_count = (
        SELECT COUNT(*) FROM git_file_changes WHERE commit_id = NEW.commit_id
    )
    WHERE id = NEW.commit_id;
END;

-- 📝 **DEFAULT CONFIGURATION**

INSERT INTO config_values (key, value, type, description) VALUES
('checkInterval', '20', 'int', 'File checking interval in seconds'),
('openaiModel', 'gpt-4.1-mini', 'str', 'Default OpenAI model for AI operations'),
('maxCommitHistory', '1000', 'int', 'Maximum number of commits to retain in database'),
('enableRealTimeUpdates', 'true', 'bool', 'Enable real-time WebSocket updates'),
('gitIntegrationEnabled', 'true', 'bool', 'Enable git-native change tracking'),
('dbVersion', '2.0.0-git', 'str', 'Database schema version');

-- 📋 **MIGRATION METADATA**

CREATE TABLE migration_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_name TEXT NOT NULL,
    executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    records_migrated INTEGER DEFAULT 0
);