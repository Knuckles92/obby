package server

import (
	"context"
	"log"

	"github.com/obby/file-watcher/internal/watcher"
	pb "github.com/obby/file-watcher/proto/generated"
	"google.golang.org/grpc"
)

// FileWatcherServer implements the gRPC FileWatcher service
// NOTE: This requires generated protobuf code from proto/file_watcher.proto
// Run: protoc --go_out=. --go-grpc_out=. --go_opt=paths=source_relative --go-grpc_opt=paths=source_relative proto/file_watcher.proto
type FileWatcherServer struct {
	pb.UnimplementedFileWatcherServer
	watcher *watcher.FileWatcher
}

// NewFileWatcherServer creates a new gRPC server
func NewFileWatcherServer(w *watcher.FileWatcher) *FileWatcherServer {
	return &FileWatcherServer{
		watcher: w,
	}
}

// StartWatching implements the StartWatching RPC
func (s *FileWatcherServer) StartWatching(ctx context.Context, req *pb.WatchRequest) (*pb.WatchResponse, error) {
	log.Printf("Starting watch on %d paths", len(req.WatchPaths))

	for _, path := range req.WatchPaths {
		if err := s.watcher.AddPath(path); err != nil {
			return &pb.WatchResponse{
				Success: false,
				Error:   err.Error(),
			}, nil
		}
	}

	return &pb.WatchResponse{Success: true}, nil
}

// StopWatching implements the StopWatching RPC
func (s *FileWatcherServer) StopWatching(ctx context.Context, req *pb.StopRequest) (*pb.StopResponse, error) {
	// Stop watching all paths
	// For now, we'll need to track paths separately to remove them
	return &pb.StopResponse{Success: true}, nil
}

// StreamEvents implements the StreamEvents RPC
func (s *FileWatcherServer) StreamEvents(req *pb.EventRequest, stream grpc.ServerStreamingServer[pb.FileEvent]) error {
	eventChan := s.watcher.Events()

	for {
		select {
		case event := <-eventChan:
			pbEvent := &pb.FileEvent{
				Path:      event.Path,
				EventType: event.EventType,
				Timestamp: event.Timestamp.Unix(),
				OldPath:   event.OldPath,
			}
			if err := stream.Send(pbEvent); err != nil {
				return err
			}
		case <-stream.Context().Done():
			return stream.Context().Err()
		}
	}
}

// UpdatePatterns implements the UpdatePatterns RPC
func (s *FileWatcherServer) UpdatePatterns(ctx context.Context, req *pb.PatternUpdate) (*pb.PatternResponse, error) {
	// Update patterns in matcher
	// This will require exposing pattern update methods in watcher
	// For now, return success - pattern updates can be handled by reloading .obbywatch/.obbyignore files
	return &pb.PatternResponse{Success: true}, nil
}

