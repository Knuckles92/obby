# Summary Components

This directory contains React components for managing summary generation features in the Obby application.

## Components

### GenerationPreview

A comprehensive preview component that displays what will be included in summary generation before the user confirms.

#### Features

- **Time Range Summary**: Displays human-readable time range from preview data
- **Statistics Grid**: Shows total files, changes, lines added/removed, and net change with color-coded badges
- **Matched Files List**: Expandable/collapsible list showing:
  - File path (truncated if too long)
  - Change summary (e.g., "3 changes, +45/-12 lines")
  - Last modified timestamp
  - File size
  - Deleted status indicator if applicable
  - View/edit link button
- **Filters Applied**: Shows applied filters as pills/tags
- **Warnings Section**: Displays any warnings with explanations (e.g., file limit reached)
- **Action Buttons**: Primary "Generate with this context" and secondary "Adjust filters" buttons

#### Props

```typescript
interface GenerationPreviewProps {
  previewData: SummaryGenerationPlan;
  isLoading?: boolean;
  onGenerate: () => void;
  onAdjustFilters: () => void;
  summaryType?: "session" | "note";
}
```

#### Usage Example

```tsx
import GenerationPreview from './components/summary/GenerationPreview'
import { SummaryGenerationPlan } from './types'

function MyComponent() {
  const [previewData, setPreviewData] = useState<SummaryGenerationPlan | null>(null)
  const [isLoadingPreview, setIsLoadingPreview] = useState(false)

  const handleGenerate = async () => {
    // Call backend API to generate summary with current context
    const response = await fetch('/api/summary-notes/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ context_config: previewData.context_config })
    })
    // Handle response...
  }

  const handleAdjustFilters = () => {
    // Navigate back to filter configuration or open filter modal
    setPreviewData(null)
  }

  return (
    <div>
      {previewData && (
        <GenerationPreview
          previewData={previewData}
          isLoading={isLoadingPreview}
          onGenerate={handleGenerate}
          onAdjustFilters={handleAdjustFilters}
          summaryType="note"
        />
      )}
    </div>
  )
}
```

#### Backend Integration

The component expects preview data matching the `SummaryGenerationPlan` structure from the backend:

```python
# Python backend (utils/summary_context.py)
@dataclass
class SummaryGenerationPlan:
    context_config: SummaryContextConfig
    matched_files: List[MatchedFile]
    time_range_description: str
    total_files: int
    total_changes: int
    total_lines_added: int
    total_lines_removed: int
    filters_applied: List[str]
    warnings: List[str]
```

To fetch preview data from the backend, make a POST request to the appropriate endpoint with the current context configuration:

```typescript
const fetchPreview = async (contextConfig) => {
  const response = await fetch('/api/summary-notes/preview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(contextConfig)
  })
  return await response.json()
}
```

### SummaryContextControls

Provides comprehensive controls for configuring summary generation context including time windows, file filters, content types, and scope controls.

## Types

All types are exported from `/frontend/src/types/index.ts`:

- `SummaryGenerationPlan`: Complete preview data structure
- `MatchedFile`: Individual file information in the preview
- `SummaryContextConfig`: Context configuration (from SummaryContextControls)

## Styling

All components use the Obby theming system with CSS variables:
- `var(--color-primary)`, `var(--color-secondary)`, `var(--color-accent)`
- `var(--color-background)`, `var(--color-surface)`, `var(--color-overlay)`
- `var(--color-text-primary)`, `var(--color-text-secondary)`, etc.
- `var(--color-success)`, `var(--color-warning)`, `var(--color-error)`, `var(--color-info)`
- `var(--color-border)`, `var(--color-divider)`

Components automatically adapt to the current theme selected by the user.
