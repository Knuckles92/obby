package server

import (
	"context"
	"os"

	"github.com/obby/content-tracker/internal/diff"
	"github.com/obby/content-tracker/internal/tracker"
	pb "github.com/obby/content-tracker/proto/generated"
	"google.golang.org/grpc"
)

// ContentTrackerServer implements the gRPC ContentTracker service
type ContentTrackerServer struct {
	pb.UnimplementedContentTrackerServer
	tracker *tracker.ContentTracker
}

// NewContentTrackerServer creates a new gRPC server
func NewContentTrackerServer(t *tracker.ContentTracker) *ContentTrackerServer {
	return &ContentTrackerServer{
		tracker: t,
	}
}

// TrackChange implements the TrackChange RPC
func (s *ContentTrackerServer) TrackChange(ctx context.Context, req *pb.TrackRequest) (*pb.TrackResponse, error) {
	result, err := s.tracker.TrackChange(ctx, req.FilePath, req.ChangeType, req.ProjectRoot)
	if err != nil {
		return &pb.TrackResponse{
			Success: false,
			Error:   err.Error(),
		}, nil
	}

	return &pb.TrackResponse{
		Success:     result.Success,
		Error:       result.Error,
		ContentHash: result.ContentHash,
		FileSize:    result.FileSize,
		VersionId:   result.VersionID,
	}, nil
}

// TrackBatch implements the TrackBatch RPC
func (s *ContentTrackerServer) TrackBatch(req *pb.BatchRequest, stream grpc.ServerStreamingServer[pb.TrackProgress]) error {
	for _, trackReq := range req.Requests {
		result, err := s.tracker.TrackChange(stream.Context(), trackReq.FilePath, trackReq.ChangeType, trackReq.ProjectRoot)
		if err != nil {
			stream.Send(&pb.TrackProgress{
				FilePath: trackReq.FilePath,
				Success:  false,
				Error:    err.Error(),
			})
			continue
		}

		stream.Send(&pb.TrackProgress{
			FilePath:    trackReq.FilePath,
			Success:     result.Success,
			Error:       result.Error,
			ContentHash: result.ContentHash,
			VersionId:   result.VersionID,
		})
	}

	return nil
}

// GetContentHash implements the GetContentHash RPC
func (s *ContentTrackerServer) GetContentHash(ctx context.Context, req *pb.HashRequest) (*pb.HashResponse, error) {
	hash, err := s.tracker.CalculateHash(req.FilePath)
	if err != nil {
		return &pb.HashResponse{
			Success: false,
			Error:   err.Error(),
		}, nil
	}

	info, err := os.Stat(req.FilePath)
	if err != nil {
		return &pb.HashResponse{
			Success: false,
			Error:   err.Error(),
		}, nil
	}

	return &pb.HashResponse{
		Success:     true,
		ContentHash: hash,
		FileSize:    info.Size(),
	}, nil
}

// GenerateDiff implements the GenerateDiff RPC
func (s *ContentTrackerServer) GenerateDiff(ctx context.Context, req *pb.DiffRequest) (*pb.DiffResponse, error) {
	// Use the diff package function
	diffContent, linesAdded, linesRemoved, err := diff.GenerateUnifiedDiff(
		req.OldContent, req.NewContent, req.OldFilePath, req.NewFilePath,
	)
	if err != nil {
		return &pb.DiffResponse{
			Success: false,
			Error:   err.Error(),
		}, nil
	}

	return &pb.DiffResponse{
		Success:      true,
		DiffContent:  diffContent,
		LinesAdded:   int32(linesAdded),
		LinesRemoved: int32(linesRemoved),
	}, nil
}

