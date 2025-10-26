# Claude-Optimized Output Format Specification

## Overview

This document defines the new output format for all Claude-powered summary features in Obby. This format replaces the previous OpenAI-based format and is optimized for Claude's autonomous file exploration capabilities.

**Version**: 1.0
**Date**: October 2025
**Status**: Active

---

## Design Principles

1. **Provenance First**: Every summary must include a Sources section showing which files were examined
2. **Rich Metadata**: Leverage Claude's analytical capabilities for deeper insights
3. **Structured for Search**: All metadata must be easily indexable for semantic search
4. **Consistent Across Features**: Same format for session summaries, individual summaries, and comprehensive summaries
5. **Human-Readable**: Markdown-formatted for direct display in UI

---

## Session Summary Format

### Structure

```markdown
## [Session Title]

**Summary**: [1-3 concise sentences describing the key changes and their significance]

**Change Pattern**: [Pattern description - e.g., "Incremental feature development", "Refactoring", "Bug fixes", "Documentation updates"]

**Impact Assessment**:
- **Scope**: [local | moderate | widespread]
- **Complexity**: [simple | moderate | complex]
- **Risk Level**: [low | medium | high]

**Topics**: [comma-separated high-level themes, 3-7 items]

**Technical Keywords**: [comma-separated technical terms, 5-10 items]

**Relationships**: [Brief description of how changed files relate to each other, if applicable]

### Sources

- `path/to/file1.ext` — [One sentence explaining why this file was examined and what role it played in the changes]
- `path/to/file2.ext` — [One sentence explaining relevance]
- `path/to/file3.ext` — [One sentence explaining relevance]

### Proposed Questions

- [Specific, actionable question about the changes]
- [Another question helping user explore implications]
- [Optional third question if relevant]
```

### Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| **Session Title** | String | Yes | 3-7 words, Title Case, optional emoji prefix |
| **Summary** | String | Yes | 1-3 sentences capturing what changed and why it matters |
| **Change Pattern** | String | Yes | High-level characterization of the type of work done |
| **Impact Assessment** | Object | Yes | Structured assessment of change scope, complexity, and risk |
| **Topics** | String[] | Yes | 3-7 high-level themes (e.g., "Authentication", "API", "Testing") |
| **Technical Keywords** | String[] | Yes | 5-10 specific technical terms for search (e.g., "JWT", "async/await", "migration") |
| **Relationships** | String | Optional | How files relate to each other (e.g., "Config changes propagated to service layer and routes") |
| **Sources** | Array | Yes | Files examined with one-sentence rationales |
| **Proposed Questions** | String[] | Optional | 2-4 actionable follow-up questions |

### Example

```markdown
## 🔒 Authentication System Refactoring

**Summary**: Refactored JWT token handling across authentication middleware and user service to support refresh tokens. Updated API endpoints to accept new token format. Added comprehensive error handling for expired tokens.

**Change Pattern**: Security enhancement with architectural improvements

**Impact Assessment**:
- **Scope**: moderate (affects auth flow across 5 files)
- **Complexity**: moderate (new token lifecycle management)
- **Risk Level**: medium (authentication-critical code)

**Topics**: authentication, security, API, error-handling, middleware

**Technical Keywords**: JWT, refresh tokens, middleware, token expiration, error handling, authentication flow, session management

**Relationships**: Middleware changes coordinate with service layer updates; config changes enable new token features; route updates expose new endpoints to clients.

### Sources

- `auth/middleware.py` — Core authentication middleware updated to validate and refresh JWT tokens with new expiration logic
- `services/user_service.py` — User service extended with refresh token generation and validation methods
- `config/security.py` — Security configuration updated with refresh token TTL and secret key rotation settings
- `routes/auth.py` — Authentication routes modified to handle token refresh endpoint and return new token format
- `models/user.py` — User model extended with refresh_token_hash field for secure token storage

### Proposed Questions

- How should the frontend handle the transition to refresh tokens for existing users?
- What monitoring should be added to track token refresh patterns and detect anomalies?
- Should we add rate limiting to the token refresh endpoint to prevent abuse?
```

