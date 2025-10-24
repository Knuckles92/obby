# Frontend Tests

Quick reference for Obby's frontend test suite using Vitest and React Testing Library.

## Quick Start

```bash
cd frontend

# Install dependencies (first time)
npm install

# Run tests in watch mode
npm test

# Run tests once
npm run test:run

# Run with UI
npm run test:ui

# Generate coverage
npm run test:coverage
```

## Structure

```
frontend/src/
├── test/
│   └── setup.ts                    # Test environment setup
└── __tests__/
    ├── utils/
    │   └── api.test.ts             # API utility tests
    └── components/
        ├── ConfirmationDialog.test.tsx
        └── ThemeSwitcher.test.tsx
```

## Test Patterns

### Component Testing

```typescript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MyComponent from '../../components/MyComponent';

it('should render and handle interaction', async () => {
  const user = userEvent.setup();
  const onClick = vi.fn();

  render(<MyComponent onClick={onClick} />);

  expect(screen.getByText('Button')).toBeInTheDocument();

  await user.click(screen.getByRole('button'));
  expect(onClick).toHaveBeenCalled();
});
```

### API Testing

```typescript
it('should fetch data', async () => {
  global.fetch = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ data: 'test' }), { status: 200 })
  );

  const result = await apiRequest('/api/endpoint');
  expect(result.data).toBe('test');
});
```

## Common Queries

Use semantic queries for better tests:

```typescript
// Preferred (accessible)
screen.getByRole('button', { name: /submit/i })
screen.getByLabelText('Email')
screen.getByPlaceholderText('Enter name')
screen.getByText(/welcome/i)

// Less preferred (fragile)
screen.getByTestId('submit-btn')
```

## Mocking

### Mock Functions

```typescript
import { vi } from 'vitest';

const mockFn = vi.fn();
mockFn.mockReturnValue('value');
mockFn.mockResolvedValue(Promise.resolve('async value'));
```

### Mock Modules

```typescript
vi.mock('../../utils/api', () => ({
  apiRequest: vi.fn().mockResolvedValue({ data: 'mocked' })
}));
```

## Test Setup

The `test/setup.ts` file provides:
- Automatic cleanup after each test
- Mocked `window.matchMedia` for theme detection
- Mocked `IntersectionObserver` for visibility tracking
- Mocked `fetch` for API calls

## Running Specific Tests

```bash
# Watch specific file
npm test api.test.ts

# Run one test
npm test -- -t "should render"

# Update snapshots
npm test -- -u
```

## Coverage Reports

```bash
npm run test:coverage

# View report
# Open frontend/coverage/index.html in browser
```

## Best Practices

✅ **DO:**
- Test user behavior, not implementation
- Use semantic queries (getByRole, getByLabelText)
- Mock API calls
- Test accessibility
- Use userEvent for interactions

❌ **DON'T:**
- Test component internals
- Use getByTestId unless necessary
- Make real network requests
- Test CSS/styling details
- Query by class names

## Debugging Tests

```bash
# Show console output
npm test -- --reporter=verbose

# Debug single test
npm test -- -t "test name" --reporter=verbose

# Browser debugging (with --ui)
npm run test:ui
```

## Common Assertions

```typescript
// DOM presence
expect(element).toBeInTheDocument()
expect(element).not.toBeInTheDocument()

// Visibility
expect(element).toBeVisible()
expect(element).not.toBeVisible()

// Text content
expect(element).toHaveTextContent('text')
expect(element).toHaveTextContent(/pattern/i)

// Form elements
expect(input).toHaveValue('value')
expect(checkbox).toBeChecked()
expect(button).toBeDisabled()

// Functions
expect(mockFn).toHaveBeenCalled()
expect(mockFn).toHaveBeenCalledTimes(2)
expect(mockFn).toHaveBeenCalledWith('arg')
```

## Documentation

For comprehensive documentation, see:
- **Full Guide**: `/specs/TEST_IMPLEMENTATION_SUMMARY.md`
- **Vitest Config**: `/frontend/vite.config.ts`
- **Test Setup**: `/frontend/src/test/setup.ts`

## Troubleshooting

**Cannot find module:**
```bash
npm install
```

**jsdom not found:**
```bash
npm install -D jsdom
```

**React Testing Library errors:**
```bash
npm install -D @testing-library/react @testing-library/jest-dom
```

## Target Coverage

- Utils: 70-80%
- Components: 50-60%
- Overall: 60-70%
