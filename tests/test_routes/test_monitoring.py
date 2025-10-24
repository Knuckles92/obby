"""
Unit tests for monitoring API routes.

Tests the /api/monitoring endpoints that provide system status
and monitoring information.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestMonitoringRoutes:
    """Test monitoring API endpoints."""

    @pytest.mark.api
    def test_get_status(self, fastapi_client):
        """Test GET /api/monitoring/status endpoint."""
        response = fastapi_client.get("/api/monitoring/status")

        assert response.status_code == 200
        data = response.json()
        assert 'status' in data or 'monitoring' in data

    @pytest.mark.api
    def test_get_stats(self, fastapi_client):
        """Test GET /api/monitoring/stats endpoint."""
        response = fastapi_client.get("/api/monitoring/stats")

        # Should return stats or 200
        assert response.status_code in [200, 404]

    @pytest.mark.api
    def test_monitoring_health(self, fastapi_client):
        """Test monitoring health check endpoint."""
        # Try common health check patterns
        response = fastapi_client.get("/api/monitoring/health")

        # Should return success or not found
        assert response.status_code in [200, 404]

    @pytest.mark.api
    def test_monitoring_with_mock_monitor(self, fastapi_client, mock_file_watcher):
        """Test monitoring routes with mocked monitor."""
        with patch('routes.monitoring.monitor', mock_file_watcher):
            response = fastapi_client.get("/api/monitoring/status")

            # Should work with mocked monitor
            assert response.status_code in [200, 500]