---

## Individual File Change Summary Format

For summaries of individual file changes (tree changes, specific diffs), use a simplified format:

```markdown
**File Change Summary**

**File**: `path/to/file.ext`

**Change Type**: [created | modified | deleted | moved | renamed]

**Summary**: [1-2 sentences describing the change]

**Topics**: [comma-separated themes]

**Keywords**: [comma-separated technical terms]

**Impact**: [brief | moderate | significant]

**Related Files**: [comma-separated paths of files that likely interact with this change]
```

---

## Comprehensive Summary Format

For comprehensive summaries covering a longer time period (e.g., daily summaries, weekly reviews):

```markdown
## [Time Period Summary Title]

**Period**: [Human-readable time range, e.g., "Last 24 hours", "October 23-26, 2025"]

**Overview**: [2-4 sentences providing high-level summary of all activity]

**Change Metrics**:
- **Files Modified**: [count]
- **Files Created**: [count]
- **Files Deleted**: [count]
- **Total Changes**: [count]

**Major Themes**: [Narrative description of 2-4 major development themes/storylines]

**Change Pattern**: [Overall characterization - e.g., "Feature sprint", "Maintenance mode", "Exploratory development"]

**Impact Assessment**:
- **Scope**: [local | moderate | widespread]
- **Complexity**: [simple | moderate | complex]
- **Risk Level**: [low | medium | high]

**Topics**: [comma-separated high-level themes, 5-10 items]

**Technical Keywords**: [comma-separated technical terms, 8-15 items]

**Key Files**: [3-5 most significant files with brief context]

**Architecture Insights**: [Optional: 1-2 sentences about architectural patterns or decisions evident in the changes]

### Sources

- `path/to/file1.ext` — [Rationale]
- `path/to/file2.ext` — [Rationale]
[... all examined files ...]

### Proposed Questions

- [Strategic question about overall direction]
- [Technical question about implementation choices]
- [Optional question about next steps or implications]
```

---

## Database Schema Considerations

### Semantic Metadata Storage

The following fields should be extracted and stored in the database for search and analysis:

```python
{
    "summary_text": str,  # Full markdown summary
    "session_title": str,  # Extracted title
    "topics": List[str],  # Parsed from Topics field
    "keywords": List[str],  # Parsed from Technical Keywords field
    "impact_scope": str,  # Values: "local", "moderate", "widespread"
    "impact_complexity": str,  # Values: "simple", "moderate", "complex"
    "impact_risk": str,  # Values: "low", "medium", "high"
    "change_pattern": str,  # Pattern description
    "file_sources": List[Dict],  # [{"path": str, "rationale": str}, ...]
    "proposed_questions": List[str],  # Extracted questions
    "relationships": str | None,  # Relationship description if present
    "metrics": Dict,  # Change metrics if present
    "timestamp": datetime,  # When summary was created
    "summary_type": str,  # "session", "file", "comprehensive"
}
```

### Migration Notes

When migrating from OpenAI format to Claude format:
- Existing `topics` and `keywords` fields map directly
- Old `impact` field ("brief"/"moderate"/"significant") can be mapped to new `impact_scope` as "local"/"moderate"/"widespread"
- Add default values for new fields: `impact_complexity="moderate"`, `impact_risk="low"`, `change_pattern="Code changes"`
- Parse Sources section from markdown if present

---

## Parsing Guidelines

### Extracting Structured Data

Use these regex patterns to parse Claude's markdown output:

