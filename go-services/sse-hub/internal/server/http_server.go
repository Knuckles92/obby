package server

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	"github.com/obby/sse-hub/internal/hub"
)

// HTTPServer handles HTTP SSE connections from the frontend
type HTTPServer struct {
	hub   *hub.SSEHub
	mux   *http.ServeMux
	server *http.Server
}

// NewHTTPServer creates a new HTTP SSE server
func NewHTTPServer(hub *hub.SSEHub, port int) *HTTPServer {
	mux := http.NewServeMux()
	h := &HTTPServer{
		hub:   hub,
		mux:   mux,
		server: &http.Server{
			Addr:         fmt.Sprintf(":%d", port),
			Handler:      mux,
			ReadTimeout:  30 * time.Second,
			WriteTimeout: 30 * time.Second,
			IdleTimeout:  120 * time.Second,
		},
	}

	// Register routes
	mux.HandleFunc("/sse", h.handleSSE)
	mux.HandleFunc("/health", h.handleHealth)

	return h
}

// handleSSE handles Server-Sent Events connection
func (h *HTTPServer) handleSSE(w http.ResponseWriter, r *http.Request) {
	// Set SSE headers
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Headers", "Cache-Control")

	// Get topics from query parameters or request body
	topics := h.getTopicsFromRequest(r)

	// Create client
	client := h.hub.NewClient(r.Context())

	// Subscribe to requested topics
	for _, topic := range topics {
		client.Subscribe(topic)
	}

	// Register client
	h.hub.Register(client)

	log.Printf("New SSE connection - Client: %s, Topics: %v", client.ID, topics)

	// Set up connection close detection
	flusher, ok := w.(http.Flusher)
	if !ok {
		log.Printf("Connection does not support flushing")
		http.Error(w, "Streaming unsupported", http.StatusInternalServerError)
		return
	}

	// Send initial message
	fmt.Fprintf(w, "event: connected\ndata: %s\n\n", client.ID)
	flusher.Flush()

	// Keep connection alive and send messages
	pingTicker := time.NewTicker(30 * time.Second)
	defer pingTicker.Stop()

	for {
		select {
		case msg := <-client.Send:
			// Send SSE message
			data, err := json.Marshal(map[string]string{
				"event": msg.Event,
				"topic": msg.Topic,
				"data":  msg.Data,
			})
			if err != nil {
				log.Printf("Error marshaling SSE message: %v", err)
				continue
			}

			fmt.Fprintf(w, "event: %s\ndata: %s\n\n", msg.Event, string(data))
			flusher.Flush()

		case <-pingTicker.C:
			// Send ping to keep connection alive
			fmt.Fprintf(w, "event: ping\ndata: %s\n\n", time.Now().Format(time.RFC3339))
			flusher.Flush()

		case <-r.Context().Done():
			// Client disconnected
			log.Printf("SSE client disconnected: %s", client.ID)
			h.hub.Unregister(client)
			return
		}
	}
}

// handleHealth provides health check endpoint
func (h *HTTPServer) handleHealth(w http.ResponseWriter, r *http.Request) {
	response := map[string]interface{}{
		"status":    "healthy",
		"timestamp": time.Now().Unix(),
		"clients":   h.hub.ClientCount(),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// getTopicsFromRequest extracts topics from HTTP request
func (h *HTTPServer) getTopicsFromRequest(r *http.Request) []string {
	// Try query parameters first
	if topicsParam := r.URL.Query().Get("topics"); topicsParam != "" {
		return []string{topicsParam}
	}

	// Try request body
	if r.Method == http.MethodPost {
		var body map[string]interface{}
		if err := json.NewDecoder(r.Body).Decode(&body); err == nil {
			if topics, ok := body["topics"].([]interface{}); ok {
				topicsStr := make([]string, len(topics))
				for i, topic := range topics {
					if str, ok := topic.(string); ok {
						topicsStr[i] = str
					}
				}
				return topicsStr
			}
			if topic, ok := body["topic"].(string); ok {
				return []string{topic}
			}
		}
	}

	// Default to all topics
	return []string{"*"}
}

// Start starts the HTTP server
func (h *HTTPServer) Start() error {
	log.Printf("SSE Hub HTTP server starting on port %s", h.server.Addr)

	// Start hub in background
	hubCtx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go h.hub.Run(hubCtx)

	// Start HTTP server
	return h.server.ListenAndServe()
}

// Stop stops the HTTP server gracefully
func (h *HTTPServer) Stop(ctx context.Context) error {
	log.Printf("Shutting down SSE Hub HTTP server...")
	return h.server.Shutdown(ctx)
}