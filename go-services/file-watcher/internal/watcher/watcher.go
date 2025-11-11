package watcher

import (
	"context"
	"log"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/fsnotify/fsnotify"
	"github.com/obby/file-watcher/internal/patterns"
)

// FileWatcher wraps fsnotify and provides debouncing and pattern matching
type FileWatcher struct {
	watcher   *fsnotify.Watcher
	debouncer *Debouncer
	matcher   *patterns.Matcher
	events    chan FileEvent
	errors    chan error
	mu        sync.RWMutex
	watching  map[string]bool
	ctx       context.Context
	cancel    context.CancelFunc
}

// NewFileWatcher creates a new file watcher
func NewFileWatcher(debounceMs int, matcher *patterns.Matcher) (*FileWatcher, error) {
	w, err := fsnotify.NewWatcher()
	if err != nil {
		return nil, err
	}

	ctx, cancel := context.WithCancel(context.Background())

	return &FileWatcher{
		watcher:   w,
		debouncer: NewDebouncer(time.Duration(debounceMs) * time.Millisecond),
		matcher:   matcher,
		events:    make(chan FileEvent, 1000),
		errors:    make(chan error, 10),
		watching:  make(map[string]bool),
		ctx:       ctx,
		cancel:    cancel,
	}, nil
}

// Start starts the file watcher
func (fw *FileWatcher) Start() error {
	go fw.processEvents()
	return nil
}

// Stop stops the file watcher
func (fw *FileWatcher) Stop() error {
	fw.cancel()
	fw.debouncer.Stop()
	err := fw.watcher.Close()
	close(fw.events)
	close(fw.errors)
	return err
}

// AddPath adds a path to watch
func (fw *FileWatcher) AddPath(path string) error {
	fw.mu.Lock()
	defer fw.mu.Unlock()

	// Normalize path
	absPath, err := filepath.Abs(path)
	if err != nil {
		return err
	}

	// Check if already watching
	if fw.watching[absPath] {
		return nil
	}

	// Add to watcher
	err = fw.watcher.Add(absPath)
	if err != nil {
		return err
	}

	fw.watching[absPath] = true
	log.Printf("Watching path: %s", absPath)

	// If it's a directory, add all subdirectories recursively
	info, err := os.Stat(absPath)
	if err == nil && info.IsDir() {
		return fw.addDirectoryRecursive(absPath)
	}

	return nil
}

// addDirectoryRecursive adds a directory and all subdirectories recursively
func (fw *FileWatcher) addDirectoryRecursive(dirPath string) error {
	return filepath.Walk(dirPath, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return nil // Skip errors
		}

		if info.IsDir() {
			// Check if should watch this directory
			if fw.matcher != nil && !fw.matcher.IsWatched(path) {
				return filepath.SkipDir
			}

			// Check if should ignore
			if fw.matcher != nil && fw.matcher.IsIgnored(path) {
				return filepath.SkipDir
			}

			// Add directory to watcher
			if !fw.watching[path] {
				if err := fw.watcher.Add(path); err != nil {
					log.Printf("Error adding directory %s: %v", path, err)
					return nil // Continue on error
				}
				fw.watching[path] = true
			}
		}

		return nil
	})
}

// RemovePath removes a path from watching
func (fw *FileWatcher) RemovePath(path string) error {
	fw.mu.Lock()
	defer fw.mu.Unlock()

	absPath, err := filepath.Abs(path)
	if err != nil {
		return err
	}

	if !fw.watching[absPath] {
		return nil
	}

	err = fw.watcher.Remove(absPath)
	if err != nil {
		return err
	}

	delete(fw.watching, absPath)
	return nil
}

// processEvents processes events from fsnotify
func (fw *FileWatcher) processEvents() {
	for {
		select {
		case event := <-fw.watcher.Events:
			fw.handleEvent(event)
		case err := <-fw.watcher.Errors:
			log.Printf("watcher error: %v", err)
			select {
			case fw.errors <- err:
			default:
			}
		case <-fw.ctx.Done():
			return
		}
	}
}

// handleEvent handles a single fsnotify event
func (fw *FileWatcher) handleEvent(event fsnotify.Event) {
	// Check if should process this event
	if !fw.shouldProcess(event.Name) {
		return
	}

	// Determine event type
	eventType := fw.determineEventType(event)

	// Debounce the event
	fw.debouncer.Process(event.Name, func() {
		fileEvent := FileEvent{
			Path:      event.Name,
			EventType: eventType,
			Timestamp: time.Now(),
		}

		// Handle rename events
		if event.Op&fsnotify.Rename == fsnotify.Rename {
			fileEvent.EventType = EventRenamed
			// Try to get old path from event (if available)
			// Note: fsnotify may not always provide old path
		}

		select {
		case fw.events <- fileEvent:
		case <-fw.ctx.Done():
			return
		default:
			log.Printf("Event channel full, dropping event: %s", event.Name)
		}
	})
}

// shouldProcess checks if an event should be processed based on patterns
func (fw *FileWatcher) shouldProcess(path string) bool {
	if fw.matcher == nil {
		return true
	}

	// Check ignore patterns first
	if fw.matcher.IsIgnored(path) {
		return false
	}

	// Check watch patterns (STRICT MODE)
	if !fw.matcher.IsWatched(path) {
		return false
	}

	return true
}

// determineEventType determines the event type from fsnotify event
func (fw *FileWatcher) determineEventType(event fsnotify.Event) string {
	// Check if file exists
	_, err := os.Stat(event.Name)
	exists := err == nil

	if event.Op&fsnotify.Create == fsnotify.Create {
		if exists {
			return EventCreated
		}
	}

	if event.Op&fsnotify.Write == fsnotify.Write {
		if exists {
			return EventModified
		}
	}

	if event.Op&fsnotify.Remove == fsnotify.Remove {
		return EventDeleted
	}

	if event.Op&fsnotify.Rename == fsnotify.Rename {
		return EventRenamed
	}

	// Default to modified
	return EventModified
}

// Events returns the events channel
func (fw *FileWatcher) Events() <-chan FileEvent {
	return fw.events
}

// Errors returns the errors channel
func (fw *FileWatcher) Errors() <-chan error {
	return fw.errors
}

// detectWSL detects if running in WSL
func detectWSL() bool {
	// Check for WSL indicators
	if _, err := os.Stat("/proc/version"); err == nil {
		data, err := os.ReadFile("/proc/version")
		if err == nil {
			return strings.Contains(strings.ToLower(string(data)), "microsoft")
		}
	}
	return false
}

// isDrvFsPath checks if a path is on DrvFS (Windows filesystem mounted in WSL)
func isDrvFsPath(path string) bool {
	// DrvFS paths typically start with /mnt/
	return strings.HasPrefix(path, "/mnt/")
}

