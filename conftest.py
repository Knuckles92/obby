"""
Pytest configuration and shared fixtures for the Obby test suite.

This module provides:
- Test database setup and teardown
- Mock OpenAI client
- Temporary directory fixtures
- FastAPI test client
- Common test data
"""

import pytest
import sqlite3
import tempfile
import shutil
from pathlib import Path
from typing import Generator, Dict, Any
from unittest.mock import MagicMock, AsyncMock
import sys
import os

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from database.models import DatabaseConnection
from config import settings


@pytest.fixture(scope="function")
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture(scope="function")
def test_db_path(temp_dir: Path) -> Path:
    """Create a temporary database file path."""
    return temp_dir / "test_obby.db"


@pytest.fixture(scope="function")
def db_connection(test_db_path: Path):
    """
    Create a test database connection with schema.

    This fixture:
    - Creates an in-memory SQLite database
    - Initializes the schema
    - Provides a DatabaseConnection instance
    - Cleans up after the test
    """
    # Create database connection
    conn = DatabaseConnection(str(test_db_path))

    # Initialize schema (run migrations)
    try:
        from database.models import (
            FileVersionModel, ContentDiffModel, FileStateModel,
            PerformanceModel, SemanticModel, ConfigModel,
            EventModel, FileChangeModel
        )

        # Create all tables
        with conn.get_connection() as db:
            cursor = db.cursor()

            # Enable foreign keys
            cursor.execute("PRAGMA foreign_keys = ON")

            # Create tables (basic schema for testing)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    content TEXT,
                    timestamp REAL NOT NULL,
                    size INTEGER,
                    UNIQUE(file_path, content_hash)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS content_diffs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    old_hash TEXT,
                    new_hash TEXT NOT NULL,
                    diff_content TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    change_type TEXT NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_states (
                    file_path TEXT PRIMARY KEY,
                    current_hash TEXT NOT NULL,
                    last_modified REAL NOT NULL,
                    size INTEGER,
                    is_deleted BOOLEAN DEFAULT 0
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS semantic_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    summary TEXT,
                    topics TEXT,
                    keywords TEXT,
                    impact_level TEXT,
                    timestamp REAL NOT NULL,
                    UNIQUE(file_path, content_hash)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at REAL NOT NULL
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    details TEXT
                )
            """)

            # Create FTS5 search table
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS file_content_fts
                USING fts5(file_path, content, content='file_versions', content_rowid='id')
            """)

            db.commit()
    except Exception as e:
        print(f"Warning: Could not initialize full schema: {e}")

    yield conn

    # Cleanup
    conn.close()
    if test_db_path.exists():
        test_db_path.unlink()


@pytest.fixture
def sample_file_content() -> str:
    """Sample file content for testing."""
    return """def hello_world():
    print("Hello, World!")
    return True

if __name__ == "__main__":
    hello_world()
"""


@pytest.fixture
def sample_diff() -> str:
    """Sample diff content for testing."""
    return """--- a/test.py
+++ b/test.py
@@ -1,5 +1,6 @@
 def hello_world():
-    print("Hello, World!")
+    print("Hello, Obby!")
+    print("Testing changes")
     return True

 if __name__ == "__main__":
"""


@pytest.fixture
def mock_openai_client():
    """
    Mock OpenAI client for testing AI functionality.

    Returns a mock that simulates OpenAI API responses without making real calls.
    """
    mock = MagicMock()

    # Mock summarize method
    async def mock_summarize(*args, **kwargs):
        return {
            "summary": "Test summary of code changes",
            "topics": ["testing", "python"],
            "keywords": ["function", "print", "test"],
            "impact_level": "minor"
        }

    mock.summarize = AsyncMock(side_effect=mock_summarize)

    # Mock summarize_minimal method
    async def mock_summarize_minimal(*args, **kwargs):
        return "• Test change\n• Updated function\n\n### Sources\n- test.py: Modified test function"

    mock.summarize_minimal = AsyncMock(side_effect=mock_summarize_minimal)

    # Mock batch processing
    async def mock_process_batch(*args, **kwargs):
        return [
            {
                "file_path": "test.py",
                "summary": "Test summary",
                "topics": ["testing"],
                "keywords": ["test"],
                "impact_level": "minor"
            }
        ]

    mock.process_batch = AsyncMock(side_effect=mock_process_batch)

    return mock


@pytest.fixture
def mock_file_watcher():
    """Mock file watcher for testing monitoring functionality."""
    mock = MagicMock()
    mock.start = MagicMock()
    mock.stop = MagicMock()
    mock.is_running = MagicMock(return_value=True)
    return mock


@pytest.fixture
def sample_file_data() -> Dict[str, Any]:
    """Sample file data for testing database operations."""
    return {
        "file_path": "test.py",
        "content_hash": "abc123def456",
        "content": "print('test')",
        "timestamp": 1234567890.0,
        "size": 15
    }


@pytest.fixture
def sample_semantic_data() -> Dict[str, Any]:
    """Sample semantic analysis data for testing."""
    return {
        "file_path": "test.py",
        "content_hash": "abc123def456",
        "summary": "A simple test file",
        "topics": ["testing", "python"],
        "keywords": ["print", "test"],
        "impact_level": "minor",
        "timestamp": 1234567890.0
    }


@pytest.fixture(scope="function")
def fastapi_client():
    """
    Create a FastAPI test client for API testing.

    Note: This imports the app and may start monitoring.
    Use with caution in tests.
    """
    from fastapi.testclient import TestClient
    from backend import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_settings(monkeypatch):
    """Mock settings for testing."""
    test_settings = {
        "OPENAI_API_KEY": "test-key-123",
        "DATABASE_PATH": ":memory:",
        "WATCH_DIRECTORY": "/tmp/test",
        "BATCH_SIZE": 10,
        "BATCH_INTERVAL": 300
    }

    for key, value in test_settings.items():
        if hasattr(settings, key):
            monkeypatch.setattr(settings, key, value)

    return test_settings


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Set test environment variable
    os.environ["TESTING"] = "1"

    # Disable AI processing during tests
    os.environ["SKIP_AI_PROCESSING"] = "1"


def pytest_unconfigure(config):
    """Cleanup after all tests."""
    # Clean environment variables
    os.environ.pop("TESTING", None)
    os.environ.pop("SKIP_AI_PROCESSING", None)
