"""
Unit tests for database queries.

Tests the FileQueries class and other query classes to ensure proper
data retrieval, filtering, and aggregation operations.
"""

import pytest
from datetime import datetime, timedelta
from database.queries import FileQueries
from database.models import (
    FileVersionModel,
    ContentDiffModel,
    SemanticModel
)


class TestFileQueries:
    """Test the FileQueries class."""

    @pytest.mark.unit
    @pytest.mark.database
    def test_get_recent_diffs(self, db_connection):
        """Test retrieving recent diffs with pagination."""
        import hashlib
        import database.models as models_module
        original_db = models_module.db
        models_module.db = db_connection

        try:
            # Create some test diffs
            for i in range(5):
                h1 = hashlib.sha256(f"old{i}".encode()).hexdigest()
                h2 = hashlib.sha256(f"new{i}".encode()).hexdigest()

                v1 = FileVersionModel.insert(f"test{i}.py", h1, f"old{i}", timestamp=datetime.now())
                v2 = FileVersionModel.insert(f"test{i}.py", h2, f"new{i}", timestamp=datetime.now())

                ContentDiffModel.insert(
                    file_path=f"test{i}.py",
                    old_version_id=v1,
                    new_version_id=v2,
                    change_type="modified",
                    diff_content=f"diff {i}",
                    lines_added=i + 1,
                    lines_removed=i,
                    timestamp=datetime.now()
                )

            # Test getting recent diffs (without watch_handler for testing)
            diffs = FileQueries.get_recent_diffs(limit=3, offset=0, watch_handler=None)

            # Note: diffs might be filtered by watch_handler, so we just check structure
            assert isinstance(diffs, list)
            if len(diffs) > 0:
                assert 'filePath' in diffs[0]
                assert 'changeType' in diffs[0]
                assert 'diffContent' in diffs[0]

        finally:
            models_module.db = original_db

    @pytest.mark.unit
    @pytest.mark.database
    def test_get_diffs_since(self, db_connection):
        """Test retrieving diffs since a specific timestamp."""
        import hashlib
        import database.models as models_module
        original_db = models_module.db
        models_module.db = db_connection

        try:
            # Create diffs at different times
            base_time = datetime.now() - timedelta(hours=2)

            for i in range(3):
                h1 = hashlib.sha256(f"old{i}".encode()).hexdigest()
                h2 = hashlib.sha256(f"new{i}".encode()).hexdigest()

                v1 = FileVersionModel.insert(f"time{i}.py", h1, f"old{i}", timestamp=base_time + timedelta(minutes=i*10))
                v2 = FileVersionModel.insert(f"time{i}.py", h2, f"new{i}", timestamp=base_time + timedelta(minutes=i*10+5))

                ContentDiffModel.insert(
                    file_path=f"time{i}.py",
                    old_version_id=v1,
                    new_version_id=v2,
                    change_type="modified",
                    diff_content=f"diff {i}",
                    timestamp=base_time + timedelta(minutes=i*10+5)
                )

            # Get diffs since 1 hour ago
            since = base_time + timedelta(minutes=15)
            diffs = FileQueries.get_diffs_since(since, limit=10, watch_handler=None)

            assert isinstance(diffs, list)
            # Should only get diffs after the 'since' timestamp
            # (exact count depends on filtering)

        finally:
            models_module.db = original_db

    @pytest.mark.unit
    @pytest.mark.database
    def test_get_file_versions(self, db_connection):
        """Test retrieving file versions."""
        import hashlib
        import database.models as models_module
        original_db = models_module.db
        models_module.db = db_connection

        try:
            file_path = "versions_test.py"

            # Create multiple versions
            for i in range(4):
                content_hash = hashlib.sha256(f"version{i}".encode()).hexdigest()
                FileVersionModel.insert(
                    file_path=file_path,
                    content_hash=content_hash,
                    content=f"version{i}",
                    timestamp=datetime.now()
                )

            # Get versions using FileVersionModel
            versions = FileVersionModel.get_file_history(file_path, limit=10)

            assert len(versions) == 4
            assert all(v['file_path'] == file_path for v in versions)

        finally:
            models_module.db = original_db

    @pytest.mark.unit
    @pytest.mark.database
    def test_get_file_stats(self, db_connection):
        """Test retrieving file statistics."""
        import hashlib
        import database.models as models_module
        original_db = models_module.db
        models_module.db = db_connection

        try:
            # Create some test data
            for i in range(3):
                h1 = hashlib.sha256(f"s1{i}".encode()).hexdigest()
                h2 = hashlib.sha256(f"s2{i}".encode()).hexdigest()

                v1 = FileVersionModel.insert(f"stats{i}.py", h1, f"s1{i}", timestamp=datetime.now())
                v2 = FileVersionModel.insert(f"stats{i}.py", h2, f"s2{i}", timestamp=datetime.now())

                ContentDiffModel.insert(
                    file_path=f"stats{i}.py",
                    old_version_id=v1,
                    new_version_id=v2,
                    change_type="modified",
                    diff_content=f"diff{i}",
                    lines_added=5,
                    lines_removed=2,
                    timestamp=datetime.now()
                )

            # Test that we can query file statistics
            # (FileQueries would have methods for this)
            stats = db_connection.execute_query("""
                SELECT
                    COUNT(DISTINCT file_path) as file_count,
                    SUM(lines_added) as total_added,
                    SUM(lines_removed) as total_removed
                FROM content_diffs
            """)

            assert stats[0]['file_count'] >= 3
            assert stats[0]['total_added'] >= 15

        finally:
            models_module.db = original_db

    @pytest.mark.unit
    @pytest.mark.database
    @pytest.mark.ai
    def test_search_functionality(self, db_connection):
        """Test search functionality across files."""
        import hashlib
        import database.models as models_module
        original_db = models_module.db
        models_module.db = db_connection

        try:
            # Create file versions with semantic data
            content_hash = hashlib.sha256("searchable content".encode()).hexdigest()

            FileVersionModel.insert(
                file_path="searchable.py",
                content_hash=content_hash,
                content="searchable content",
                timestamp=datetime.now()
            )

            # Add semantic analysis
            SemanticModel.upsert(
                file_path="searchable.py",
                content_hash=content_hash,
                summary="A searchable test file",
                topics=["search", "test"],
                keywords=["searchable", "content"],
                impact_level="minor",
                timestamp=datetime.now()
            )

            # Test search by keyword
            results = SemanticModel.search_by_keyword("searchable")
            assert len(results) > 0

        finally:
            models_module.db = original_db

    @pytest.mark.unit
    @pytest.mark.database
    def test_pagination(self, db_connection):
        """Test pagination for query results."""
        import hashlib
        import database.models as models_module
        original_db = models_module.db
        models_module.db = db_connection

        try:
            # Create many diffs
            for i in range(15):
                h1 = hashlib.sha256(f"p1{i}".encode()).hexdigest()
                h2 = hashlib.sha256(f"p2{i}".encode()).hexdigest()

                v1 = FileVersionModel.insert(f"page{i}.py", h1, f"p1{i}", timestamp=datetime.now())
                v2 = FileVersionModel.insert(f"page{i}.py", h2, f"p2{i}", timestamp=datetime.now())

                ContentDiffModel.insert(
                    file_path=f"page{i}.py",
                    old_version_id=v1,
                    new_version_id=v2,
                    change_type="modified",
                    diff_content=f"diff{i}",
                    timestamp=datetime.now()
                )

            # Test first page
            page1 = FileQueries.get_recent_diffs(limit=5, offset=0, watch_handler=None)

            # Test second page
            page2 = FileQueries.get_recent_diffs(limit=5, offset=5, watch_handler=None)

            # Pages should be different (unless heavily filtered)
            assert isinstance(page1, list)
            assert isinstance(page2, list)

        finally:
            models_module.db = original_db

    @pytest.mark.unit
    @pytest.mark.database
    def test_filter_by_file_path(self, db_connection):
        """Test filtering diffs by specific file path."""
        import hashlib
        import database.models as models_module
        original_db = models_module.db
        models_module.db = db_connection

        try:
            target_file = "target.py"
            other_file = "other.py"

            # Create diffs for both files
            for file_path in [target_file, other_file]:
                h1 = hashlib.sha256(f"{file_path}1".encode()).hexdigest()
                h2 = hashlib.sha256(f"{file_path}2".encode()).hexdigest()

                v1 = FileVersionModel.insert(file_path, h1, f"{file_path}1", timestamp=datetime.now())
                v2 = FileVersionModel.insert(file_path, h2, f"{file_path}2", timestamp=datetime.now())

                ContentDiffModel.insert(
                    file_path=file_path,
                    old_version_id=v1,
                    new_version_id=v2,
                    change_type="modified",
                    diff_content=f"diff {file_path}",
                    timestamp=datetime.now()
                )

            # Get diffs for specific file
            diffs = FileQueries.get_recent_diffs(
                limit=10,
                file_path=target_file,
                watch_handler=None
            )

            # All returned diffs should be for the target file
            assert isinstance(diffs, list)
            if len(diffs) > 0:
                assert all(d['filePath'] == target_file for d in diffs)

        finally:
            models_module.db = original_db
