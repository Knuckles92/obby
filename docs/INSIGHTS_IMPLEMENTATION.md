# Insights Implementation Documentation

## Overview

This document describes the implementation of the Aggregated Insights feature for the Obby project. The insights system provides AI-powered analysis of project data, generating contextual observations about code quality, development velocity, risks, and other important metrics.

## Architecture

### Backend Components

#### 1. Database Schema (`database/schema.sql`)

```sql
CREATE TABLE insights (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL CHECK(category IN ('action', 'pattern', 'relationship', 'temporal', 'opportunity', 'quality', 'velocity', 'risk', 'documentation', 'follow-ups')),
    priority TEXT NOT NULL CHECK(priority IN ('low', 'medium', 'high', 'critical')),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    related_files TEXT, -- JSON array
    evidence TEXT, -- JSON object
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    dismissed BOOLEAN DEFAULT FALSE,
    archived BOOLEAN DEFAULT FALSE,
    source_section TEXT, -- Source of the insight
    source_pointers TEXT, -- JSON array of source references
    generated_by_agent TEXT, -- Agent that generated the insight
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### 2. Data Models (`database/models.py`)

- **InsightModel**: SQLAlchemy model for insights table
- **InsightRecord**: Pydantic model for data validation and serialization

#### 3. Insights Aggregator (`services/insights_aggregator.py`)

The aggregator collects signals from multiple data sources:

- **Semantic Analysis**: `semantic_entries`, `semantic_topics`, `semantic_keywords`
- **File Activity**: `FileVersionModel`, `ContentDiffModel`, `FileChangeModel`
- **Comprehensive Summaries**: `services/comprehensive_summary_service.py`
- **Session Summaries**: `SessionSummaryService`
- **Chat Transcripts**: AI conversation data

Key features:
- Respects watch filtering via `WatchHandler`
- Configurable via `INSIGHTS_*` settings in `config/settings.py`
- Supports both Claude Agent SDK and OpenAI for analysis
- Implements retry logic and timeout handling

#### 4. Insights Service (`services/insights_service.py`)

Provides high-level API for insights operations:

- `get_insights()`: Retrieve filtered insights
- `get_insight_by_id()`: Get specific insight details
- `dismiss_insight()`: Mark insight as dismissed
- `archive_insight()`: Archive insight
- `refresh_insights()`: Force regeneration
- `get_insights_stats()`: Get statistics

#### 5. API Routes (`routes/insights.py`)

RESTful endpoints for insights:

- `GET /api/insights/`: List insights with filters
- `GET /api/insights/{insight_id}`: Get insight details
- `POST /api/insights/{insight_id}/dismiss`: Dismiss insight
- `POST /api/insights/{insight_id}/archive`: Archive insight
- `POST /api/insights/refresh`: Refresh insights
- `GET /api/insights/stats`: Get statistics

### Frontend Components

#### 1. Insights Page (`frontend/src/pages/Insights.tsx`)

Main page component that:
- Fetches and displays insights
- Handles filtering and pagination
- Manages insight state (dismiss/archive)
- Integrates with theme system

#### 2. InsightFilters Component (`frontend/src/components/insights/InsightFilters.tsx`)

Filter controls for:
- Category selection
- Priority filtering
- Time range selection
- Include dismissed toggle

#### 3. InsightEvidence Component (`frontend/src/components/insights/InsightEvidence.tsx`)

Displays detailed evidence for insights:
- Reasoning and data points
- Source pointers
- Analysis scope metrics
- Most active files
- Agent provenance

## Data Flow

1. **Data Collection**: Aggregator collects signals from various sources
2. **AI Analysis**: Claude Agent SDK analyzes collected data
3. **Insight Generation**: Structured insights are created and stored
4. **API Exposure**: Insights are available via REST endpoints
5. **Frontend Display**: React components render insights with filtering

## Configuration

### Backend Settings (`config/settings.py`)

```python
INSIGHTS_ENABLED = True
INSIGHTS_AUTO_REFRESH = True
INSIGHTS_REFRESH_INTERVAL = 3600  # 1 hour
INSIGHTS_MAX_INSIGHTS = 50
INSIGHTS_DEFAULT_TIME_RANGE = 7  # days
INSIGHTS_AGENT_MODEL = "claude-sonnet"
INSIGHTS_RETRY_ATTEMPTS = 3
INSIGHTS_TIMEOUT = 30  # seconds
```

### Watch Filtering

The system respects strict watch filtering:
- Only processes files/directories in `.obbywatch`
- Unwatched paths are never included in insights
- Database queries automatically filter by watch patterns

## AI Integration

### Claude Agent SDK

Used for deep analysis and insight generation:
- Autonomous file exploration
- Structured output format
- Source provenance tracking
- Configurable model selection (haiku, sonnet, opus)

### OpenAI Integration

Optional for conversational features:
- Chat interactions
- Monitoring analysis
- Configuration assistance

## Testing

### Backend Tests (`tests/test_services/test_insights_service.py`)

Comprehensive test suite covering:
- Insight retrieval and filtering
- Dismissal and archival operations
- Error handling
- Watch filtering
- Data validation

### Frontend Tests (`frontend/src/__tests__/components/insights.test.tsx`)

Component testing for:
- Filter interactions
- Evidence display
- Theme integration
- User interactions

## Security Considerations

1. **Watch Filtering**: Strict enforcement prevents unauthorized file access
2. **Input Validation**: All user inputs are validated
3. **Rate Limiting**: API endpoints implement appropriate limits
4. **Data Sanitization**: AI outputs are sanitized before storage

## Performance Optimizations

1. **Caching**: Insights are cached per time window
2. **Lazy Loading**: Large datasets are paginated
3. **Background Processing**: Heavy AI operations run asynchronously
4. **Database Indexing**: Optimized queries with proper indexes

## Monitoring and Observability

1. **Logging**: Detailed logging for all operations
2. **Metrics**: Performance and usage metrics
3. **Error Tracking**: Comprehensive error reporting
4. **Health Checks**: Service health monitoring

## Migration Guide

### Database Migration

1. Run the insights table migration:
```sql
-- See database/migration_insights.sql
```

2. Update configuration:
```python
# Add to config/settings.py
INSIGHTS_ENABLED = True
```

3. Restart backend service

### Frontend Migration

1. Update dependencies (if any)
2. Build and deploy frontend
3. Clear browser cache

## Troubleshooting

### Common Issues

1. **No Insights Generated**
   - Check `.obbywatch` configuration
   - Verify API keys are set
   - Check watch filtering settings

2. **Performance Issues**
   - Reduce time range
   - Lower max insights limit
   - Check database indexes

3. **AI Errors**
   - Verify API key configuration
   - Check network connectivity
   - Review rate limits

### Debug Commands

```python
# Check insights service status
python -c "from services.insights_service import InsightsService; print(InsightsService().health_check())"

