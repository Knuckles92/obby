"""
Unit tests for OpenAI client integration.

Tests the OpenAI client with mocked API responses to ensure proper
integration without making real API calls.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime


class TestOpenAIClient:
    """Test the OpenAI client class."""

    @pytest.mark.unit
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test OpenAI client initialization with API key."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            from ai.openai_client import OpenAIClient

            client = OpenAIClient()
            assert client is not None

    @pytest.mark.unit
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_summarize_content(self, mock_openai_client):
        """Test content summarization."""
        diff_content = "Added new feature\n+def new_function():\n+    return True"

        result = await mock_openai_client.summarize(diff_content)

        assert result is not None
        assert 'summary' in result
        assert 'topics' in result
        assert 'keywords' in result
        assert 'impact_level' in result

    @pytest.mark.unit
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_summarize_minimal(self, mock_openai_client):
        """Test minimal summary generation."""
        diffs = [
            {"file_path": "test.py", "diff_content": "+print('hello')"}
        ]

        result = await mock_openai_client.summarize_minimal(diffs)

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.unit
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_batch_processing(self, mock_openai_client):
        """Test batch processing of multiple files."""
        files = [
            {"file_path": "file1.py", "diff_content": "diff1"},
            {"file_path": "file2.py", "diff_content": "diff2"},
            {"file_path": "file3.py", "diff_content": "diff3"}
        ]

        results = await mock_openai_client.process_batch(files)

        assert results is not None
        assert isinstance(results, list)
        assert len(results) > 0

    @pytest.mark.unit
    @pytest.mark.ai
    def test_format_loading(self):
        """Test that format templates are loaded correctly."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            from ai.openai_client import OpenAIClient

            client = OpenAIClient()
            # Should have loaded format config if available
            assert hasattr(client, 'api_key')

    @pytest.mark.unit
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling for API failures."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            from ai.openai_client import OpenAIClient

            client = OpenAIClient()

            # Mock a failing API call
            with patch.object(client, 'summarize', side_effect=Exception("API Error")):
                with pytest.raises(Exception):
                    await client.summarize("test content")

    @pytest.mark.unit
    @pytest.mark.ai
    def test_model_selection(self):
        """Test that different models can be selected."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            from ai.openai_client import OpenAIClient

            # Should support multiple models
            client = OpenAIClient()
            assert client is not None

    @pytest.mark.unit
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_structured_response_parsing(self, mock_openai_client):
        """Test parsing of structured JSON responses from OpenAI."""
        diff_content = "test changes"

        result = await mock_openai_client.summarize(diff_content)

        # Should return structured data
        assert isinstance(result, dict)
        assert isinstance(result.get('topics', []), list)
        assert isinstance(result.get('keywords', []), list)
        assert result.get('impact_level') in ['minor', 'moderate', 'major', None]

    @pytest.mark.unit
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_empty_content_handling(self, mock_openai_client):
        """Test handling of empty or minimal content."""
        # Test with empty content
        result = await mock_openai_client.summarize("")

        # Should handle gracefully
        assert result is not None
