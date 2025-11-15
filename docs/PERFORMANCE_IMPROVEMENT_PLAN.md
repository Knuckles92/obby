# Dashboard Navigation Performance Improvement Plan

## Problem Analysis

When navigating to the dashboard, users experience slow load times. Analysis reveals several performance bottlenecks:

### Primary Bottlenecks

1. **`/api/monitor/status` endpoint** (CRITICAL)
   - Performs expensive file system operations on every request
   - Uses `rglob('*.md')` to recursively walk all watched directories
   - Applies watch/ignore filters for each file found
   - No caching mechanism
   - **Impact**: Can take 1-5+ seconds depending on directory size

2. **Database Query Performance**
   - `get_recent_diffs()` fetches all records then filters in Python
   - Watch filtering happens after database fetch (inefficient)
   - Missing indexes on frequently queried columns

3. **Frontend Loading Strategy**
   - Blocks UI rendering until all data loads
   - No progressive loading or skeleton states
   - Immediate polling (5s interval) can cause request queuing

## Performance Improvement Strategy

### Phase 1: Backend Optimizations (High Impact)

#### 1.1 Cache File Count in Monitor Status Endpoint
**Priority**: CRITICAL  
**Estimated Impact**: 80-90% reduction in response time

**Implementation**:
- Cache `total_files` count with TTL (10-30 seconds)
- Invalidate cache when:
  - Monitoring starts/stops
  - Files are added/removed from watch directories
  - Watch patterns change
- Use in-memory cache (dict with timestamp) or Redis if available

**Files to Modify**:
- `routes/monitoring.py` - Add caching logic to `get_status()`
- Create `utils/cache.py` for cache management

#### 1.2 Database Indexing
**Priority**: HIGH  
**Estimated Impact**: 30-50% faster queries

**Indexes to Add**:
```sql
CREATE INDEX IF NOT EXISTS idx_content_diffs_timestamp ON content_diffs(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_content_diffs_file_path ON content_diffs(file_path);
CREATE INDEX IF NOT EXISTS idx_events_timestamp_date ON events(DATE(timestamp));
```

**Files to Modify**:
- `database/migration_service_monitoring.py` - Add migration for indexes
- Or create new migration file

#### 1.3 Optimize Database Queries
**Priority**: HIGH  
**Estimated Impact**: 20-40% faster activity queries

**Changes**:
- Apply watch filtering at database level (if possible) or limit results before filtering
- Use `LIMIT` in SQL query before Python-side filtering
- Consider materialized view for frequently accessed data

**Files to Modify**:
- `database/queries.py` - Optimize `get_recent_diffs()`

#### 1.4 Response Caching with TTL
**Priority**: MEDIUM  
**Estimated Impact**: 50-70% reduction for repeated requests

**Implementation**:
- Cache `/api/monitor/status` response for 10-30 seconds
- Cache `/api/files/activity` response for 5-10 seconds
- Use FastAPI's built-in caching or custom decorator

**Files to Modify**:
- `routes/monitoring.py` - Add cache decorator
- `routes/files.py` - Add cache decorator

### Phase 2: Frontend Optimizations (User Experience)

#### 2.1 Progressive Loading
**Priority**: HIGH  
**Estimated Impact**: Perceived performance improvement (instant UI)

**Implementation**:
- Show skeleton UI immediately (don't wait for data)
- Load critical data first (status), then secondary data (activity)
- Use React Suspense or loading states per section

**Files to Modify**:
- `frontend/src/pages/Dashboard.tsx` - Implement progressive loading

#### 2.2 Request Debouncing
**Priority**: MEDIUM  
**Estimated Impact**: Prevents request queuing

**Implementation**:
- Prevent multiple simultaneous requests
- Debounce rapid navigation changes
- Cancel in-flight requests when component unmounts

**Files to Modify**:
- `frontend/src/pages/Dashboard.tsx` - Add request cancellation
- `frontend/src/utils/api.ts` - Add AbortController support

#### 2.3 Optimize Polling Strategy
**Priority**: LOW  
**Estimated Impact**: Reduced server load

**Implementation**:
- Increase polling interval when tab is inactive (use Page Visibility API)
- Pause polling when dashboard is not visible
- Use exponential backoff on errors

**Files to Modify**:
- `frontend/src/pages/Dashboard.tsx` - Smart polling logic

### Phase 3: Advanced Optimizations (Future)

#### 3.1 Background File Count Updates
- Update file count in background thread/process
- Store count in database or cache
- Only refresh on demand or periodic intervals

#### 3.2 Database Query Optimization
- Use database views for common queries
- Implement query result caching at database level
- Consider read replicas for heavy read operations

#### 3.3 Watch Handler Optimization
- Cache watch pattern compilation
- Batch file existence checks
- Use file system watchers to track count changes

## Implementation Priority

### Immediate (Week 1)
1. ✅ Cache file count in monitor status endpoint
2. ✅ Add database indexes
3. ✅ Implement progressive loading in frontend

### Short-term (Week 2)
4. ✅ Optimize database queries
5. ✅ Add response caching with TTL
6. ✅ Implement request debouncing

### Long-term (Future)
7. Background file count updates
8. Advanced caching strategies
9. Database query result caching

## Success Metrics

### Target Performance Goals
- **Initial Load**: < 500ms (from current 2-5s)
- **Status Endpoint**: < 100ms (from current 1-5s)
- **Activity Endpoint**: < 200ms (from current 300-800ms)
- **Time to Interactive**: < 1s (from current 2-5s)

### Measurement
- Add performance logging to endpoints
- Track response times in frontend
- Monitor database query execution times

## Testing Strategy

1. **Load Testing**: Test with large directories (1000+ files)
2. **Concurrent Requests**: Test multiple users accessing dashboard
3. **Cache Invalidation**: Verify cache updates correctly
4. **Error Handling**: Ensure graceful degradation when cache fails

## Rollout Plan

1. **Phase 1**: Backend optimizations (caching, indexing)
2. **Phase 2**: Frontend optimizations (progressive loading)
3. **Phase 3**: Monitor and measure improvements
4. **Phase 4**: Iterate based on metrics

## Notes

- All changes must maintain STRICT watch filtering mode
- Cache invalidation must be reliable
- Backward compatibility must be maintained
- Consider feature flags for gradual rollout


