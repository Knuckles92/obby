package main

import (
	"fmt"
	"log"
	"net"

	"github.com/obby/file-watcher/config"
	"github.com/obby/file-watcher/internal/patterns"
	"github.com/obby/file-watcher/internal/server"
	"github.com/obby/file-watcher/internal/watcher"
	pb "github.com/obby/file-watcher/proto/generated"
	"google.golang.org/grpc"
)

func main() {
	// Load configuration
	cfg := config.LoadConfig()

	// Create pattern matcher
	matcher := patterns.NewMatcher()

	// Create file watcher
	fw, err := watcher.NewFileWatcher(cfg.DebounceMs, matcher)
	if err != nil {
		log.Fatalf("Failed to create file watcher: %v", err)
	}
	defer fw.Stop()

	// Start watcher
	if err := fw.Start(); err != nil {
		log.Fatalf("Failed to start file watcher: %v", err)
	}

	// Create gRPC server
	grpcServer := grpc.NewServer()

	// Register FileWatcher service
	fileWatcherServer := server.NewFileWatcherServer(fw)
	pb.RegisterFileWatcherServer(grpcServer, fileWatcherServer)

	// Start listening
	lis, err := net.Listen("tcp", fmt.Sprintf(":%d", cfg.Port))
	if err != nil {
		log.Fatalf("Failed to listen: %v", err)
	}

	log.Printf("File Watcher Service listening on :%d", cfg.Port)

	// Serve
	if err := grpcServer.Serve(lis); err != nil {
		log.Fatalf("Failed to serve: %v", err)
	}
}

