# Obby Test Suite Implementation Summary

## Overview

This document provides a comprehensive guide to the test suite implemented for the Obby note monitoring application. The test suite covers both backend (Python/pytest) and frontend (TypeScript/Vitest) code with a target coverage of 60-80%.

## Test Infrastructure

### Backend Testing (pytest)

#### Configuration Files

- **`pytest.ini`**: Main pytest configuration
  - Test discovery patterns
  - Async test configuration
  - Custom markers (unit, integration, slow, database, api, ai)
  - Ignore patterns for excluded directories

- **`.coveragerc`**: Coverage reporting configuration
  - Source code inclusion/exclusion rules
  - Branch coverage enabled
  - HTML and XML report generation
  - Lines to exclude from coverage (debug code, abstract methods, etc.)

- **`conftest.py`**: Shared test fixtures
  - `temp_dir`: Temporary directory for test files
  - `test_db_path`: Temporary database file path
  - `db_connection`: Test database with schema
  - `mock_claude_agent_client`: Mocked Claude client for testing
  - `mock_file_watcher`: Mocked file monitoring
  - `fastapi_client`: FastAPI test client for API testing
  - Sample data fixtures for common test scenarios

#### Test Dependencies

Added to `requirements.txt`:
- `pytest>=7.0.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async test support
- `pytest-cov>=4.0.0` - Coverage reporting
- `pytest-mock>=3.10.0` - Mocking utilities
- `httpx>=0.24.0` - HTTP client for FastAPI testing

### Frontend Testing (Vitest)

#### Configuration Files

- **`vite.config.ts`**: Enhanced with Vitest configuration
  - jsdom environment for DOM testing
  - Coverage reporting (v8 provider)
  - Test setup file integration
  - CSS support in tests

- **`frontend/package.json`**: Updated with test scripts and dependencies
  - `npm test`: Run tests in watch mode
  - `npm run test:run`: Run tests once
  - `npm run test:ui`: Open Vitest UI
  - `npm run test:coverage`: Generate coverage report

- **`src/test/setup.ts`**: Test environment setup
  - React Testing Library cleanup
  - jsdom matchers
  - Mock `window.matchMedia` for theme detection
  - Mock `IntersectionObserver` for component testing
  - Mock `fetch` for API calls

#### Test Dependencies

Added to `frontend/package.json`:
- `vitest@^1.0.4` - Test runner
- `@vitest/ui@^1.0.4` - Test UI
- `@testing-library/react@^14.1.2` - React testing utilities
- `@testing-library/jest-dom@^6.1.5` - Custom matchers
- `@testing-library/user-event@^14.5.1` - User interaction simulation
- `jsdom@^23.0.1` - DOM environment

## Test Structure

### Backend Tests (`tests/`)

```
tests/
├── conftest.py                      # Shared fixtures
├── __init__.py
├── test_database/
│   ├── __init__.py
│   ├── test_models.py              # Database model tests
│   └── test_queries.py             # Query layer tests
├── test_utils/
│   ├── __init__.py
│   ├── test_file_helpers.py        # File utility tests
│   ├── test_ignore_handler.py      # .obbyignore pattern tests
│   └── test_watch_handler.py       # .obbywatch pattern tests
├── test_services/
│   └── __init__.py                 # Service layer tests (extensible)
├── test_routes/
│   ├── __init__.py
│   ├── test_monitoring.py          # Monitoring API tests
│   ├── test_files.py               # File API tests
│   └── test_search.py              # Search API tests
└── test_ai/
    ├── __init__.py
```

### Frontend Tests (`frontend/src/`)

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

## Running Tests

### Backend Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=. --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_database/test_models.py

# Run tests with specific marker
pytest -m unit
pytest -m api
pytest -m database

# Run with verbose output
pytest -v

# Run and watch for changes (requires pytest-watch)
ptw
```

### Frontend Tests

```bash
# Change to frontend directory
cd frontend

# Install dependencies (first time only)
npm install

# Run tests in watch mode
npm test

# Run tests once (CI mode)
npm run test:run

# Open Vitest UI
npm run test:ui

# Generate coverage report
npm run test:coverage
```

## Test Categories

### Backend Test Markers

Tests are organized using pytest markers for selective execution:

- `@pytest.mark.unit` - Fast unit tests for individual functions
- `@pytest.mark.integration` - Tests that involve multiple components
- `@pytest.mark.slow` - Tests that take significant time
- `@pytest.mark.database` - Tests requiring database access
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.ai` - AI integration tests (mocked)

Example usage:
```bash
# Run only unit tests
pytest -m unit

# Run only API tests
pytest -m api

# Skip slow tests
pytest -m "not slow"
```

## Key Testing Patterns

### Backend Patterns

#### 1. Database Testing
```python
def test_database_operation(db_connection):
    """Test uses isolated test database."""
    import database.models as models_module
    original_db = models_module.db
    models_module.db = db_connection

    try:
        # Test code here
        FileVersionModel.insert(...)
    finally:
        models_module.db = original_db
```

#### 2. API Testing
```python
def test_api_endpoint(fastapi_client):
    """Test uses FastAPI test client."""
    response = fastapi_client.get("/api/endpoint")
    assert response.status_code == 200
    data = response.json()
    assert 'expected_key' in data
```

#### 3. Mocking AI Calls
```python
@pytest.mark.ai
async def test_ai_feature(mock_claude_agent_client):
    """Test AI features without real API calls."""
    result = await mock_claude_agent_client.summarize_changes([{"path": "file.md", "content": "delta"}])
    assert result is not None
```

### Frontend Patterns

#### 1. Component Testing
```typescript
it('should render component', () => {
  render(<MyComponent prop="value" />);
  expect(screen.getByText('Expected Text')).toBeInTheDocument();
});
```

#### 2. User Interaction Testing
```typescript
it('should handle click', async () => {
  const user = userEvent.setup();
  const onClick = vi.fn();

  render(<Button onClick={onClick}>Click Me</Button>);
  await user.click(screen.getByRole('button'));

  expect(onClick).toHaveBeenCalledTimes(1);
});
```

#### 3. API Call Testing
```typescript
it('should fetch data', async () => {
  global.fetch = vi.fn().mockResolvedValue(
    new Response(JSON.stringify({ data: 'test' }), { status: 200 })
  );

  const result = await apiRequest('/api/test');
  expect(result.data).toBe('test');
});
```

## Coverage Goals

### Current Target: 60-80%

- **Database Layer**: 70-80% coverage
  - Models: CRUD operations, data validation
  - Queries: File operations, search, filtering

- **Utils**: 70-80% coverage
  - File helpers: Core file operations
  - Handlers: Pattern matching, configuration loading

- **Routes/API**: 60-70% coverage
  - Key endpoints: monitoring, files, search
  - Request validation, response formatting

- **Services**: 60-70% coverage
  - Business logic for summaries and processing

- **Frontend Utils**: 70-80% coverage
  - API client functions
  - Helper utilities

- **Frontend Components**: 50-60% coverage
  - Key reusable components
  - User interaction flows

### Viewing Coverage Reports

#### Backend
```bash
# Generate HTML coverage report
pytest --cov=. --cov-report=html

# Open in browser
# Linux/WSL:
xdg-open htmlcov/index.html
# Windows:
start htmlcov/index.html
# macOS:
open htmlcov/index.html
```

#### Frontend
```bash
cd frontend
npm run test:coverage

# Coverage report will be in frontend/coverage/
# Open frontend/coverage/index.html in browser
```

## Writing New Tests

### Backend Test Template

```python
"""
Unit tests for [module name].

Brief description of what is being tested.
"""

import pytest
from module_name import function_or_class


class TestFeatureName:
    """Test the FeatureName functionality."""

    @pytest.mark.unit
    def test_basic_functionality(self):
        """Test basic operation."""
        result = function_or_class()
        assert result is not None

    @pytest.mark.unit
    def test_error_handling(self):
        """Test error conditions."""
        with pytest.raises(ValueError):
            function_or_class(invalid_input)

    @pytest.mark.database
    def test_with_database(self, db_connection):
        """Test database operations."""
        # Use db_connection fixture
        pass