# Test aggregator
python -c "from services.insights_aggregator import InsightsAggregator; print(InsightsAggregator().test_connection())"
```

## Future Enhancements

1. **Real-time Updates**: SSE integration for live insights
2. **Custom Categories**: User-defined insight categories
3. **Export Features**: Insight export in various formats
4. **Integration Points**: External tool integrations
5. **Advanced Filtering**: More sophisticated filtering options

## API Reference

### GET /api/insights/

Query Parameters:
- `time_range_days`: Number of days to look back (default: 7)
- `max_insights`: Maximum insights to return (default: 20)
- `category`: Filter by category
- `priority`: Filter by priority
- `source_section`: Filter by source section
- `include_dismissed`: Include dismissed insights (default: false)

Response:
```json
{
  "success": true,
  "data": [...],
  "metadata": {
    "time_range_days": 7,
    "max_insights": 20,
    "generated_at": "2023-12-01T10:00:00Z",
    "total_insights": 15
  }
}
```

### POST /api/insights/refresh

Request Body:
```json
{
  "time_range_days": 7,
  "max_insights": 20,
  "force_refresh": true,
  "agent_model": "claude-sonnet"
}
```

## Contributing

When contributing to the insights system:

1. Follow the existing code patterns
2. Add comprehensive tests
3. Update documentation
4. Respect watch filtering
5. Include source provenance
6. Handle errors gracefully
7. Consider performance implications