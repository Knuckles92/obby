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

	pb "github.com/obby/query-service/proto/generated"
	"github.com/obby/query-service/internal/database"
)

// QueryServiceServer implements the gRPC QueryService interface
type QueryServiceServer struct {
	pb.UnimplementedQueryServiceServer
	db *database.DB
}

// NewQueryServiceServer creates a new query service server
func NewQueryServiceServer(db *database.DB) *QueryServiceServer {
	return &QueryServiceServer{
		db: db,
	}
}

// GetRecentDiffs implements GetRecentDiffs RPC (streaming)
func (s *QueryServiceServer) GetRecentDiffs(req *pb.DiffQuery, stream pb.QueryService_GetRecentDiffsServer) error {
	log.Printf("GetRecentDiffs called with limit: %d", req.GetLimit())

	ctx := stream.Context()
	diffs, err := s.db.GetRecentDiffs(ctx, req.GetLimit())
	if err != nil {
		log.Printf("Error getting recent diffs: %v", err)
		return err
	}

	// Stream results
	for _, diff := range diffs {
		pbDiff := &pb.DiffRecord{
			Id:           diff.Id,
			FilePath:     diff.FilePath,
			ChangeType:   diff.ChangeType,
			DiffContent:  diff.DiffContent,
			LinesAdded:   int32(diff.LinesAdded),
			LinesRemoved: int32(diff.LinesRemoved),
			Timestamp:    diff.Timestamp,
			ContentHash:  diff.ContentHash,
			Size:         diff.Size,
		}
		if err := stream.Send(pbDiff); err != nil {
			log.Printf("Error streaming diff: %v", err)
			return err
		}
	}

	log.Printf("Streamed %d recent diffs", len(diffs))
	return nil
}

// GetDiffsSince implements GetDiffsSince RPC (streaming)
func (s *QueryServiceServer) GetDiffsSince(req *pb.SinceQuery, stream pb.QueryService_GetDiffsSinceServer) error {
	log.Printf("GetDiffsSince called with timestamp: %d, limit: %d", req.GetTimestamp(), req.GetLimit())

	ctx := stream.Context()
	diffs, err := s.db.GetDiffsSince(ctx, req.GetTimestamp(), req.GetLimit())
	if err != nil {
		log.Printf("Error getting diffs since: %v", err)
		return err
	}

	// Stream results
	for _, diff := range diffs {
		pbDiff := &pb.DiffRecord{
			Id:           diff.Id,
			FilePath:     diff.FilePath,
			ChangeType:   diff.ChangeType,
			DiffContent:  diff.DiffContent,
			LinesAdded:   int32(diff.LinesAdded),
			LinesRemoved: int32(diff.LinesRemoved),
			Timestamp:    diff.Timestamp,
			ContentHash:  diff.ContentHash,
			Size:         diff.Size,
		}
		if err := stream.Send(pbDiff); err != nil {
			log.Printf("Error streaming diff: %v", err)
			return err
		}
	}

	log.Printf("Streamed %d diffs since timestamp", len(diffs))
	return nil
}

// GetFileVersions implements GetFileVersions RPC (streaming)
func (s *QueryServiceServer) GetFileVersions(req *pb.FileQuery, stream pb.QueryService_GetFileVersionsServer) error {
	log.Printf("GetFileVersions called for path: %s, limit: %d", req.GetFilePath(), req.GetLimit())

	ctx := stream.Context()
	versions, err := s.db.GetFileVersions(ctx, req.GetFilePath(), req.GetLimit())
	if err != nil {
		log.Printf("Error getting file versions: %v", err)
		return err
	}

	// Stream results
	for _, version := range versions {
		pbVersion := &pb.FileVersion{
			Id:          version.Id,
			FilePath:    version.FilePath,
			ContentHash: version.ContentHash,
			Size:        version.Size,
			Timestamp:   version.Timestamp,
		}
		if err := stream.Send(pbVersion); err != nil {
			log.Printf("Error streaming file version: %v", err)
			return err
		}
	}

	log.Printf("Streamed %d file versions for %s", len(versions), req.GetFilePath())
	return nil
}