```

### Frontend Test Template

```typescript
/**
 * Unit tests for [component/module name]
 *
 * Brief description of what is being tested.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ComponentName from './ComponentName';

describe('ComponentName', () => {
  it('should render correctly', () => {
    render(<ComponentName />);
    expect(screen.getByText('Expected Text')).toBeInTheDocument();
  });

  it('should handle interactions', async () => {
    const user = userEvent.setup();
    const onAction = vi.fn();

    render(<ComponentName onAction={onAction} />);
    await user.click(screen.getByRole('button'));

    expect(onAction).toHaveBeenCalled();
  });
});
```

## Continuous Integration (Future)

The test suite is designed to integrate easily with CI/CD pipelines:

### GitHub Actions Example
```yaml
name: Tests

on: [push, pull_request]

jobs:
  backend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest --cov=. --cov-report=xml
      - uses: codecov/codecov-action@v3

  frontend-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - run: cd frontend && npm install
      - run: cd frontend && npm run test:run
```

## Best Practices

### General Guidelines

1. **Test Independence**: Each test should be independent and not rely on other tests
2. **Fast Tests**: Keep unit tests fast (<100ms each) for quick feedback
3. **Clear Naming**: Use descriptive test names that explain what is being tested
4. **Single Assertion Focus**: Each test should verify one specific behavior
5. **Fixture Usage**: Use fixtures to reduce code duplication

### Backend-Specific

1. **Isolate Database**: Always use test database fixtures, never production data
2. **Mock External Services**: Mock Claude Agent SDK, file system when appropriate
3. **Test Edge Cases**: Test error conditions, boundary values, empty inputs
4. **Async Tests**: Use `@pytest.mark.asyncio` for async functions

### Frontend-Specific

1. **Test User Behavior**: Focus on testing what users see and do
2. **Avoid Implementation Details**: Don't test component internals
3. **Mock Network Calls**: Always mock API calls in component tests
4. **Accessibility**: Use semantic queries (getByRole, getByLabelText)

## Troubleshooting

### Common Issues

#### Backend

**Issue**: Import errors in tests
```bash
# Solution: Ensure project root is in Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Issue**: Database locked errors
```bash
# Solution: Ensure each test uses fresh db_connection fixture
# and doesn't share connections between tests
```

**Issue**: Async test failures
```bash
# Solution: Verify pytest-asyncio is installed
# and tests are marked with @pytest.mark.asyncio
```

#### Frontend

**Issue**: "Cannot find module" errors
```bash
# Solution: Install dependencies
cd frontend && npm install
```

**Issue**: "jsdom environment not found"
```bash
# Solution: Install jsdom
npm install -D jsdom
```

**Issue**: Component tests failing
```bash
# Solution: Check if setup.ts is being loaded
# Verify vite.config.ts has correct setupFiles path
```

## Maintenance

### Updating Tests

- When adding new features, add corresponding tests
- When fixing bugs, add regression tests
- Keep test coverage above 60% overall
- Review and update mocks when dependencies change
- Run full test suite before commits

### Test Review Checklist

- [ ] Tests are independent and can run in any order
- [ ] Tests have clear, descriptive names
- [ ] Edge cases and error conditions are tested
- [ ] Mocks are used for external dependencies
- [ ] Coverage remains above threshold
- [ ] Tests run quickly (unit tests < 100ms)
- [ ] Documentation is updated if test patterns change

## Resources

### Documentation

- [pytest documentation](https://docs.pytest.org/)
- [Vitest documentation](https://vitest.dev/)
- [React Testing Library](https://testing-library.com/react)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)

### Tools

- **pytest**: Python testing framework
- **pytest-cov**: Coverage reporting for Python
- **Vitest**: Vite-native test runner for frontend
- **React Testing Library**: User-centric React testing
- **jsdom**: JavaScript DOM implementation for Node.js

---

## Summary

The Obby test suite provides comprehensive coverage of both backend and frontend functionality:

- ✅ **Backend**: pytest-based tests with isolated database, mocked AI, and API testing
- ✅ **Frontend**: Vitest-based tests with React Testing Library
- ✅ **Coverage**: Targeting 60-80% across the codebase
- ✅ **Easy Execution**: Simple commands to run all or specific tests
- ✅ **CI/CD Ready**: Structured for easy integration with pipelines
- ✅ **Documentation**: Clear patterns and examples for writing new tests

**Getting Started:**
```bash
# Backend
pytest --cov=. --cov-report=html

# Frontend
cd frontend && npm test
```

For questions or issues with the test suite, refer to this document or check the inline comments in test files.
