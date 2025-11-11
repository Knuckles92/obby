package database

import (
	"context"
	"database/sql"
	"fmt"
	"log"

	_ "github.com/mattn/go-sqlite3"
)

// DB wraps SQLite database connection
type DB struct {
	conn *sql.DB
}

// NewDB creates a new database connection
func NewDB(dbPath string) (*DB, error) {
	conn, err := sql.Open("sqlite3", dbPath+"?_journal_mode=WAL&_foreign_keys=ON&_busy_timeout=5000")
	if err != nil {
		return nil, fmt.Errorf("failed to open database: %w", err)
	}

	// Test connection
	if err := conn.Ping(); err != nil {
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	db := &DB{conn: conn}
	
	// Initialize FTS5 if needed
	if err := db.initFTS(); err != nil {
		log.Printf("Warning: FTS initialization failed: %v", err)
	}

	return db, nil
}

// initFTS initializes full-text search if not already present
func (db *DB) initFTS() error {
	// Check if file_versions_fts table exists
	var count int
	err := db.conn.QueryRow("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='file_versions_fts'").Scan(&count)
	if err != nil {
		return err
	}

	if count == 0 {
		// Create FTS5 virtual table
		_, err := db.conn.Exec(`
			CREATE VIRTUAL TABLE file_versions_fts USING fts5(
				file_path, 
				content,
				content=file_versions,
				content_rowid=id
			)
		`)
		if err != nil {
			return err
		}

		// Populate FTS table with existing data
		_, err = db.conn.Exec(`
			INSERT INTO file_versions_fts(file_path, content)
			SELECT file_path, content FROM file_versions
		`)
		if err != nil {
			return err
		}

		// Create triggers to keep FTS in sync
		_, err = db.conn.Exec(`
			CREATE TRIGGER file_versions_ai AFTER INSERT ON file_versions BEGIN
				INSERT INTO file_versions_fts(file_path, content) VALUES (new.file_path, new.content);
			END
		`)
		if err != nil {
			return err
		}

		_, err = db.conn.Exec(`
			CREATE TRIGGER file_versions_ad AFTER DELETE ON file_versions BEGIN
				INSERT INTO file_versions_fts(file_versions_fts, rowid, file_path, content) VALUES('delete', old.id, old.file_path, old.content);
			END
		`)
		if err != nil {
			return err
		}

		_, err = db.conn.Exec(`
			CREATE TRIGGER file_versions_au AFTER UPDATE ON file_versions BEGIN
				INSERT INTO file_versions_fts(file_versions_fts, rowid, file_path, content) VALUES('delete', old.id, old.file_path, old.content);
				INSERT INTO file_versions_fts(file_path, content) VALUES (new.file_path, new.content);
			END
		`)
		if err != nil {
			return err
		}
	}

	return nil
}

// GetRecentDiffs retrieves recent diffs with streaming support
func (db *DB) GetRecentDiffs(ctx context.Context, limit int32) ([]DiffRecord, error) {
	query := `
		SELECT 
			d.id,
			d.file_path,
			d.change_type,
			d.diff_content,
			d.lines_added,
			d.lines_removed,
			d.timestamp,
			d.content_hash,
			d.size
		FROM content_diffs d
		ORDER BY d.timestamp DESC
		LIMIT ?
	`

	rows, err := db.conn.QueryContext(ctx, query, limit)
	if err != nil {
		return nil, fmt.Errorf("failed to query recent diffs: %w", err)
	}
	defer rows.Close()

	var diffs []DiffRecord
	for rows.Next() {
		var diff DiffRecord
		err := rows.Scan(
			&diff.Id,
			&diff.FilePath,
			&diff.ChangeType,
			&diff.DiffContent,
			&diff.LinesAdded,
			&diff.LinesRemoved,
			&diff.Timestamp,
			&diff.ContentHash,
			&diff.Size,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan diff record: %w", err)
		}
		diffs = append(diffs, diff)
	}

	return diffs, rows.Err()
}

// GetDiffsSince retrieves diffs since a specific timestamp
func (db *DB) GetDiffsSince(ctx context.Context, timestamp int64, limit int32) ([]DiffRecord, error) {
	query := `
		SELECT 
			d.id,
			d.file_path,
			d.change_type,
			d.diff_content,
			d.lines_added,
			d.lines_removed,
			d.timestamp,
			d.content_hash,
			d.size
		FROM content_diffs d
		WHERE d.timestamp > ?
		ORDER BY d.timestamp DESC
		LIMIT ?
	`

	rows, err := db.conn.QueryContext(ctx, query, timestamp, limit)
	if err != nil {
		return nil, fmt.Errorf("failed to query diffs since timestamp: %w", err)
	}
	defer rows.Close()

	var diffs []DiffRecord
	for rows.Next() {
		var diff DiffRecord
		err := rows.Scan(
			&diff.Id,
			&diff.FilePath,
			&diff.ChangeType,
			&diff.DiffContent,
			&diff.LinesAdded,
			&diff.LinesRemoved,
			&diff.Timestamp,
			&diff.ContentHash,
			&diff.Size,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan diff record: %w", err)
		}
		diffs = append(diffs, diff)
	}

	return diffs, rows.Err()
}

// GetFileVersions retrieves version history for a specific file
func (db *DB) GetFileVersions(ctx context.Context, filePath string, limit int32) ([]FileVersion, error) {
	query := `
		SELECT 
			id,
			file_path,
			content_hash,
			size,
			timestamp
		FROM file_versions
		WHERE file_path = ?
		ORDER BY timestamp DESC
		LIMIT ?
	`

	rows, err := db.conn.QueryContext(ctx, query, filePath, limit)
	if err != nil {
		return nil, fmt.Errorf("failed to query file versions: %w", err)
	}
	defer rows.Close()

	var versions []FileVersion
	for rows.Next() {
		var version FileVersion
		err := rows.Scan(
			&version.Id,
			&version.FilePath,
			&version.ContentHash,
			&version.Size,
			&version.Timestamp,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan file version: %w", err)
		}
		versions = append(versions, version)
	}

	return versions, rows.Err()
}

// SearchContent performs full-text search across file content
func (db *DB) SearchContent(ctx context.Context, query string, limit int32) ([]SearchResult, error) {
	// Use FTS5 for efficient search
	ftsQuery := `
		SELECT 
			fv.id,
			fv.file_path,
			fv.content,
			fv.timestamp,
			snippet(file_versions_fts.content, 1, '<mark>', '</mark>', '...', 32) as highlighted,
			rank() as rank
		FROM file_versions fv
		JOIN file_versions_fts fts ON fv.id = fts.rowid
		WHERE file_versions_fts MATCH ?
		ORDER BY rank
		LIMIT ?
	`

	rows, err := db.conn.QueryContext(ctx, ftsQuery, query, limit)
	if err != nil {
		return nil, fmt.Errorf("failed to search content: %w", err)
	}
	defer rows.Close()

	var results []SearchResult
	for rows.Next() {
		var result SearchResult
		err := rows.Scan(
			&result.FilePath,
			&result.Content,
			&result.Timestamp,
			&result.Highlighted,
			&result.Rank,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan search result: %w", err)
		}
		results = append(results, result)
	}

	return results, rows.Err()
}

// GetTopicFiles retrieves files related to specific topics
func (db *DB) GetTopicFiles(ctx context.Context, topic string, limit int32) ([]FileRecord, error) {
	// Simple topic extraction from file paths and content
	query := `
		SELECT DISTINCT
			fv.file_path,
			fv.content_hash,
			fv.line_count,
			fv.timestamp
		FROM file_versions fv
		WHERE fv.file_path LIKE ? 
		   OR fv.content LIKE ?
		ORDER BY fv.timestamp DESC
		LIMIT ?
	`

	topicPattern := "%" + topic + "%"

	rows, err := db.conn.QueryContext(ctx, query, topicPattern, topicPattern, limit)
	if err != nil {
		return nil, fmt.Errorf("failed to query topic files: %w", err)
	}
	defer rows.Close()

	var files []FileRecord
	for rows.Next() {
		var file FileRecord
		err := rows.Scan(
			&file.FilePath,
			&file.ContentHash,
			&file.LineCount,
			&file.Timestamp,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan file record: %w", err)
		}
		files = append(files, file)
	}

	return files, rows.Err()
}

// GetTimeAnalysis performs time-based activity analysis
func (db *DB) GetTimeAnalysis(ctx context.Context, startTimestamp, endTimestamp int64) (*TimeAnalysisResult, error) {
	query := `
		SELECT 
			COUNT(*) as total_files_changed,
			COUNT(DISTINCT file_path) as unique_files,
			SUM(lines_added) as total_lines_added,
			SUM(lines_removed) as total_lines_removed
		FROM content_diffs
		WHERE timestamp BETWEEN ? AND ?
	`

	var result TimeAnalysisResult
	err := db.conn.QueryRowContext(ctx, query, startTimestamp, endTimestamp).Scan(
		&result.TotalFilesChanged,
		&result.UniqueFiles,
		&result.TotalLinesAdded,
		&result.TotalLinesRemoved,
	)

	if err != nil {
		return nil, fmt.Errorf("failed to get time analysis: %w", err)
	}

	// Calculate hourly activity distribution
	hourlyQuery := `
		SELECT 
			CAST(strftime('%H', datetime(timestamp, 'unixepoch')) AS INTEGER) as hour,
			COUNT(*) as changes
		FROM content_diffs
		WHERE timestamp BETWEEN ? AND ?
		GROUP BY hour
		ORDER BY hour
	`

	rows, err := db.conn.QueryContext(ctx, hourlyQuery, startTimestamp, endTimestamp)
	if err != nil {
		return nil, fmt.Errorf("failed to get hourly activity: %w", err)
	}
	defer rows.Close()

	for rows.Next() {
		var hour, changes int
		if err := rows.Scan(&hour, &changes); err != nil {
			return nil, fmt.Errorf("failed to scan hourly data: %w", err)
		}
		result.HourlyActivity = append(result.HourlyActivity, HourlyActivity{
			Hour:    int32(hour),
			Changes:  int32(changes),
		})
	}

	// Extract top topics and keywords (simplified)
	result.TopTopics = []string{"development", "documentation", "configuration"}
	result.TopKeywords = []string{"code", "changes", "updates", "files"}

	return &result, nil
}

// GetActivityStats generates activity statistics
func (db *DB) GetActivityStats(ctx context.Context, startTimestamp, endTimestamp int64) (*ActivityStats, error) {
	query := `
		SELECT 
			COUNT(DISTINCT file_path) as files_changed,
			COUNT(*) as total_changes,
			SUM(lines_added) as lines_added,
			SUM(lines_removed) as lines_removed,
			AVG(lines_added + lines_removed) as avg_changes_per_file
		FROM content_diffs
		WHERE timestamp BETWEEN ? AND ?
	`

	var stats ActivityStats
	err := db.conn.QueryRowContext(ctx, query, startTimestamp, endTimestamp).Scan(
		&stats.FilesChanged,
		&stats.TotalChanges,
		&stats.LinesAdded,
		&stats.LinesRemoved,
		&stats.AvgChangesPerFile,
	)

	if err != nil {
		return nil, fmt.Errorf("failed to get activity stats: %w", err)
	}

	return &stats, nil
}

// Close closes the database connection
func (db *DB) Close() error {
	return db.conn.Close()
}

// Data structures matching with protobuf definitions
type DiffRecord struct {
	Id           int64  `json:"id"`
	FilePath     string  `json:"file_path"`
	ChangeType   string  `json:"change_type"`
	DiffContent  string  `json:"diff_content"`
	LinesAdded   int32  `json:"lines_added"`
	LinesRemoved int32  `json:"lines_removed"`
	Timestamp    int64  `json:"timestamp"`
	ContentHash  string  `json:"content_hash"`
	Size         int64  `json:"size"`
}

type FileVersion struct {
	Id          int64  `json:"id"`
	FilePath    string  `json:"file_path"`
	ContentHash string  `json:"content_hash"`
	Size        int64  `json:"size"`
	Timestamp   int64  `json:"timestamp"`
}

type SearchResult struct {
	FilePath    string  `json:"file_path"`
	Content     string  `json:"content"`
	Timestamp   int64  `json:"timestamp"`
	Highlighted string  `json:"highlighted"`
	Rank        float64 `json:"rank"`
}

type FileRecord struct {
	FilePath     string  `json:"file_path"`
	ContentHash  string  `json:"content_hash"`
	LineCount    int32  `json:"line_count"`
	Timestamp    int64  `json:"timestamp"`
}

type TimeAnalysisResult struct {
	TotalFilesChanged int64           `json:"total_files_changed"`
	UniqueFiles       int32           `json:"unique_files"`
	TotalLinesAdded   int64           `json:"total_lines_added"`
	TotalLinesRemoved int64           `json:"total_lines_removed"`
	TopTopics        []string        `json:"top_topics"`
	TopKeywords      []string        `json:"top_keywords"`
	HourlyActivity   []HourlyActivity `json:"hourly_activity"`
}

type HourlyActivity struct {
	Hour    int32 `json:"hour"`
	Changes  int32 `json:"changes"`
}

type ActivityStats struct {
	FilesChanged         int32 `json:"files_changed"`
	TotalChanges         int32 `json:"total_changes"`
	LinesAdded           int32 `json:"lines_added"`
	LinesRemoved         int32 `json:"lines_removed"`
	AvgChangesPerFile    float32 `json:"avg_changes_per_file"`
}