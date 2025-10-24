# Backend Tests

Quick reference for Obby's backend test suite using pytest.

## Important: Python Environment

**ALWAYS use `python -m pytest` instead of `pytest` directly.**

Due to multiple Python installations on the system, the `pytest` command may use a different Python version than your dependencies are installed for. Using `python -m pytest` ensures consistency.

## Quick Start

```bash
# Run all tests (RECOMMENDED)
python -m pytest

# Run with coverage
python -m pytest --cov=. --cov-report=html --cov-report=term

# Run specific test file
python -m pytest tests/test_database/test_models.py

# Run by marker
python -m pytest -m unit      # Unit tests only
python -m pytest -m api       # API tests only
python -m pytest -m database  # Database tests only
```

## Structure

```
tests/
├── conftest.py              # Shared fixtures (db, mocks, sample data)
├── test_database/           # Database models & queries
├── test_utils/              # File helpers, handlers
├── test_routes/             # API endpoint tests
├── test_services/           # Business logic tests
└── test_ai/                 # AI integration tests (mocked)
```

## Test Markers

Use markers to categorize and run specific test types:

- `@pytest.mark.unit` - Fast unit tests
- `@pytest.mark.integration` - Multi-component tests
- `@pytest.mark.database` - Tests requiring database
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.ai` - AI integration tests
- `@pytest.mark.slow` - Time-consuming tests

## Common Fixtures

Available in all tests via `conftest.py`:

- `temp_dir` - Temporary directory for test files
- `db_connection` - Isolated test database
- `mock_openai_client` - Mocked AI client
- `fastapi_client` - API test client
- `sample_file_content` - Test file content
- `sample_diff` - Test diff content

## Example Test

```python
import pytest
from database.models import FileVersionModel

class TestFeature:
    @pytest.mark.unit
    @pytest.mark.database
    def test_operation(self, db_connection):
        """Test with isolated database."""
        import database.models as models_module
        original_db = models_module.db
        models_module.db = db_connection

        try:
            # Your test code
            result = FileVersionModel.insert(...)
            assert result is not None
        finally:
            models_module.db = original_db
```

## Running Specific Tests

```bash
# Single test function
pytest tests/test_database/test_models.py::TestFileVersionModel::test_insert

# Test class
pytest tests/test_database/test_models.py::TestFileVersionModel

# Tests matching pattern
pytest -k "test_insert"

# Verbose output
pytest -v

# Show print statements
pytest -s
```

## Coverage Reports

```bash
# Generate HTML report
pytest --cov=. --cov-report=html

# View report
# Linux/WSL: xdg-open htmlcov/index.html
# Windows: start htmlcov/index.html
# macOS: open htmlcov/index.html
```

## Best Practices

✅ **DO:**
- Use fixtures from `conftest.py`
- Mark tests with appropriate markers
- Test edge cases and errors
- Keep unit tests fast (<100ms)
- Mock external dependencies (AI, network)

❌ **DON'T:**
- Use production database
- Make real API calls
- Share state between tests
- Test implementation details

## Documentation

For comprehensive documentation, see:
- **Full Guide**: `/specs/TEST_IMPLEMENTATION_SUMMARY.md`
- **Coverage Config**: `/.coveragerc`
- **Pytest Config**: `/pytest.ini`

## Troubleshooting

**Import errors:**
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Database locked:**
Use `db_connection` fixture, don't share connections

**Async test failures:**
Add `@pytest.mark.asyncio` decorator

## Target Coverage

- Database Layer: 70-80%
- Utils: 70-80%
- Routes/API: 60-70%
- Services: 60-70%
- Overall: 60-80%
