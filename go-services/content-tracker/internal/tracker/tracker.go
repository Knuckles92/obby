package tracker

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"hash"
	"io"
	"os"
	"sync"

	"github.com/obby/content-tracker/internal/database"
	"github.com/obby/content-tracker/internal/diff"
)

var hashPool = sync.Pool{
	New: func() interface{} {
		return sha256.New()
	},
}

// ContentTracker tracks file content changes
type ContentTracker struct {
	db         *database.DB
	diffGen    *diff.Generator
	workerPool *WorkerPool
}

// NewContentTracker creates a new content tracker
func NewContentTracker(dbPath string) (*ContentTracker, error) {
	db, err := database.NewDB(dbPath)
	if err != nil {
		return nil, err
	}

	return &ContentTracker{
		db:         db,
		diffGen:    diff.NewDiffGenerator(),
		workerPool: NewWorkerPool(10), // 10 concurrent workers
	}, nil
}

// CalculateHash calculates SHA-256 hash of file content with line ending normalization
func (ct *ContentTracker) CalculateHash(filePath string) (string, error) {
	// Open file with buffered reading
	f, err := os.Open(filePath)
	if err != nil {
		return "", err
	}
	defer f.Close()

	// Get hash instance from pool
	h := hashPool.Get().(hash.Hash)
	defer func() {
		h.Reset()
		hashPool.Put(h)
	}()

	// Read and normalize line endings on the fly
	buf := make([]byte, 32*1024) // 32KB buffer
	for {
		n, err := f.Read(buf)
		if n > 0 {
			// Normalize line endings: \r\n and \r → \n
			normalized := normalizeLineEndings(buf[:n], nil)
			h.Write(normalized)
		}
		if err == io.EOF {
			break
		}
		if err != nil {
			return "", err
		}
	}

	return hex.EncodeToString(h.Sum(nil)), nil
}

// normalizeLineEndings normalizes line endings in a buffer
func normalizeLineEndings(data []byte, lastByte *byte) []byte {
	if len(data) == 0 {
		return data
	}
	var result []byte
	start := 0

	for i := 0; i < len(data); i++ {
		if data[i] == '\r' {
			// Check if followed by \n
			if i+1 < len(data) && data[i+1] == '\n' {
				// \r\n -> \n
				result = append(result, data[start:i]...)
				result = append(result, '\n')
				i++ // Skip the \n
				start = i + 1
			} else {
				// \r -> \n
				result = append(result, data[start:i]...)
				result = append(result, '\n')
				start = i + 1
			}
		}
	}

	// Handle case where \r is at end of buffer
	if start < len(data) {
		result = append(result, data[start:]...)
	}

	return result
}

// ReadFile reads file content with line ending normalization
func (ct *ContentTracker) ReadFile(filePath string) (string, error) {
	data, err := os.ReadFile(filePath)
	if err != nil {
		return "", err
	}

	// Normalize line endings
	normalized := normalizeLineEndings(data, nil)
	return string(normalized), nil
}

// TrackChange tracks a file change
func (ct *ContentTracker) TrackChange(ctx context.Context, filePath string, changeType string, projectRoot string) (*TrackResult, error) {
	// Read file content
	content, err := ct.ReadFile(filePath)
	if err != nil {
		return &TrackResult{
			Success: false,
			Error:   err.Error(),
		}, nil
	}

	// Calculate hash
	hash, err := ct.CalculateHash(filePath)
	if err != nil {
		return &TrackResult{
			Success: false,
			Error:   err.Error(),
		}, nil
	}

	// Get file size
	info, err := os.Stat(filePath)
	if err != nil {
		return &TrackResult{
			Success: false,
			Error:   err.Error(),
		}, nil
	}
	fileSize := info.Size()

	// Get previous hash from database
	prevHash, prevVersionID, err := ct.db.GetPreviousHash(ctx, filePath)
	if err != nil {
		// Not an error if no previous version exists
		prevHash = ""
		prevVersionID = 0
	}

	// Check if content changed
	if prevHash == hash {
		return &TrackResult{
			Success:     true,
			ContentHash: hash,
			FileSize:    fileSize,
			VersionID:   prevVersionID,
		}, nil
	}

	// Store new version
	versionID, err := ct.db.InsertFileVersion(ctx, filePath, hash, content, fileSize)
	if err != nil {
		return &TrackResult{
			Success: false,
			Error:   err.Error(),
		}, nil
	}

	// Generate diff asynchronously if previous version exists
	if prevHash != "" && prevVersionID > 0 {
		go ct.GenerateDiffAsync(ctx, filePath, prevVersionID, versionID)
	}

	return &TrackResult{
		Success:     true,
		ContentHash: hash,
		FileSize:    fileSize,
		VersionID:   versionID,
	}, nil
}

// GenerateDiffAsync generates diff asynchronously
func (ct *ContentTracker) GenerateDiffAsync(ctx context.Context, filePath string, oldVersionID, newVersionID int64) {
	// Get old and new content
	oldContent, err := ct.db.GetFileVersionContent(ctx, oldVersionID)
	if err != nil {
		return
	}

	newContent, err := ct.db.GetFileVersionContent(ctx, newVersionID)
	if err != nil {
		return
	}

	// Generate diff
	diffContent, linesAdded, linesRemoved, err := ct.diffGen.GenerateUnifiedDiff(
		oldContent, newContent, filePath, filePath,
	)
	if err != nil {
		return
	}

	// Store diff in database
	ct.db.InsertDiff(ctx, filePath, oldVersionID, newVersionID, diffContent, linesAdded, linesRemoved)
}

// TrackResult represents the result of tracking a file change
type TrackResult struct {
	Success     bool
	Error       string
	ContentHash string
	FileSize    int64
	VersionID    int64
}

// StartWorkerPool starts the worker pool
func (ct *ContentTracker) StartWorkerPool() {
	if ct.workerPool != nil {
		ct.workerPool.Start()
	}
}

// Close closes the content tracker
func (ct *ContentTracker) Close() error {
	if ct.workerPool != nil {
		ct.workerPool.Stop()
	}
	return ct.db.Close()
}

