package hub

import (
	"context"
	"log"
	"sync"
	"time"
)

// Message represents an SSE message
type Message struct {
	Event string
	Topic string
	Data  string
}

// Client represents an SSE client connection
type Client struct {
	ID     string
	Hub    *SSEHub
	Send   chan Message
	Topics map[string]bool
	mu     sync.RWMutex
}

// SSEHub manages SSE client connections and broadcasting
type SSEHub struct {
	clients    map[string]*Client
	broadcast   chan Message
	register    chan *Client
	unregister  chan *Client
	mu          sync.RWMutex
}

// NewSSEHub creates a new SSE hub
func NewSSEHub() *SSEHub {
	return &SSEHub{
		clients:    make(map[string]*Client),
		broadcast:  make(chan Message, 100),
		register:   make(chan *Client),
		unregister: make(chan *Client),
	}
}

// NewClient creates a new client
func (h *SSEHub) NewClient(ctx context.Context) *Client {
	return &Client{
		ID:     generateClientID(),
		Hub:    h,
		Send:   make(chan Message, 256),
		Topics: make(map[string]bool),
	}
}

// Register registers a client
func (h *SSEHub) Register(client *Client) {
	h.register <- client
}

// Unregister unregisters a client
func (h *SSEHub) Unregister(client *Client) {
	h.unregister <- client
}

// Broadcast broadcasts a message to all subscribed clients
func (h *SSEHub) Broadcast(msg Message) {
	h.broadcast <- msg
}

// Run runs the hub's main loop
func (h *SSEHub) Run(ctx context.Context) {
	for {
		select {
		case client := <-h.register:
			h.mu.Lock()
			h.clients[client.ID] = client
			h.mu.Unlock()
			log.Printf("Client registered: %s (total: %d)", client.ID, len(h.clients))

		case client := <-h.unregister:
			h.mu.Lock()
			if _, exists := h.clients[client.ID]; exists {
				delete(h.clients, client.ID)
				close(client.Send)
			}
			h.mu.Unlock()
			log.Printf("Client unregistered: %s", client.ID)

		case message := <-h.broadcast:
			h.mu.RLock()
			for _, client := range h.clients {
				if client.IsSubscribed(message.Topic) {
					select {
					case client.Send <- message:
					default:
						// Client buffer full, disconnect slow client
						go h.unregisterClient(client)
					}
				}
			}
			h.mu.RUnlock()

		case <-ctx.Done():
			h.shutdown()
			return
		}
	}
}

// IsSubscribed checks if client is subscribed to a topic
func (c *Client) IsSubscribed(topic string) bool {
	c.mu.RLock()
	defer c.mu.RUnlock()

	// If no topics specified, subscribe to all
	if len(c.Topics) == 0 {
		return true
	}

	return c.Topics[topic]
}

// Subscribe subscribes client to a topic
func (c *Client) Subscribe(topic string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.Topics[topic] = true
}

// Unsubscribe unsubscribes client from a topic
func (c *Client) Unsubscribe(topic string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	delete(c.Topics, topic)
}

// ClientCount returns the number of active clients
func (h *SSEHub) ClientCount() int {
	h.mu.RLock()
	defer h.mu.RUnlock()
	return len(h.clients)
}

// unregisterClient unregisters a client (internal helper)
func (h *SSEHub) unregisterClient(client *Client) {
	h.unregister <- client
}

// shutdown gracefully shuts down the hub
func (h *SSEHub) shutdown() {
	h.mu.Lock()
	defer h.mu.Unlock()

	for _, client := range h.clients {
		close(client.Send)
	}
	h.clients = make(map[string]*Client)
}

// generateClientID generates a unique client ID
func generateClientID() string {
	return time.Now().Format("20060102150405") + "-" + randomString(8)
}

// randomString generates a random string
func randomString(length int) string {
	const charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
	b := make([]byte, length)
	for i := range b {
		b[i] = charset[time.Now().UnixNano()%int64(len(charset))]
	}
	return string(b)
}