```python
# Session title (first heading)
title_pattern = r'^##\s+(.+)$'

# Summary field
summary_pattern = r'\*\*Summary\*\*:\s*(.+?)(?=\n\n|\*\*|$)'

# Change pattern
pattern_pattern = r'\*\*Change Pattern\*\*:\s*(.+?)(?=\n\n|\*\*|$)'

# Impact assessment
scope_pattern = r'-\s+\*\*Scope\*\*:\s*(\w+)'
complexity_pattern = r'-\s+\*\*Complexity\*\*:\s*(\w+)'
risk_pattern = r'-\s+\*\*Risk Level\*\*:\s*(\w+)'

# Topics (comma-separated)
topics_pattern = r'\*\*Topics\*\*:\s*(.+?)(?=\n\n|\*\*|$)'

# Keywords (comma-separated)
keywords_pattern = r'\*\*Technical Keywords\*\*:\s*(.+?)(?=\n\n|\*\*|$)'

# Sources section (entire section)
sources_pattern = r'###\s+Sources\s*\n((?:-.+\n?)+)'

# Individual source entry
source_entry_pattern = r'-\s+`([^`]+)`\s+—\s+(.+)'

# Proposed questions
questions_pattern = r'###\s+Proposed Questions\s*\n((?:-.+\n?)+)'
```

### Fallback Handling

If Claude's output doesn't match the expected format:
1. Extract whatever fields are present
2. Use sensible defaults for missing fields:
   - `summary_text`: Use raw Claude output
   - `topics`: ["Code Changes"]
   - `keywords`: []
   - `impact_scope`: "moderate"
   - `impact_complexity`: "moderate"
   - `impact_risk`: "low"
   - `change_pattern`: "Code modifications"
3. Log a warning for format compliance issues
4. Store raw output separately for debugging

---

## Validation Rules

### Required Field Validation

All summaries must include:
- ✅ Summary (at least 10 characters)
- ✅ At least one topic
- ✅ Sources section with at least one file
- ✅ Valid impact scope value
- ✅ Valid complexity value
- ✅ Valid risk level value

### Quality Checks

- Topics should be 2-20 words each
- Keywords should be 2-40 characters each
- Summary should be 50-500 characters
- Sources rationales should be 10-150 characters each
- No duplicate topics or keywords
- No internal artifact files in sources (e.g., `semantic_index.json`)

---

## Claude Prompt Integration

### System Prompt Template

```
You are a technical code analyst for the Obby file monitoring system. Your role is to investigate file changes and produce structured summaries.

IMPORTANT INSTRUCTIONS:
1. Use the Read, Grep, and Glob tools to explore files autonomously
2. Focus on understanding WHAT changed and WHY it matters
3. Always follow the exact output format specified
4. Include a Sources section listing every file you examined
5. Be concise but insightful in your analysis

OUTPUT FORMAT:
[Insert specific format template based on summary type]

CRITICAL:
- Do not describe your analysis process
- Do not use phrases like "I'll analyze" or "Let me check"
- Respond directly with the formatted summary
- Always include the Sources section
```

### User Prompt Template

```
Analyze the following file changes from the past [TIME_RANGE]:

CHANGED FILES:
[List of file paths]

TIME PERIOD: [Timestamp range]

TASK: Investigate these files and produce a [SUMMARY_TYPE] summary following the exact format specified in your system prompt.

Use your tools (Read, Grep, Glob) to explore the files and understand the changes. Focus on substantive modifications and their implications.
```

---

## Migration Checklist

When implementing this format:

- [ ] Update `ai/claude_agent_client.py` with new prompt templates
- [ ] Update database schema with new fields
- [ ] Create migration script for existing summaries
- [ ] Update parsing functions in services
- [ ] Update frontend components to display new fields
- [ ] Update tests with new format examples
- [ ] Update API documentation
- [ ] Create example summaries for each type
- [ ] Validate with real API calls
- [ ] Update user documentation

---

## Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | October 2025 | Initial specification for Claude-optimized format |

---

## See Also

- `CLAUDE.md` - Project-wide Claude Code instructions
- `config/format.md` - Claude prompt templates (will be updated)
- `database/models.py` - Database schema definitions
- `services/session_summary_service.py` - Session summary implementation
