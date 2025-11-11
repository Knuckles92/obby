package config

import (
	"os"
	"strconv"
)

// Config holds the configuration for the file watcher service
type Config struct {
	Port       int
	LogLevel   string
	DebounceMs int
}

// LoadConfig loads configuration from environment variables with defaults
func LoadConfig() *Config {
	port := 50051
	if portStr := os.Getenv("WATCHER_PORT"); portStr != "" {
		if p, err := strconv.Atoi(portStr); err == nil {
			port = p
		}
	}

	logLevel := "info"
	if ll := os.Getenv("LOG_LEVEL"); ll != "" {
		logLevel = ll
	}

	debounceMs := 500
	if dbStr := os.Getenv("DEBOUNCE_MS"); dbStr != "" {
		if db, err := strconv.Atoi(dbStr); err == nil {
			debounceMs = db
		}
	}

	return &Config{
		Port:       port,
		LogLevel:   logLevel,
		DebounceMs: debounceMs,
	}
}

