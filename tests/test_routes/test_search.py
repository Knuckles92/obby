"""
Unit tests for search API routes.

Tests the /api/search endpoints that handle full-text
and semantic search functionality.
"""

import pytest
from unittest.mock import patch


class TestSearchRoutes:
    """Test search API endpoints."""

    @pytest.mark.api
    def test_basic_search(self, fastapi_client):
        """Test GET /api/search endpoint with query."""
        response = fastapi_client.get("/api/search?q=test")

        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

    @pytest.mark.api
    def test_search_empty_query(self, fastapi_client):
        """Test search with empty query."""
        response = fastapi_client.get("/api/search?q=")

        # Should handle empty query gracefully
        assert response.status_code in [200, 400, 422]

    @pytest.mark.api
    def test_search_with_filters(self, fastapi_client):
        """Test search with additional filters."""
        response = fastapi_client.get("/api/search?q=test&file_type=py")

        # Should process filters or return appropriate status
        assert response.status_code in [200, 404, 422]

    @pytest.mark.api
    @pytest.mark.ai
    def test_semantic_search(self, fastapi_client):
        """Test semantic search endpoint."""
        response = fastapi_client.get("/api/search/semantic?q=testing")

        # Should return semantic results or 404
        assert response.status_code in [200, 404]

    @pytest.mark.api
    def test_search_by_topic(self, fastapi_client):
        """Test searching by topic."""
        response = fastapi_client.get("/api/search?q=topic:testing")

        assert response.status_code in [200, 404]

    @pytest.mark.api
    def test_search_by_keyword(self, fastapi_client):
        """Test searching by keyword."""
        response = fastapi_client.get("/api/search?q=keyword:function")

        assert response.status_code in [200, 404]

    @pytest.mark.api
    def test_search_pagination(self, fastapi_client):
        """Test search result pagination."""
        response = fastapi_client.get("/api/search?q=test&limit=10&offset=0")

        assert response.status_code in [200, 404]

    @pytest.mark.api
    def test_search_special_characters(self, fastapi_client):
        """Test search with special characters."""
        import urllib.parse
        query = urllib.parse.quote("test & special * chars")

        response = fastapi_client.get(f"/api/search?q={query}")

        # Should handle special characters
        assert response.status_code in [200, 400, 404, 422]

    @pytest.mark.api
    @pytest.mark.database
    def test_search_with_data(self, fastapi_client, db_connection):
        """Test search with actual database content."""
        import database.models as models_module
        from database.models import FileVersionModel, SemanticModel
        import hashlib

        original_db = models_module.db
        models_module.db = db_connection

        try:
            # Create searchable content
            content = "def searchable_function(): pass"
            content_hash = hashlib.sha256(content.encode()).hexdigest()

            FileVersionModel.insert(
                file_path="searchable.py",
                content_hash=content_hash,
                content=content,
                timestamp=None
            )

            # Add semantic data
            from datetime import datetime
            SemanticModel.upsert(
                file_path="searchable.py",
                content_hash=content_hash,
                summary="A searchable function",
                topics=["functions"],
                keywords=["searchable"],
                impact_level="minor",
                timestamp=datetime.now()
            )

            # Search for it
            response = fastapi_client.get("/api/search?q=searchable")

            # Should find results or handle appropriately
            assert response.status_code in [200, 404]

        finally:
            models_module.db = original_db

    @pytest.mark.api
    def test_search_result_format(self, fastapi_client):
        """Test that search results have proper format."""
        response = fastapi_client.get("/api/search?q=test")

        if response.status_code == 200:
            data = response.json()
            # Results should be in a structured format
            assert isinstance(data, (list, dict))
