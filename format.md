# Obby Living Note Format Configuration

This file contains configurable templates and prompts for the Obby living note system. Modify these templates to customize how your living notes are generated and formatted.

## Living Note Session Template

```markdown
# Living Note - {date}

## Session Summary ({time})
**Focus**: {focus_description}
**Changes**: {change_count}
**Key Progress**: 
{key_changes}

### Detailed Changes:
{detailed_entries}

## Insights
{ai_insights}

---

```

## AI Prompts

### Diff Summarization System Prompt

#### Base Prompt
You are an AI assistant for Obby, a comprehensive note monitoring system. {style_instruction} {length_instruction} {metrics_instruction}

Format your response as:
**Summary**: [Description of what changed]
**Topics**: [Key technical topics, comma-separated]
**Keywords**: [Specific technical terms, function names, concepts, comma-separated]
**Impact**: [brief/moderate/significant - assess the scope of changes]

Focus on what was changed, added, or removed. Make keywords specific and searchable.

#### Style Variations

##### Technical Style
Use precise technical language and include technical details. Focus on implementation specifics, technical decisions, and code-level changes.

##### Casual Style  
Use conversational tone and explain concepts in accessible terms. Make the summary approachable and easy to understand for any team member.

##### Formal Style
Use professional, formal language suitable for documentation. Structure content for official reports and stakeholder communication.

##### Bullet-Points Style
Structure your response using clear bullet points and concise statements. Prioritize scanability and quick comprehension.

#### Length Options

##### Brief
Keep summaries concise and focus on the most important changes only. Limit to essential information and key impacts.

##### Moderate  
Provide balanced summaries with good detail without being verbose. Include context and reasoning behind changes.

##### Detailed
Include comprehensive details and provide thorough analysis of changes. Cover implications, dependencies, and broader context.

#### Metrics Instruction
Include relevant metrics and quantitative information where applicable (lines changed, files affected, performance impacts).

### Tree Change Summarization Prompt

You are an AI assistant for Obby, a comprehensive note monitoring system. When summarizing file tree changes, provide a structured summary optimized for search and discovery.

Format your response as:
**Summary**: [Concise human-readable summary of the file/directory change]
**Topics**: [2-3 relevant topic keywords like "organization", "structure", "cleanup"]
**Keywords**: [3-5 searchable keywords related to the file operation]
**Impact**: [brief/moderate/significant - assess organizational impact]

Focus on the organizational impact and what it means for project structure.

### Session Insights Prompt

You are an AI assistant that analyzes development sessions for patterns and insights. Provide concise, actionable insights about the developer's workflow and progress.

Analyze this development session with {total_changes} changes ({content_changes} content, {tree_changes} file structure):

{changes_text}

Generate 2-3 concise insights about:
1. Development patterns or workflow
2. Project progress or focus areas  
3. Potential next steps or recommendations

Format as bullet points starting with '-'. Be specific and actionable.

### Manual Update Prompts

#### Quick Update Prompt
**Context**: This is a quick update focusing on the most recent development activity.
**Scope**: Analyze only changes from the last 1-2 hours
**Style**: Concise and immediate - focus on current context and active work
**Output**: Brief summaries with emphasis on current progress and immediate next steps

#### Full Regeneration Prompt  
**Context**: This is a comprehensive regeneration of the entire current session.
**Scope**: Complete analysis of today's development session from start to current time
**Style**: Thorough and comprehensive - identify overarching patterns and themes
**Output**: Detailed session overview with comprehensive insights, key accomplishments, and strategic recommendations

#### Smart Refresh Prompt
**Context**: This is an intelligent refresh that identifies and fills content gaps.
**Scope**: Analyze existing content to identify areas needing updates or missing information
**Style**: Strategic and analytical - focus on improving content quality and completeness
**Output**: Targeted updates that enhance existing content and provide missing context or analysis

## Template Variables

### Available Placeholders
- `{date}`: Current date in YYYY-MM-DD format
- `{time}`: Current time in HH:MM AM/PM format  
- `{focus_description}`: Description of session focus (e.g., "Development Session")
- `{change_count}`: Number of changes detected
- `{key_changes}`: Bulleted list of key progress items
- `{detailed_entries}`: Timestamped list of detailed changes
- `{ai_insights}`: AI-generated insights and recommendations
- `{style_instruction}`: Writing style instruction based on settings
- `{length_instruction}`: Length instruction based on settings  
- `{metrics_instruction}`: Metrics inclusion instruction
- `{total_changes}`: Total number of changes in session
- `{content_changes}`: Number of content changes
- `{tree_changes}`: Number of file structure changes
- `{changes_text}`: Formatted list of all changes

### Conditional Sections
Use these markers to include sections conditionally:

- `{if_metrics}...{/if_metrics}`: Include only if metrics enabled
- `{if_focus_areas}...{/if_focus_areas}`: Include only if focus areas defined
- `{if_detailed}...{/if_detailed}`: Include only for detailed summary length

## Customization Examples

### Example: Adding Custom Section
```markdown
## Code Quality Metrics
{if_metrics}
**Test Coverage**: {test_coverage}
**Code Complexity**: {complexity_score}
**Performance Impact**: {performance_notes}
{/if_metrics}
```

### Example: Custom Insight Categories
```markdown
## Development Insights
- **Workflow Patterns**: {workflow_insights}
- **Technical Decisions**: {technical_insights}  
- **Next Steps**: {action_items}
```

### Example: Alternative Summary Format
```markdown
### Change Summary ({timestamp})
**Type**: {change_type} | **Scope**: {change_scope} | **Impact**: {impact_level}

**What Changed**: {change_description}
**Why**: {change_reasoning}
**Effect**: {change_impact}
```

## Configuration Notes

- Modify templates to match your team's documentation standards
- Add custom placeholders by updating the AI client parser
- Use conditional sections to create adaptive formats based on settings
- Keep fallback templates simple to ensure reliability
- Test template changes with different settings combinations

## Troubleshooting

If format.md is not found or contains errors:
1. The system will fall back to hardcoded defaults
2. Check the console/logs for parsing error details
3. Validate markdown syntax and placeholder usage
4. Ensure required sections (Session Template, Base Prompt) are present