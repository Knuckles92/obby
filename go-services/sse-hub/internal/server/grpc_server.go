package server

import (
	"context"
	"fmt"
	"log"
	"net"
	"os"
	"os/signal"
	"syscall"

	"google.golang.org/grpc"
	"google.golang.org/grpc/reflection"

	pb "github.com/obby/sse-hub/proto/generated"
	"github.com/obby/sse-hub/internal/hub"
)

// SSEServiceServer implements the gRPC SSEService interface
type SSEServiceServer struct {
	pb.UnimplementedSSEServiceServer
	hub *hub.SSEHub
}

// NewSSEServiceServer creates a new SSE service server
func NewSSEServiceServer(hub *hub.SSEHub) *SSEServiceServer {
	return &SSEServiceServer{
		hub: hub,
	}
}

// Publish implements Publish RPC
func (s *SSEServiceServer) Publish(ctx context.Context, req *pb.PublishRequest) (*pb.PublishResponse, error) {
	log.Printf("Publish called - Event: %s, Topic: %s", req.GetEvent(), req.GetTopic())

	// Create SSE message
	msg := hub.Message{
		Event: req.GetEvent(),
		Topic: req.GetTopic(),
		Data:  req.GetData(),
	}

	// Broadcast to all subscribed clients
	s.hub.Broadcast(msg)

	// Return success response with client count
	clientCount := s.hub.ClientCount()
	log.Printf("Broadcasted to %d clients", clientCount)

	return &pb.PublishResponse{
		Success: true,
		Clients: int32(clientCount),
	}, nil
}

// RegisterClient implements RegisterClient RPC (streaming)
func (s *SSEServiceServer) RegisterClient(req *pb.ClientRequest, stream pb.SSEService_RegisterClientServer) error {
	log.Printf("RegisterClient called - Topics: %v", req.GetTopics())

	// Create new client
	client := s.hub.NewClient(stream.Context())

	// Subscribe to requested topics
	for _, topic := range req.GetTopics() {
		client.Subscribe(topic)
	}

	// Register client with hub
	s.hub.Register(client)

	// Set up cancellation for when stream is closed
	ctx := stream.Context()
	done := ctx.Done()

	// Stream messages to client
	for {
		select {
		case msg := <-client.Send:
			pbMsg := &pb.SSEMessage{
				Event: msg.Event,
				Topic: msg.Topic,
				Data:  msg.Data,
			}
			if err := stream.Send(pbMsg); err != nil {
				log.Printf("Error sending SSE message: %v", err)
				s.hub.Unregister(client)
				return err
			}
		case <-done:
			// Client disconnected
			s.hub.Unregister(client)
			log.Printf("Client disconnected from streaming: %s", client.ID)
			return nil
		}
	}
}

// StartGRPCServer starts the gRPC server
func StartGRPCServer(port int, hub *hub.SSEHub) error {
	lis, err := net.Listen("tcp", fmt.Sprintf(":%d", port))
	if err != nil {
		return fmt.Errorf("failed to listen on port %d: %w", port, err)
	}

	s := grpc.NewServer()
	pb.RegisterSSEServiceServer(s, NewSSEServiceServer(hub))

	// Enable reflection for development
	reflection.Register(s)

	log.Printf("SSE Hub gRPC server starting on port %d", port)

	// Graceful shutdown
	go func() {
		sigChan := make(chan os.Signal, 1)
		signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
		<-sigChan

		log.Println("Shutting down SSE Hub gRPC server...")
		s.GracefulStop()
	}()

	return s.Serve(lis)
}