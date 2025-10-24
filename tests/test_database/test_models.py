"""
Unit tests for database models.

Tests the FileVersionModel, ContentDiffModel, SemanticModel, and other
database model classes to ensure proper CRUD operations and data integrity.
"""

import pytest
import sqlite3
from datetime import datetime
from database.models import (
    DatabaseConnection,
    FileVersionModel,
    ContentDiffModel,
    SemanticModel,
    FileStateModel,
    ConfigModel
)


class TestDatabaseConnection:
    """Test the DatabaseConnection class."""

    def test_connection_creation(self, test_db_path):
        """Test that a database connection can be created."""
        conn = DatabaseConnection(str(test_db_path))
        assert conn.db_path == str(test_db_path)

    def test_get_connection(self, db_connection):
        """Test getting a database connection."""
        with db_connection.get_connection() as conn:
            assert conn is not None
            assert isinstance(conn, sqlite3.Connection)

    def test_execute_query(self, db_connection):
        """Test executing a SELECT query."""
        # Insert test data first (use valid 64-char SHA-256 hash)
        valid_hash = "a" * 64  # Valid SHA-256 format
        with db_connection.get_connection() as conn:
            conn.execute("""
                INSERT INTO file_versions (file_path, content_hash, timestamp)
                VALUES (?, ?, ?)
            """, ("test.py", valid_hash, datetime.now().timestamp()))
            conn.commit()

        # Query the data
        results = db_connection.execute_query(
            "SELECT * FROM file_versions WHERE file_path = ?",
            ("test.py",)
        )

        assert len(results) > 0
        assert results[0]['file_path'] == "test.py"

    def test_execute_update(self, db_connection):
        """Test executing an INSERT/UPDATE/DELETE query."""
        valid_hash = "b" * 64  # Valid SHA-256 format
        affected = db_connection.execute_update(
            "INSERT INTO file_versions (file_path, content_hash, timestamp) VALUES (?, ?, ?)",
            ("test2.py", valid_hash, datetime.now().timestamp())
        )

        assert affected >= 1

    def test_transaction_rollback(self, db_connection):
        """Test that transactions are rolled back on error."""
        valid_hash = "c" * 64  # Valid SHA-256 format
        with pytest.raises(sqlite3.IntegrityError):
            with db_connection.get_connection() as conn:
                # Try to insert duplicate primary key (should fail)
                conn.execute("""
                    INSERT INTO file_versions (file_path, content_hash, timestamp)
                    VALUES (?, ?, ?)
                """, ("test.py", valid_hash, datetime.now().timestamp()))
                conn.execute("""
                    INSERT INTO file_versions (file_path, content_hash, timestamp)
                    VALUES (?, ?, ?)
                """, ("test.py", valid_hash, datetime.now().timestamp()))
                conn.commit()


