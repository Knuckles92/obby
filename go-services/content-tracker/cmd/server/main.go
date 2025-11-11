package main

import (
	"fmt"
	"log"
	"net"
	"os"

	"github.com/obby/content-tracker/internal/server"
	"github.com/obby/content-tracker/internal/tracker"
	pb "github.com/obby/content-tracker/proto/generated"
	"google.golang.org/grpc"
)

func main() {
	// Get database path from environment or use default
	dbPath := os.Getenv("DB_PATH")
	if dbPath == "" {
		dbPath = "obby.db"
	}

	// Create content tracker
	ct, err := tracker.NewContentTracker(dbPath)
	if err != nil {
		log.Fatalf("Failed to create content tracker: %v", err)
	}
	defer ct.Close()

	// Start worker pool
	ct.StartWorkerPool()

	// Create gRPC server
	grpcServer := grpc.NewServer()

	// Register ContentTracker service
	contentTrackerServer := server.NewContentTrackerServer(ct)
	pb.RegisterContentTrackerServer(grpcServer, contentTrackerServer)

	// Get port from environment or use default
	port := 50052
	if portStr := os.Getenv("TRACKER_PORT"); portStr != "" {
		fmt.Sscanf(portStr, "%d", &port)
	}

	// Start listening
	lis, err := net.Listen("tcp", fmt.Sprintf(":%d", port))
	if err != nil {
		log.Fatalf("Failed to listen: %v", err)
	}

	log.Printf("Content Tracker Service listening on :%d", port)

	// Serve
	if err := grpcServer.Serve(lis); err != nil {
		log.Fatalf("Failed to serve: %v", err)
	}
}

