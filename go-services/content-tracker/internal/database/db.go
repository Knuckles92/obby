package database

import (
	"context"
	"database/sql"
	"time"

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
		return nil, err
	}

	// Configure connection pool
	conn.SetMaxOpenConns(25)
	conn.SetMaxIdleConns(5)
	conn.SetConnMaxLifetime(time.Hour)

	// Ensure tables exist (they should be created by Python backend)
	// We'll just verify connection works
	if err := conn.Ping(); err != nil {
		return nil, err
	}

	return &DB{conn: conn}, nil
}

// GetPreviousHash gets the previous hash and version ID for a file
func (db *DB) GetPreviousHash(ctx context.Context, filePath string) (string, int64, error) {
	query := `
		SELECT content_hash, id 
		FROM file_versions 
		WHERE file_path = ? 
		ORDER BY timestamp DESC 
		LIMIT 1
	`

	var hash string
	var versionID int64
	err := db.conn.QueryRowContext(ctx, query, filePath).Scan(&hash, &versionID)
	if err == sql.ErrNoRows {
		return "", 0, nil
	}
	if err != nil {
		return "", 0, err
	}

	return hash, versionID, nil
}

// InsertFileVersion inserts a new file version
func (db *DB) InsertFileVersion(ctx context.Context, filePath, hash, content string, size int64) (int64, error) {
	query := `
		INSERT INTO file_versions (file_path, content_hash, content, size, timestamp)
		VALUES (?, ?, ?, ?, ?)
	`

	result, err := db.conn.ExecContext(ctx, query, filePath, hash, content, size, time.Now().Unix())
	if err != nil {
		return 0, err
	}

	versionID, err := result.LastInsertId()
	if err != nil {
		return 0, err
	}

	return versionID, nil
}

// GetFileVersionContent gets the content of a file version
func (db *DB) GetFileVersionContent(ctx context.Context, versionID int64) (string, error) {
	query := `SELECT content FROM file_versions WHERE id = ?`

	var content string
	err := db.conn.QueryRowContext(ctx, query, versionID).Scan(&content)
	if err != nil {
		return "", err
	}

	return content, nil
}

// InsertDiff inserts a diff record
func (db *DB) InsertDiff(ctx context.Context, filePath string, oldVersionID, newVersionID int64, diffContent string, linesAdded, linesRemoved int) error {
	query := `
		INSERT INTO content_diffs (file_path, old_version_id, new_version_id, diff_content, lines_added, lines_removed, timestamp)
		VALUES (?, ?, ?, ?, ?, ?, ?)
	`

	_, err := db.conn.ExecContext(ctx, query, filePath, oldVersionID, newVersionID, diffContent, linesAdded, linesRemoved, time.Now().Unix())
	return err
}

// Close closes the database connection
func (db *DB) Close() error {
	return db.conn.Close()
}