class TestFileVersionModel:
    """Test the FileVersionModel class."""

    @pytest.mark.unit
    def test_insert_file_version(self, db_connection, sample_file_content):
        """Test inserting a new file version."""
        import hashlib
        content_hash = hashlib.sha256(sample_file_content.encode()).hexdigest()

        # Monkey-patch the global db instance for testing
        import database.models as models_module
        original_db = models_module.db
        models_module.db = db_connection

        try:
            version_id = FileVersionModel.insert(
                file_path="test.py",
                content_hash=content_hash,
                content=sample_file_content,
                line_count=6,
                timestamp=datetime.now()
            )

            assert version_id is not None
            assert isinstance(version_id, int)

            # Verify the data was inserted
            version = FileVersionModel.get_by_id(version_id)
            assert version is not None
            assert version['file_path'] == "test.py"
            assert version['content_hash'] == content_hash
            assert version['content'] == sample_file_content
        finally:
            models_module.db = original_db

    @pytest.mark.unit
    def test_get_recent_versions(self, db_connection, sample_file_content):
        """Test retrieving recent file versions."""
        import hashlib
        import database.models as models_module
        original_db = models_module.db
        models_module.db = db_connection

        try:
            # Insert multiple versions
            for i in range(3):
                content_hash = hashlib.sha256(f"content{i}".encode()).hexdigest()
                FileVersionModel.insert(
                    file_path=f"file{i}.py",
                    content_hash=content_hash,
                    content=f"content{i}",
                    timestamp=datetime.now()
                )

            # Get recent versions
            recent = FileVersionModel.get_recent(limit=10)
            assert len(recent) >= 3
            assert all('file_path' in v for v in recent)
        finally:
            models_module.db = original_db

    @pytest.mark.unit
    def test_get_by_hash(self, db_connection):
        """Test retrieving a file version by content hash."""
        import hashlib
        import database.models as models_module
        original_db = models_module.db
        models_module.db = db_connection

        try:
            content = "unique content"
            content_hash = hashlib.sha256(content.encode()).hexdigest()

            FileVersionModel.insert(
                file_path="unique.py",
                content_hash=content_hash,
                content=content,
                timestamp=datetime.now()
            )

            version = FileVersionModel.get_by_hash(content_hash)
            assert version is not None
            assert version['content_hash'] == content_hash
            assert version['content'] == content
        finally:
            models_module.db = original_db

    @pytest.mark.unit
    def test_get_file_history(self, db_connection):
        """Test retrieving version history for a specific file."""
        import hashlib
        import database.models as models_module
        original_db = models_module.db
        models_module.db = db_connection

        try:
            file_path = "history_test.py"

            # Insert multiple versions of the same file
            for i in range(5):
                content_hash = hashlib.sha256(f"version{i}".encode()).hexdigest()
                FileVersionModel.insert(
                    file_path=file_path,
                    content_hash=content_hash,
                    content=f"version{i}",
                    timestamp=datetime.now()
                )

            # Get history
            history = FileVersionModel.get_file_history(file_path, limit=10)
            assert len(history) == 5
            assert all(v['file_path'] == file_path for v in history)
        finally:
            models_module.db = original_db

    @pytest.mark.unit
    def test_duplicate_version_handling(self, db_connection):
        """Test that duplicate versions are handled correctly."""
        import hashlib
        import database.models as models_module
        original_db = models_module.db
        models_module.db = db_connection

        try:
            content_hash = hashlib.sha256("duplicate".encode()).hexdigest()

            # Insert first version
            id1 = FileVersionModel.insert(
                file_path="duplicate.py",
                content_hash=content_hash,
                content="duplicate",
                timestamp=datetime.now()
            )

            # Try to insert duplicate (should return existing ID)
            id2 = FileVersionModel.insert(
                file_path="duplicate.py",
                content_hash=content_hash,
                content="duplicate",
                timestamp=datetime.now()
            )

            assert id1 is not None
            assert id2 is not None
            # Both should reference the same record
            assert id1 == id2
        finally:
            models_module.db = original_db


class TestContentDiffModel:
    """Test the ContentDiffModel class."""

    @pytest.mark.unit
    def test_insert_diff(self, db_connection):
        """Test inserting a content diff."""
        import hashlib
        import database.models as models_module
        original_db = models_module.db
        models_module.db = db_connection

        try:
            # Create two file versions first
            hash1 = hashlib.sha256("v1".encode()).hexdigest()
            hash2 = hashlib.sha256("v2".encode()).hexdigest()

            v1_id = FileVersionModel.insert("test.py", hash1, "v1", timestamp=datetime.now())
            v2_id = FileVersionModel.insert("test.py", hash2, "v2", timestamp=datetime.now())

            # Create diff
            diff_id = ContentDiffModel.insert(
                file_path="test.py",
                old_version_id=v1_id,
                new_version_id=v2_id,
                change_type="modified",
                diff_content="@@ -1 +1 @@\n-v1\n+v2",
                lines_added=1,
                lines_removed=1,
                timestamp=datetime.now()
            )

            assert diff_id is not None
        finally:
            models_module.db = original_db

    @pytest.mark.unit
    def test_should_create_diff(self, db_connection):
        """Test diff creation logic."""
        import hashlib
        import database.models as models_module
        original_db = models_module.db
        models_module.db = db_connection

        try:
            # Same version IDs should not create diff
            should_create = ContentDiffModel.should_create_diff(
                old_version_id=1,
                new_version_id=1,
                old_content="test",
                new_content="test"
            )
            assert should_create is False

            # Identical content should not create diff
            should_create = ContentDiffModel.should_create_diff(
                old_version_id=1,
                new_version_id=2,
                old_content="same content",
                new_content="same content"
            )
            assert should_create is False

            # Different content should create diff
            should_create = ContentDiffModel.should_create_diff(
                old_version_id=1,
                new_version_id=2,
                old_content="old",
                new_content="new"
            )
            assert should_create is True
        finally:
            models_module.db = original_db

    @pytest.mark.unit
    def test_get_recent_diffs(self, db_connection):
        """Test retrieving recent diffs."""
        import hashlib
        import database.models as models_module
        original_db = models_module.db
        models_module.db = db_connection

        try:
            # Create versions and diffs
            for i in range(3):
                h1 = hashlib.sha256(f"v{i}a".encode()).hexdigest()
                h2 = hashlib.sha256(f"v{i}b".encode()).hexdigest()
                v1 = FileVersionModel.insert(f"file{i}.py", h1, f"v{i}a", timestamp=datetime.now())
                v2 = FileVersionModel.insert(f"file{i}.py", h2, f"v{i}b", timestamp=datetime.now())

                ContentDiffModel.insert(
                    file_path=f"file{i}.py",
                    old_version_id=v1,
                    new_version_id=v2,
                    change_type="modified",
                    diff_content=f"diff{i}",
                    timestamp=datetime.now()
                )

            # Get recent diffs
            diffs = ContentDiffModel.get_recent(limit=10)
            assert len(diffs) >= 3
            assert all('file_path' in d for d in diffs)
        finally:
            models_module.db = original_db


