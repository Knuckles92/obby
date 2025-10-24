# Tests

Pytest drives the automated checks for Obby. Run everything from the project root so the shared fixtures in `conftest.py` are picked up.

## Layout
- `test_ai/` exercises the async `ai.openai_client.OpenAIClient` via the `mock_openai_client` fixture.
- `test_database/` validates SQLite models and queries against the ephemeral DB created by the `db_connection` fixture.
- `test_routes/` hits FastAPI endpoints with `fastapi_client` and stubs for watch filtering and database state.
- `test_utils/` covers helper modules such as file watching and ignore handling.
- `test_services/` is a placeholder to group future service-level tests.

## How to run
1. `python -m venv venv && source venv/bin/activate`
2. `pip install -r requirements.txt`
3. `pytest -q`

Common markers include `unit` and `ai`; filter with `pytest -m unit`. Async tests rely on `pytest-asyncio`, which is already listed in project dependencies.

During test runs `conftest.py` sets `TESTING=1` and `SKIP_AI_PROCESSING=1` so no real API calls or watchers are started.
