package main

import (
	"flag"
	"log"

	"github.com/obby/query-service/internal/database"
	"github.com/obby/query-service/internal/server"
)

func main() {
	// Parse command line flags
	var (
		port = flag.Int("port", 50053, "Port to listen on")
		dbPath = flag.String("db", "obby.db", "Path to SQLite database")
	)
	flag.Parse()

	log.Printf("Starting Query Service on port %d with database: %s", *port, *dbPath)

	// Initialize database
	db, err := database.NewDB(*dbPath)
	if err != nil {
		log.Fatalf("Failed to initialize database: %v", err)
	}
	defer db.Close()

	// Start gRPC server
	if err := server.StartServer(*port, db); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}