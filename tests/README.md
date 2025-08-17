# Tests

This directory is reserved for formal unit tests and integration tests.

## Current Status

No formal test framework is currently configured. See CLAUDE.md for current testing approach.

## Future Structure

When implementing formal tests, consider this structure:

```
tests/
├── unit/           # Unit tests for individual components
├── integration/    # Integration tests for API endpoints
├── fixtures/       # Test data and fixtures
└── conftest.py     # Test configuration
```

## Development Testing

For debugging and investigation scripts, see the `/debug/` directory.