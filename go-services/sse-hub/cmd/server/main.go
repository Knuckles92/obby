package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"sync"
	"syscall"

	"github.com/obby/sse-hub/internal/hub"
	"github.com/obby/sse-hub/internal/server"
)

func main() {
	// Parse command line flags
	var (
		grpcPort = flag.Int("grpc-port", 50054, "Port for gRPC server")
		httpPort = flag.Int("http-port", 8080, "Port for HTTP server")
	)
	flag.Parse()

	log.Printf("Starting SSE Hub Service")
	log.Printf("gRPC Port: %d, HTTP Port: %d", *grpcPort, *httpPort)

	// Create SSE hub
	sseHub := hub.NewSSEHub()

	// Start gRPC server in goroutine
	go func() {
		if err := server.StartGRPCServer(*grpcPort, sseHub); err != nil {
			log.Printf("gRPC server failed: %v", err)
		}
	}()

	// Start HTTP server in goroutine
	httpServer := server.NewHTTPServer(sseHub, *httpPort)
	go func() {
		if err := httpServer.Start(); err != nil && err != http.ErrServerClosed {
			log.Printf("HTTP server failed: %v", err)
		}
	}()

	// Wait for graceful shutdown
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	// Start hub in background
	go sseHub.Run(ctx)

	log.Printf("SSE Hub Service is running...")
	<-sigChan

	log.Printf("Shutting down SSE Hub Service...")
	
	// Stop both servers
	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		defer wg.Done()
		// Note: HTTP server shutdown would need proper context management
		// For now, we rely on OS signal handling
	}()

	// Wait for graceful shutdown
	wg.Wait()
	fmt.Println("SSE Hub Service stopped")
}