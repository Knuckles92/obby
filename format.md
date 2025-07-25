# Obby Living Note Format Configuration

This file contains templates for the Obby living note system. Modify these to customize how your notes are generated.

## Living Note Template

```markdown
# Living Note - {date}

## Session Summary
**Time**: {time}
**Changes**: {change_count}

### What Changed:
{detailed_entries}

### Insights:
{ai_insights}

---

```

## AI Prompts

### Change Summary Prompt
You are analyzing code changes for a development note system. 

For each change, provide:
**Summary**: Brief description of what changed
**Keywords**: Important terms and concepts (comma-separated)
**Impact**: brief/moderate/significant

Keep it simple and focused on what actually changed.

### Session Insights Prompt
You are analyzing a development session with {total_changes} changes.

{changes_text}

Provide 2-3 simple insights about:
- What the developer worked on
- Key progress made
- Suggested next steps

Format as bullet points starting with '-'.

## Available Variables

Basic variables you can use in templates:
- `{date}`: Today's date
- `{time}`: Current time
- `{change_count}`: Number of changes
- `{detailed_entries}`: List of changes
- `{ai_insights}`: AI-generated insights
- `{total_changes}`: Total changes in session
- `{changes_text}`: All changes formatted

## Getting Started

1. The system uses the templates above by default
2. Edit the "Living Note Template" section to change how notes look
3. Edit the prompts to change how AI analyzes your changes
4. Add variables using `{variable_name}` format

That's it! Start simple and customize as needed.
