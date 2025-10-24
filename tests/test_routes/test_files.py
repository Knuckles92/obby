"""
Unit tests for files API routes.

Tests the /api/files endpoints that handle file operations
and diff retrieval.
"""

import pytest
from unittest.mock import patch
import hashlib
from datetime import datetime


class TestFilesRoutes:
    """Test files API endpoints."""

    @pytest.mark.api
    def test_get_recent_diffs(self, fastapi_client):
        """Test GET /api/files/diffs endpoint."""
        response = fastapi_client.get("/api/files/diffs")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.api
    def test_get_diffs_with_pagination(self, fastapi_client):
        """Test diff retrieval with pagination parameters."""
        response = fastapi_client.get("/api/files/diffs?limit=5&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.api
    def test_get_file_versions(self, fastapi_client):
        """Test GET /api/files/{file_path}/versions endpoint."""
        # Encode file path for URL
        import urllib.parse
        file_path = urllib.parse.quote("test.py", safe='')

        response = fastapi_client.get(f"/api/files/{file_path}/versions")

        # Should return versions or 404
        assert response.status_code in [200, 404, 422]

    @pytest.mark.api
    @pytest.mark.database
    def test_get_diffs_with_data(self, fastapi_client, db_connection):
        """Test getting diffs with actual database data."""
        import database.models as models_module
        from database.models import FileVersionModel, ContentDiffModel

        original_db = models_module.db
        models_module.db = db_connection

        try:
            # Create test data
            h1 = hashlib.sha256("old".encode()).hexdigest()
            h2 = hashlib.sha256("new".encode()).hexdigest()

            v1 = FileVersionModel.insert("api_test.py", h1, "old", timestamp=datetime.now())
            v2 = FileVersionModel.insert("api_test.py", h2, "new", timestamp=datetime.now())

            ContentDiffModel.insert(
                file_path="api_test.py",
                old_version_id=v1,
                new_version_id=v2,
                change_type="modified",
                diff_content="test diff",
                timestamp=datetime.now()
            )

            # Query the endpoint
            response = fastapi_client.get("/api/files/diffs")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

        finally:
            models_module.db = original_db

    @pytest.mark.api
    def test_file_search(self, fastapi_client):
        """Test file search endpoint."""
        response = fastapi_client.get("/api/files/search?q=test")

        # Should return results or 404
        assert response.status_code in [200, 404]

    @pytest.mark.api
    def test_clear_missing_files(self, fastapi_client):
        """Test POST /api/files/clear-missing endpoint."""
        response = fastapi_client.post("/api/files/clear-missing")

        # Should process or return appropriate status
        assert response.status_code in [200, 404, 405]

    @pytest.mark.api
    def test_file_stats(self, fastapi_client):
        """Test retrieving file statistics."""
        response = fastapi_client.get("/api/files/stats")

        # Should return stats or 404
        assert response.status_code in [200, 404]

    @pytest.mark.api
    def test_invalid_file_path(self, fastapi_client):
        """Test handling of invalid file paths."""
        response = fastapi_client.get("/api/files/../../../../etc/passwd/versions")

        # Should reject invalid paths
        assert response.status_code in [400, 404, 422]

    @pytest.mark.api
    def test_get_diff_by_id(self, fastapi_client):
        """Test GET /api/files/diff/{diff_id} endpoint."""
        response = fastapi_client.get("/api/files/diff/1")

        # Should return diff or 404
        assert response.status_code in [200, 404, 422]

    @pytest.mark.api
    def test_pagination_limits(self, fastapi_client):
        """Test pagination with various limits."""
        # Test with different limit values
        for limit in [1, 10, 50, 100]:
            response = fastapi_client.get(f"/api/files/diffs?limit={limit}")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) <= limit