// SearchContent implements SearchContent RPC (streaming)
func (s *QueryServiceServer) SearchContent(req *pb.SearchQuery, stream pb.QueryService_SearchContentServer) error {
	log.Printf("SearchContent called with query: %s, limit: %d", req.GetQuery(), req.GetLimit())

	ctx := stream.Context()
	results, err := s.db.SearchContent(ctx, req.GetQuery(), req.GetLimit())
	if err != nil {
		log.Printf("Error searching content: %v", err)
		return err
	}

	// Stream results
	for _, result := range results {
		pbResult := &pb.SearchResult{
			FilePath:    result.FilePath,
			Content:     result.Content,
			Highlighted: result.Highlighted,
			Rank:        float32(result.Rank),
		}
		if err := stream.Send(pbResult); err != nil {
			log.Printf("Error streaming search result: %v", err)
			return err
		}
	}

	log.Printf("Streamed %d search results for query: %s", len(results), req.GetQuery())
	return nil
}

// GetTopicFiles implements GetTopicFiles RPC (streaming)
func (s *QueryServiceServer) GetTopicFiles(req *pb.TopicQuery, stream pb.QueryService_GetTopicFilesServer) error {
	log.Printf("GetTopicFiles called for topic: %s, limit: %d", req.GetTopic(), req.GetLimit())

	ctx := stream.Context()
	files, err := s.db.GetTopicFiles(ctx, req.GetTopic(), req.GetLimit())
	if err != nil {
		log.Printf("Error getting topic files: %v", err)
		return err
	}

	// Stream results
	for _, file := range files {
		pbFile := &pb.FileRecord{
			FilePath:     file.FilePath,
			LastModified: file.Timestamp,
			Size:         int64(file.LineCount), // Convert LineCount to Size for protobuf
		}
		if err := stream.Send(pbFile); err != nil {
			log.Printf("Error streaming topic file: %v", err)
			return err
		}
	}

	log.Printf("Streamed %d files for topic: %s", len(files), req.GetTopic())
	return nil
}

// GetTimeAnalysis implements GetTimeAnalysis RPC
func (s *QueryServiceServer) GetTimeAnalysis(ctx context.Context, req *pb.TimeQuery) (*pb.TimeAnalysisResult, error) {
	log.Printf("GetTimeAnalysis called with start: %d, end: %d", req.GetStartTimestamp(), req.GetEndTimestamp())

	result, err := s.db.GetTimeAnalysis(ctx, req.GetStartTimestamp(), req.GetEndTimestamp())
	if err != nil {
		log.Printf("Error getting time analysis: %v", err)
		return nil, err
	}

	// Convert to protobuf format
	pbResult := &pb.TimeAnalysisResult{
		TotalFilesChanged: result.TotalFilesChanged,
		TotalLinesAdded:   result.TotalLinesAdded,
		TotalLinesRemoved: result.TotalLinesRemoved,
		TopTopics:         result.TopTopics,
		TopKeywords:       result.TopKeywords,
	}

	log.Printf("Time analysis completed: %d changes", result.TotalFilesChanged)
	return pbResult, nil
}

// GetActivityStats implements GetActivityStats RPC
func (s *QueryServiceServer) GetActivityStats(ctx context.Context, req *pb.StatsQuery) (*pb.ActivityStats, error) {
	log.Printf("GetActivityStats called with start: %d, end: %d", req.GetStartTimestamp(), req.GetEndTimestamp())

	stats, err := s.db.GetActivityStats(ctx, req.GetStartTimestamp(), req.GetEndTimestamp())
	if err != nil {
		log.Printf("Error getting activity stats: %v", err)
		return nil, err
	}

	// Convert to protobuf format with proper type casting
	pbStats := &pb.ActivityStats{
		FilesChanged:      int64(stats.FilesChanged),
		TotalChanges:      int64(stats.TotalChanges),
		LinesAdded:        int64(stats.LinesAdded),
		LinesRemoved:      int64(stats.LinesRemoved),
		AvgChangesPerFile: stats.AvgChangesPerFile,
	}

	log.Printf("Activity stats completed: %d events", stats.TotalChanges)
	return pbStats, nil
}

// StartServer starts the gRPC server
func StartServer(port int, db *database.DB) error {
	lis, err := net.Listen("tcp", fmt.Sprintf(":%d", port))
	if err != nil {
		return fmt.Errorf("failed to listen on port %d: %w", port, err)
	}

	s := grpc.NewServer()
	pb.RegisterQueryServiceServer(s, NewQueryServiceServer(db))

	// Enable reflection for development
	reflection.Register(s)

	log.Printf("Query Service starting on port %d", port)

	// Graceful shutdown
	go func() {
		sigChan := make(chan os.Signal, 1)
		signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)
		<-sigChan

		log.Println("Shutting down Query Service...")
		s.GracefulStop()
	}()

	return s.Serve(lis)
}