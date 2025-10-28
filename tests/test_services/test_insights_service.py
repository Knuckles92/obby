"""
Test suite for Insights Service
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from services.insights_service import InsightsService, InsightsGenerator, Insight, InsightCategory


class TestInsight:
    """Test Insight model"""
    
    def test_insight_creation(self):
        """Test creating an Insight object"""
        insight = Insight(
            category=InsightCategory.ACTION,
            priority="high",
            title="Test Insight",
            content="This is a test insight",
            related_files=["file1.py", "file2.py"],
            evidence={"reasoning": "test reasoning"}
        )
        
        assert insight.category == InsightCategory.ACTION
        assert insight.priority == "high"
        assert insight.title == "Test Insight"
        assert insight.dismissed is False
        assert insight.archived is False
        assert insight.id is not None
    
    def test_insight_to_dict(self):
        """Test converting Insight to dictionary"""
        insight = Insight(
            category=InsightCategory.PATTERN,
            priority="medium",
            title="Pattern Test",
            content="Pattern detected",
            related_files=["file1.py"],
            evidence={"data_points": [1, 2, 3]}
        )
        
        result = insight.to_dict()
        
        assert result['category'] == InsightCategory.PATTERN
        assert result['priority'] == "medium"
        assert result['title'] == "Pattern Test"
        assert result['relatedFiles'] == ["file1.py"]
        assert result['evidence']['data_points'] == [1, 2, 3]
        assert 'timestamp' in result


class TestInsightsGenerator:
    """Test InsightsGenerator class"""
    
    @pytest.fixture
    def generator(self):
        """Create InsightsGenerator instance with mocked dependencies"""
        with patch('services.insights_service.FileQueries'), \
             patch('services.insights_service.ClaudeAgentClient'), \
             patch('services.insights_service.WatchHandler'), \
             patch('services.insights_service.NotesSearchTool'):
            return InsightsGenerator()
    
    @pytest.mark.asyncio
    async def test_generate_insights_success(self, generator):
        """Test successful insight generation"""
        # Mock the context gathering
        mock_context = {
            'time_range': {'days': 7},
            'total_files': 5,
            'total_changes': 10
        }
        generator._gather_context_data = AsyncMock(return_value=mock_context)
        
        # Mock Claude analysis
        mock_insights_data = [
            {
                'category': 'action',
                'priority': 'high',
                'title': 'Test Action',
                'content': 'This is an action item',
                'related_files': ['file1.py'],
                'evidence': {'reasoning': 'test'},
                'id': 'test_insight_1'
            }
        ]
        generator._analyze_with_claude = AsyncMock(return_value=mock_insights_data)
        
        # Generate insights
        insights = await generator.generate_insights(time_range_days=7, max_insights=1)
        
        assert len(insights) == 1
        assert insights[0].category == 'action'
        assert insights[0].title == 'Test Action'
        assert insights[0].related_files == ['file1.py']
    
    @pytest.mark.asyncio
    async def test_generate_insights_failure(self, generator):
        """Test insight generation with error"""
        generator._gather_context_data = AsyncMock(side_effect=Exception("Test error"))
        
        insights = await generator.generate_insights()
        
        assert insights == []
    
    def test_analyze_topic_patterns(self, generator):
        """Test topic pattern analysis"""
        # Mock semantic data
        mock_semantic_data = [
            Mock(topics=['python', 'testing'], keywords=['pytest', 'mock']),
            Mock(topics=['python', 'api'], keywords=['fastapi', 'endpoint']),
            Mock(topics=['javascript'], keywords=['react', 'component'])
        ]
        
        result = generator._analyze_topic_patterns(mock_semantic_data)
        
        assert 'python' in result
        assert 'javascript' in result
        assert 'Top topics:' in result
        assert 'Top keywords:' in result
    
    def test_parse_insights_response_valid_json(self, generator):
        """Test parsing valid JSON response"""
        mock_response = Mock()
        mock_response.content = '''
        {
            "insights": [
                {
                    "category": "action",
                    "priority": "high",
                    "title": "Test",
                    "content": "Test content",
                    "related_files": ["file.py"]
                }
            ]
        }
        '''
        
        result = generator._parse_insights_response(mock_response)
        
        assert len(result) == 1
        assert result[0]['category'] == 'action'
        assert result[0]['title'] == 'Test'
    
    def test_parse_insights_response_invalid_json(self, generator):
        """Test parsing invalid JSON response"""
        mock_response = Mock()
        mock_response.content = 'Invalid JSON response'
        
        result = generator._parse_insights_response(mock_response)
        
        assert result == []


class TestInsightsService:
    """Test InsightsService class"""
    
    @pytest.fixture
    def service(self):
        """Create InsightsService instance with mocked generator"""
        with patch('services.insights_service.InsightsGenerator') as mock_generator_class, \
             patch('services.insights_service.FileQueries'):
            mock_generator = AsyncMock()
            mock_generator_class.return_value = mock_generator
            service = InsightsService()
            service.generator = mock_generator
            return service
    
    @pytest.mark.asyncio
    async def test_get_insights_success(self, service):
        """Test successful insights retrieval"""
        # Mock insight
        mock_insight = Insight(
            category=InsightCategory.OPPORTUNITY,
            priority="medium",
            title="Test Opportunity",
            content="Opportunity detected",
            related_files=["file1.py"],
            evidence={}
        )
        
        service.generator.generate_insights.return_value = [mock_insight]
        
        result = await service.get_insights(time_range_days=7, max_insights=5)
        
        assert len(result) == 1
        assert result[0]['category'] == InsightCategory.OPPORTUNITY
        assert result[0]['title'] == "Test Opportunity"
        assert service.generator.generate_insights.call_count == 1
    
    @pytest.mark.asyncio
    async def test_get_insights_failure(self, service):
        """Test insights retrieval with error"""
        service.generator.generate_insights.side_effect = Exception("Test error")
        
        result = await service.get_insights()
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_dismiss_insight(self, service):
        """Test dismissing an insight"""
        # Note: This is a placeholder since we haven't implemented persistence yet
        result = await service.dismiss_insight("test_insight_id")
        assert result is True
    
    @pytest.mark.asyncio
    async def test_archive_insight(self, service):
        """Test archiving an insight"""
        # Note: This is a placeholder since we haven't implemented persistence yet
        result = await service.archive_insight("test_insight_id")
        assert result is True


class TestInsightsIntegration:
    """Integration tests for Insights service"""
    
    @pytest.mark.asyncio
    async def test_insight_categories(self):
        """Test all insight categories are valid"""
        valid_categories = [
            InsightCategory.ACTION,
            InsightCategory.PATTERN,
            InsightCategory.RELATIONSHIP,
            InsightCategory.TEMPORAL,
            InsightCategory.OPPORTUNITY
        ]
        
        for category in valid_categories:
            insight = Insight(
                category=category,
                priority="medium",
                title=f"Test {category}",
                content=f"Test {category} content",
                related_files=["file.py"],
                evidence={}
            )
            
            assert insight.category == category
            assert category in InsightCategory.__dict__.values()
    
    @pytest.mark.asyncio
    async def test_insight_priorities(self):
        """Test all insight priorities are valid"""
        valid_priorities = ["low", "medium", "high", "critical"]
        
        for priority in valid_priorities:
            insight = Insight(
                category=InsightCategory.ACTION,
                priority=priority,
                title=f"Test {priority}",
                content=f"Test {priority} content",
                related_files=["file.py"],
                evidence={}
            )
            
            assert insight.priority == priority
            assert priority in valid_priorities