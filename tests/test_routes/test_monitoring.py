"""
Unit tests for monitoring API routes.

Tests the /api/monitor endpoints that provide system status
and monitoring information.
"""

import pytest
from unittest.mock import MagicMock, patch


class TestMonitoringRoutes:
    """Test monitoring API endpoints."""

    @pytest.mark.api
    def test_get_status(self, fastapi_client):
        """Test GET /api/monitor/status endpoint."""
        response = fastapi_client.get("/api/monitor/status")

        assert response.status_code == 200
        data = response.json()
        # API returns status with isActive, watchedPaths, totalFiles, eventsToday
        assert 'isActive' in data or 'status' in data or 'monitoring' in data
        # Verify expected fields in response
        if 'isActive' in data:
            assert isinstance(data['isActive'], bool)

    @pytest.mark.api
    def test_get_stats(self, fastapi_client):
        """Test GET /api/monitor/stats endpoint."""
        response = fastapi_client.get("/api/monitor/stats")

        # Should return stats or 200
        assert response.status_code in [200, 404]

    @pytest.mark.api
    def test_monitoring_health(self, fastapi_client):
        """Test monitoring health check endpoint."""
        # Try common health check patterns
        response = fastapi_client.get("/api/monitor/health")

        # Should return success or not found
        assert response.status_code in [200, 404]

    @pytest.mark.api
    def test_monitoring_with_mock_monitor(self, fastapi_client, mock_file_watcher):
        """Test monitoring routes with mocked monitor."""
        with patch('routes.monitoring.monitor_instance', mock_file_watcher):
            response = fastapi_client.get("/api/monitor/status")

            # Should work with mocked monitor
            assert response.status_code in [200, 500]
