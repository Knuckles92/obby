Integration Plan for Aggregated Insights
========================================

1. Inventory & Contracts  
   - Catalogue the data “sections” feeding Insights: session summaries (`routes/session_summary.py`, `services/session_summary_service.py`), summary notes (`routes/summary_note.py`, `services/summary_note_service.py`), comprehensive monitor outputs (`routes/monitoring.py`, `routes/monitoring_comp_helper.py`), file activity/metrics (`core/file_tracker.py`, `database/models.py`, `database/queries.py`), chat/agent transcripts (`routes/chat.py`, `ai/claude_agent_client.py`), and configuration/watch filters (`utils/watch_handler.py`, `config/settings.py`).  
   - Document the data fields each section exposes, their refresh cadence, and whether the data is persisted in SQLite (`database/schema.sql`) or computed on demand.  
   - Define canonical insight domains (quality, velocity, risk, documentation, follow-ups) so every section can map into consistent categories, priorities, and provenance metadata.

2. Domain Model & Persistence  
   - Define an `InsightRecord` structure storing category, priority, evidence payload, related entities, dismissal/archive flags, generated_by agent, and source pointers (file paths, summary IDs, timestamps).  
   - Extend `database/schema.sql` and `database/models.py` with an `InsightModel` for persisting generated insights, enabling caching per time window.  
   - Ensure strict watch filtering by reusing `WatchHandler` (`utils/watch_handler.py`) and `FileTracker` guards so unwatched paths never populate the insights table.  
   - Provide a migration script mirroring the existing `database/migration_*` pattern for deployments that need to apply the new table.

3. Aggregation & Agent Orchestration  
   - Implement `services/insights_aggregator.py` (or similar) to collect raw signals from:  
     • Semantic summaries (`semantic_entries`, `semantic_topics`, `semantic_keywords`).  
     • Recent file/version activity (`FileVersionModel`, `ContentDiffModel`, `FileChangeModel`).  
     • Monitoring/comprehensive summaries (`services/comprehensive_summary_service.py`).  
     • Session summary snapshots via `SessionSummaryService`.  
     • Chat/agent transcripts or queues if stored.  
   - Normalize signals into agent-friendly input (include provenance lists) and decide which agent to call: use `ClaudeAgentClient` for deep analysis, optional OpenAI client from `ai/ai_tooling.py` for conversational enrichment.  
   - Respect guardrails: retries, timeout budgets, per-section toggles sourced from `config/settings.py` (new `INSIGHTS_*` configuration block).

4. API Surface & Background Jobs  
   - Replace the mock generator in `services/insights_service.py` with the aggregator + agent orchestration, supporting synchronous fetch and async refresh (e.g., via background tasks in `core` or `asyncio.create_task`).  
   - Expand `routes/insights.py` to provide:  
     • Aggregated list endpoint with filters (category, priority, source_section, time_range, include_dismissed).  
     • Detail endpoint returning evidence, agent reasoning, and source provenance.  
     • Refresh trigger endpoint to force regeneration with optional agent selection.  
     • Stats endpoint populated from real metrics (counts per category/section, agent latency).  
   - Ensure every response surfaces “Sources” metadata required by the AI prompts while honoring `.obbywatch` boundaries.

5. Frontend Experience  
   - Refactor `frontend/src/pages/Insights.tsx` to consume the richer API: adopt the new schema, add per-section filters, show agent provenance badges, and support evidence/file link presentation.  
   - Introduce reusable UI components (e.g., `frontend/src/components/insights/InsightFilters.tsx`, `InsightEvidence.tsx`) to keep the page modular.  
   - Add user controls for agent refresh (manual “Re-run agent” button, auto-refresh indicators) and connect to SSE streams if the backend exposes real-time updates (reuse patterns from `SessionSummary.tsx` and `/api/session-summary/events`).

6. Validation & Observability  
   - Create backend unit tests in `tests/unit/test_insights_service.py` (mock agent responses) and integration tests exercising `/api/insights/` via the FastAPI test client (`test_insights_server.py`).  
   - Instrument logging around agent calls (duration, model used, sections included) and expose status via `/api/insights/stats/overview`.  
  - If feasible, add a frontend smoke test (Vitest/Cypress) asserting the Insights page renders categories after mocked API responses.

7. Rollout & Documentation  
   - Update developer docs (`README.md`, `docs/`) with configuration steps (API keys, feature flags), data flow diagrams, and troubleshooting for agent failures.  
   - Provide migration instructions for initializing the insights table and optional backfill from historical summaries.  
   - Roll out behind a feature flag in `config/settings.py`, enabling sections progressively, and monitor performance/latency before default activation.
