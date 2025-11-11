package watcher

import (
	"sync"
	"time"
)

// Debouncer implements channel-based debouncing for file events
type Debouncer struct {
	delay  time.Duration
	timers map[string]*time.Timer
	mu     sync.Mutex
}

// NewDebouncer creates a new debouncer with the specified delay
func NewDebouncer(delay time.Duration) *Debouncer {
	return &Debouncer{
		delay:  delay,
		timers: make(map[string]*time.Timer),
	}
}

// Process processes an event with debouncing
// If an event for the same key arrives within the delay window,
// the previous timer is cancelled and a new one is started
func (d *Debouncer) Process(key string, fn func()) {
	d.mu.Lock()
	defer d.mu.Unlock()

	// Cancel existing timer if present
	if timer, exists := d.timers[key]; exists {
		timer.Stop()
	}

	// Create new timer
	d.timers[key] = time.AfterFunc(d.delay, func() {
		fn()
		d.mu.Lock()
		delete(d.timers, key)
		d.mu.Unlock()
	})
}

// Stop stops all pending timers
func (d *Debouncer) Stop() {
	d.mu.Lock()
	defer d.mu.Unlock()

	for _, timer := range d.timers {
		timer.Stop()
	}
	d.timers = make(map[string]*time.Timer)
}