class TestSemanticModel:
    """Test the SemanticModel class."""

    @pytest.mark.unit
    @pytest.mark.ai
    def test_insert_semantic_analysis(self, db_connection, sample_semantic_data):
        """Test inserting semantic analysis data."""
        import database.models as models_module
        original_db = models_module.db
        models_module.db = db_connection

        try:
            result = SemanticModel.upsert(
                file_path=sample_semantic_data['file_path'],
                content_hash=sample_semantic_data['content_hash'],
                summary=sample_semantic_data['summary'],
                topics=sample_semantic_data['topics'],
                keywords=sample_semantic_data['keywords'],
                impact_level=sample_semantic_data['impact_level'],
                timestamp=datetime.fromtimestamp(sample_semantic_data['timestamp'])
            )

            assert result is not None
        finally:
            models_module.db = original_db

    @pytest.mark.unit
    @pytest.mark.ai
    def test_search_by_topic(self, db_connection):
        """Test searching semantic data by topic."""
        import database.models as models_module
        original_db = models_module.db
        models_module.db = db_connection

        try:
            # Insert semantic data
            SemanticModel.upsert(
                file_path="topic_test.py",
                content_hash="hash123",
                summary="Test file",
                topics=["testing", "python"],
                keywords=["test"],
                impact_level="minor",
                timestamp=datetime.now()
            )

            # Search by topic
            results = SemanticModel.search_by_topic("testing")
            assert len(results) > 0
            assert any("testing" in r.get('topics', []) for r in results)
        finally:
            models_module.db = original_db


class TestConfigModel:
    """Test the ConfigModel class."""

    @pytest.mark.unit
    def test_set_and_get_config(self, db_connection):
        """Test setting and getting configuration values."""
        import database.models as models_module
        original_db = models_module.db
        models_module.db = db_connection

        try:
            # Set config
            ConfigModel.set("test_key", "test_value")

            # Get config
            value = ConfigModel.get("test_key")
            assert value == "test_value"
        finally:
            models_module.db = original_db

    @pytest.mark.unit
    def test_get_nonexistent_config(self, db_connection):
        """Test getting a non-existent config key."""
        import database.models as models_module
        original_db = models_module.db
        models_module.db = db_connection

        try:
            value = ConfigModel.get("nonexistent_key", default="default_value")
            assert value == "default_value"
        finally:
            models_module.db = original_db

    @pytest.mark.unit
    def test_update_config(self, db_connection):
        """Test updating an existing config value."""
        import database.models as models_module
        original_db = models_module.db
        models_module.db = db_connection

        try:
            # Set initial value
            ConfigModel.set("update_test", "initial")
            assert ConfigModel.get("update_test") == "initial"

            # Update value
            ConfigModel.set("update_test", "updated")
            assert ConfigModel.get("update_test") == "updated"
        finally:
            models_module.db = original_db
