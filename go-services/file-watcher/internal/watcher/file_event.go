package watcher

import "time"

// FileEvent represents a file system event
type FileEvent struct {
	Path      string
	EventType string // created, modified, deleted, renamed
	Timestamp time.Time
	OldPath   string // for rename events
}

// EventType constants
const (
	EventCreated = "created"
	EventModified = "modified"
	EventDeleted = "deleted"
	EventRenamed = "renamed"
)

