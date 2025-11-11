package patterns

import (
	"path/filepath"
	"strings"
	"sync"

	"github.com/gobwas/glob"
)

// Matcher handles pattern matching for watch and ignore patterns
type Matcher struct {
	watchPatterns  []glob.Glob
	ignorePatterns []glob.Glob
	mu             sync.RWMutex
}

// NewMatcher creates a new pattern matcher
func NewMatcher() *Matcher {
	return &Matcher{
		watchPatterns:  make([]glob.Glob, 0),
		ignorePatterns: make([]glob.Glob, 0),
	}
}

// SetWatchPatterns sets the watch patterns
func (m *Matcher) SetWatchPatterns(patterns []string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	m.watchPatterns = make([]glob.Glob, 0, len(patterns))
	for _, pattern := range patterns {
		pattern = strings.TrimSpace(pattern)
		if pattern == "" || strings.HasPrefix(pattern, "#") {
			continue
		}

		// Normalize pattern: use forward slashes
		pattern = filepath.ToSlash(pattern)

		g, err := glob.Compile(pattern)
		if err != nil {
			return err
		}
		m.watchPatterns = append(m.watchPatterns, g)
	}

	return nil
}

// SetIgnorePatterns sets the ignore patterns
func (m *Matcher) SetIgnorePatterns(patterns []string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	m.ignorePatterns = make([]glob.Glob, 0, len(patterns))
	for _, pattern := range patterns {
		pattern = strings.TrimSpace(pattern)
		if pattern == "" || strings.HasPrefix(pattern, "#") {
			continue
		}

		// Normalize pattern: use forward slashes
		pattern = filepath.ToSlash(pattern)

		g, err := glob.Compile(pattern)
		if err != nil {
			return err
		}
		m.ignorePatterns = append(m.ignorePatterns, g)
	}

	return nil
}

// IsIgnored checks if a path matches any ignore pattern
func (m *Matcher) IsIgnored(path string) bool {
	m.mu.RLock()
	defer m.mu.RUnlock()

	// Normalize path: use forward slashes
	normalizedPath := filepath.ToSlash(path)

	// Check against ignore patterns
	for _, pattern := range m.ignorePatterns {
		if pattern.Match(normalizedPath) {
			return true
		}
		// Also check just the filename
		if pattern.Match(filepath.Base(normalizedPath)) {
			return true
		}
	}

	return false
}

// IsWatched checks if a path matches any watch pattern
// Returns false if no watch patterns are defined (STRICT MODE)
func (m *Matcher) IsWatched(path string) bool {
	m.mu.RLock()
	defer m.mu.RUnlock()

	// STRICT MODE: If no patterns specified, watch NOTHING
	if len(m.watchPatterns) == 0 {
		return false
	}

	// Normalize path: use forward slashes
	normalizedPath := filepath.ToSlash(path)

	// Check against watch patterns
	for _, pattern := range m.watchPatterns {
		if pattern.Match(normalizedPath) {
			return true
		}
		// Also check just the filename
		if pattern.Match(filepath.Base(normalizedPath)) {
			return true
		}
		// Check if path is inside a watched directory (for directory patterns ending with /)
		pathParts := strings.Split(normalizedPath, "/")
		for i := range pathParts {
			partialPath := strings.Join(pathParts[:i+1], "/") + "/"
			if pattern.Match(partialPath) {
				return true
			}
		}
	}

	return false
}

