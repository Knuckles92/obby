import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import json

from services.insights_service import InsightsService
from services.insights_aggregator import InsightsAggregator
from database.models import InsightModel
from utils.watch_handler import WatchHandler


class TestInsightsService:
    """Test suite for InsightsService"""

    @pytest.fixture
    def mock_watch_handler(self):
        """Mock watch handler"""
        handler = Mock(spec=WatchHandler)
        handler.is_watched.return_value = True
        return handler

    @pytest.fixture
    def mock_aggregator(self):
        """Mock insights aggregator"""
        aggregator = Mock(spec=InsightsAggregator)
        aggregator.aggregate_insights = AsyncMock()
        return aggregator

    @pytest.fixture
    def insights_service(self, mock_watch_handler, mock_aggregator):
        """Create insights service with mocked dependencies"""
        return InsightsService(
            watch_handler=mock_watch_handler,
            aggregator=mock_aggregator
        )

    @pytest.mark.asyncio
    async def test_get_insights_success(self, insights_service, mock_aggregator):
        """Test successful insights retrieval"""
        # Mock aggregator response
        mock_insights = [
            {
                'id': 'insight_1',
                'category': 'quality',
                'priority': 'high',
                'title': 'Code Quality Issue',
                'content': 'Potential code duplication detected',
                'related_files': ['src/utils.py', 'src/helpers.py'],
                'evidence': {
                    'reasoning': 'Similar code patterns found across multiple files',
                    'data_points': ['Duplicate function in utils.py and helpers.py'],
                    'generated_by_agent': 'claude-sonnet'
                },
                'timestamp': datetime.now().isoformat(),
                'dismissed': False,
                'archived': False,
                'source_section': 'semantic'
            }
        ]
        mock_aggregator.aggregate_insights.return_value = mock_insights

        # Test the service method
        result = await insights_service.get_insights(
            time_range_days=7,
            max_insights=10,
            category='quality',
            include_dismissed=False
        )

        # Verify aggregator was called with correct parameters
        mock_aggregator.aggregate_insights.assert_called_once_with(
            time_range_days=7,
            max_insights=10,
            category='quality',
            include_dismissed=False
        )

        # Verify result structure
        assert result['success'] is True
        assert 'data' in result
        assert 'metadata' in result
        assert len(result['data']) == 1
        assert result['data'][0]['id'] == 'insight_1'
        assert result['data'][0]['category'] == 'quality'

    @pytest.mark.asyncio
    async def test_get_insights_with_filters(self, insights_service, mock_aggregator):
        """Test insights retrieval with various filters"""
        mock_insights = [
            {
                'id': 'insight_1',
                'category': 'quality',
                'priority': 'high',
                'title': 'Quality Issue',
                'content': 'Test content',
                'related_files': [],
                'timestamp': datetime.now().isoformat(),
                'dismissed': False,
                'archived': False
            },
            {
                'id': 'insight_2',
                'category': 'velocity',
                'priority': 'medium',
                'title': 'Velocity Issue',
                'content': 'Test content',
                'related_files': [],
                'timestamp': datetime.now().isoformat(),
                'dismissed': True,
                'archived': False
            }
        ]
        mock_aggregator.aggregate_insights.return_value = mock_insights

        # Test with priority filter
        result = await insights_service.get_insights(
            time_range_days=7,
            max_insights=10,
            priority='high'
        )

        assert result['success'] is True
        assert len(result['data']) == 1
        assert result['data'][0]['priority'] == 'high'

    @pytest.mark.asyncio
    async def test_get_insight_by_id_success(self, insights_service):
        """Test successful insight retrieval by ID"""
        # Mock database query
        mock_insight = InsightModel(
            id='insight_1',
            category='quality',
            priority='high',
            title='Test Insight',
            content='Test content',
            related_files='["test.py"]',
            evidence='{"reasoning": "test"}',
            timestamp=datetime.now(),
            dismissed=False,
            archived=False
        )

        with patch.object(insights_service, '_get_insight_from_db') as mock_get:
            mock_get.return_value = mock_insight

            result = await insights_service.get_insight_by_id('insight_1')

            assert result['success'] is True
            assert result['data']['id'] == 'insight_1'
            assert result['data']['category'] == 'quality'

    @pytest.mark.asyncio
    async def test_get_insight_by_id_not_found(self, insights_service):
        """Test insight retrieval when ID not found"""
        with patch.object(insights_service, '_get_insight_from_db') as mock_get:
            mock_get.return_value = None

            result = await insights_service.get_insight_by_id('nonexistent')

            assert result['success'] is False
            assert 'Insight not found' in result['error']

    @pytest.mark.asyncio
    async def test_dismiss_insight_success(self, insights_service):
        """Test successful insight dismissal"""
        mock_insight = InsightModel(
            id='insight_1',
            category='quality',
            priority='high',
            title='Test Insight',
            content='Test content',
            related_files='[]',
            evidence='{}',
            timestamp=datetime.now(),
            dismissed=False,
            archived=False
        )

        with patch.object(insights_service, '_get_insight_from_db') as mock_get, \
             patch.object(insights_service, '_update_insight_in_db') as mock_update:
            
            mock_get.return_value = mock_insight
            mock_update.return_value = True

            result = await insights_service.dismiss_insight('insight_1')

            assert result['success'] is True
            mock_update.assert_called_once_with('insight_1', dismissed=True)

    @pytest.mark.asyncio
    async def test_archive_insight_success(self, insights_service):
        """Test successful insight archival"""
        mock_insight = InsightModel(
            id='insight_1',
            category='quality',
            priority='high',
            title='Test Insight',
            content='Test content',
            related_files='[]',
            evidence='{}',
            timestamp=datetime.now(),
            dismissed=False,
            archived=False
        )

        with patch.object(insights_service, '_get_insight_from_db') as mock_get, \
             patch.object(insights_service, '_update_insight_in_db') as mock_update:
            
            mock_get.return_value = mock_insight
            mock_update.return_value = True

            result = await insights_service.archive_insight('insight_1')

            assert result['success'] is True
            mock_update.assert_called_once_with('insight_1', archived=True)

    @pytest.mark.asyncio
    async def test_refresh_insights_success(self, insights_service, mock_aggregator):
        """Test successful insights refresh"""
        mock_insights = [
            {
                'id': 'new_insight_1',
                'category': 'quality',
                'priority': 'high',
                'title': 'New Insight',
                'content': 'Fresh analysis',
                'related_files': ['test.py'],
                'timestamp': datetime.now().isoformat(),
                'dismissed': False,
                'archived': False
            }
        ]
        mock_aggregator.aggregate_insights.return_value = mock_insights

        result = await insights_service.refresh_insights(
            time_range_days=7,
            max_insights=10,
            force_refresh=True
        )

        assert result['success'] is True
        assert len(result['data']) == 1
        assert result['data'][0]['id'] == 'new_insight_1'

    @pytest.mark.asyncio
    async def test_get_insights_stats(self, insights_service):
        """Test insights statistics retrieval"""
        with patch.object(insights_service, '_get_insights_stats_from_db') as mock_stats:
            mock_stats.return_value = {
                'total_insights': 25,
                'by_category': {
                    'quality': 8,
                    'velocity': 6,
                    'risk': 4,
                    'documentation': 3,
                    'follow-ups': 4
                },
                'by_priority': {
                    'critical': 3,
                    'high': 8,
                    'medium': 10,
                    'low': 4
                },
                'dismissed_count': 5,
                'archived_count': 3
            }

            result = await insights_service.get_insights_stats()

            assert result['success'] is True
            assert result['data']['total_insights'] == 25
            assert result['data']['by_category']['quality'] == 8
            assert result['data']['by_priority']['critical'] == 3

    def test_parse_insight_filters(self, insights_service):
        """Test insight filter parsing"""
        # Test no filters
        filters = insights_service._parse_insight_filters({})
        assert filters['category'] is None
        assert filters['priority'] is None
        assert filters['include_dismissed'] is False

        # Test with filters
        filters = insights_service._parse_insight_filters({
            'category': 'quality',
            'priority': 'high',
            'include_dismissed': 'true'
        })
        assert filters['category'] == 'quality'
        assert filters['priority'] == 'high'
        assert filters['include_dismissed'] is True

    def test_validate_insight_data(self, insights_service):
        """Test insight data validation"""
        # Valid insight
        valid_insight = {
            'category': 'quality',
            'priority': 'high',
            'title': 'Test Insight',
            'content': 'Test content'
        }
        assert insights_service._validate_insight_data(valid_insight) is True

        # Invalid category
        invalid_insight = {
            'category': 'invalid',
            'priority': 'high',
            'title': 'Test Insight',
            'content': 'Test content'
        }
        assert insights_service._validate_insight_data(invalid_insight) is False

        # Missing required field
        invalid_insight = {
            'category': 'quality',
            'priority': 'high',
            'content': 'Test content'
        }
        assert insights_service._validate_insight_data(invalid_insight) is False

    @pytest.mark.asyncio
    async def test_error_handling_in_aggregator(self, insights_service, mock_aggregator):
        """Test error handling when aggregator fails"""
        mock_aggregator.aggregate_insights.side_effect = Exception("Aggregator error")

        result = await insights_service.get_insights()

        assert result['success'] is False
        assert 'error' in result
        assert 'Aggregator error' in result['error']

    @pytest.mark.asyncio
    async def test_watch_filtering(self, insights_service, mock_watch_handler):
        """Test that watch filtering is applied"""
        # Mock unwatched file
        mock_watch_handler.is_watched.return_value = False

        result = await insights_service.get_insights()

        # Should return empty result when files are not watched
        assert result['success'] is True
        assert len(result['data']) == 0