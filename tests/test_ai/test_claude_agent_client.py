"""
Unit and integration tests for Claude Agent SDK client.

This module contains two types of tests:
1. Unit tests - Use mocked SDK, run fast, no external dependencies
2. Integration tests - Use real SDK, require API key, verify connectivity
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from pathlib import Path


# =============================================================================
# UNIT TESTS (Mocked - Always Run)
# =============================================================================

class TestClaudeAgentClientUnit:
    """Unit tests for ClaudeAgentClient using mocked SDK."""

    @pytest.mark.unit
    @pytest.mark.ai
    def test_client_initialization_mock(self, mock_claude_agent_client):
        """Test that mock client initializes correctly."""
        assert mock_claude_agent_client is not None
        assert mock_claude_agent_client.is_available() is True
        assert hasattr(mock_claude_agent_client, 'working_dir')

    @pytest.mark.unit
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_analyze_diff_mock(self, mock_claude_agent_client):
        """Test diff analysis with mocked SDK."""
        sample_diff = """
        + def new_feature(self):
        +     return "Hello World"
        - def old_feature(self):
        -     return "Goodbye"
        """

        result = await mock_claude_agent_client.analyze_diff(sample_diff)

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.unit
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_summarize_changes_mock(self, mock_claude_agent_client):
        """Test batch change summarization with mocked SDK."""
        changes = [
            {"path": "core/monitor.py", "type": "modified", "content": "Added monitoring"},
            {"path": "api/routes.py", "type": "modified", "content": "Updated endpoints"},
        ]

        result = await mock_claude_agent_client.summarize_changes(changes)

        assert result is not None
        assert isinstance(result, str)
        assert "•" in result  # Should contain bullet points

    @pytest.mark.unit
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_ask_question_mock(self, mock_claude_agent_client):
        """Test question answering with mocked SDK."""
        question = "What are the main components?"
        context = "This is a test project"

        result = await mock_claude_agent_client.ask_question(question, context)

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.unit
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_generate_comprehensive_summary_mock(self, mock_claude_agent_client):
        """Test comprehensive summary generation with mocked SDK."""
        file_summaries = [
            {'file_path': 'test.py', 'summary': '1 change (+5/-2 lines)'},
            {'file_path': 'config.py', 'summary': '2 changes (+10/-3 lines)'}
        ]

        result = await mock_claude_agent_client.generate_comprehensive_summary(
            changes_context="Test diff content",
            file_summaries=file_summaries,
            time_span="2 hours",
            summary_length="brief"
        )

        assert result is not None
        assert isinstance(result, str)
        # Should contain structured sections
        assert "**Summary**" in result or "Summary" in result
        assert "**Key Topics**" in result or "Topics" in result
        assert "**Key Keywords**" in result or "Keywords" in result
        assert "**Overall Impact**" in result or "Impact" in result

    @pytest.mark.unit
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_comprehensive_summary_response_parsing(self, mock_claude_agent_client):
        """Test that comprehensive summary response can be parsed correctly."""
        file_summaries = [{'file_path': 'test.py', 'summary': '1 change'}]

        result = await mock_claude_agent_client.generate_comprehensive_summary(
            changes_context="test",
            file_summaries=file_summaries,
            time_span="1 hour"
        )

        # Verify the response format matches what ComprehensiveSummaryService expects
        lines = result.split('\n')
        assert any('Summary' in line for line in lines)
        assert any('Topics' in line or 'Keywords' in line for line in lines)

    @pytest.mark.unit
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_interactive_analysis_mock(self, mock_claude_agent_client):
        """Test interactive analysis generator with mocked SDK."""
        messages = []
        async for message in mock_claude_agent_client.interactive_analysis("Analyze this code"):
            messages.append(message)

        assert len(messages) > 0
        assert all(isinstance(msg, str) for msg in messages)

    @pytest.mark.unit
    @pytest.mark.ai
    def test_is_available_mock(self, mock_claude_agent_client):
        """Test availability check with mocked SDK."""
        assert mock_claude_agent_client.is_available() is True

    # ==========================================================================
    # NEW: Session Summary Methods Tests (Migration from OpenAI)
    # ==========================================================================

    @pytest.mark.unit
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_summarize_session_mock(self, mock_claude_agent_client):
        """Test session summary generation with file exploration."""
        changed_files = [
            "services/session_summary_service.py",
            "ai/claude_agent_client.py",
            "tests/test_ai/test_claude_agent_client.py"
        ]
        time_range = "last 2 hours"

        result = await mock_claude_agent_client.summarize_session(
            changed_files=changed_files,
            time_range=time_range,
            working_dir=None
        )

        # Verify structured format
        assert result is not None
        assert isinstance(result, str)
        assert "## " in result  # Should have title
        assert "**Summary**:" in result
        assert "**Change Pattern**:" in result
        assert "**Impact Assessment**:" in result
        assert "**Scope**:" in result
        assert "**Complexity**:" in result
        assert "**Risk Level**:" in result
        assert "**Topics**:" in result
        assert "**Technical Keywords**:" in result
        assert "### Sources" in result
        assert "### Proposed Questions" in result
        assert "### Metrics" in result

    @pytest.mark.unit
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_summarize_session_with_empty_files(self, mock_claude_agent_client):
        """Test session summary with no files."""
        result = await mock_claude_agent_client.summarize_session(
            changed_files=[],
            time_range="last hour",
            working_dir=None
        )

        # Should still return valid summary
        assert result is not None
        assert isinstance(result, str)

    @pytest.mark.unit
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_summarize_file_change_mock(self, mock_claude_agent_client):
        """Test individual file change summary."""
        result = await mock_claude_agent_client.summarize_file_change(
            file_path="services/session_summary_service.py",
            change_type="modified",
            working_dir=None
        )

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
        assert "services/session_summary_service.py" in result

    @pytest.mark.unit
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_generate_session_title_single_file(self, mock_claude_agent_client):
        """Test session title generation for single file."""
        changed_files = ["README.md"]

        result = await mock_claude_agent_client.generate_session_title(
            changed_files=changed_files,
            context_summary=None
        )

        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0
        assert len(result) < 100  # Should be concise

    @pytest.mark.unit
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_generate_session_title_multiple_files(self, mock_claude_agent_client):
        """Test session title generation for multiple files."""
        changed_files = [
            "tests/test_ai/test_claude.py",
            "tests/conftest.py",
            "tests/test_services/test_summary.py"
        ]

        result = await mock_claude_agent_client.generate_session_title(
            changed_files=changed_files,
            context_summary="Enhanced test coverage"
        )

        assert result is not None
        assert isinstance(result, str)
        assert "test" in result.lower() or "enhanced" in result.lower()

    @pytest.mark.unit
    @pytest.mark.ai
    @pytest.mark.asyncio
    async def test_generate_follow_up_questions_mock(self, mock_claude_agent_client):
        """Test follow-up question generation."""
        changed_files = ["services/session_summary_service.py"]
        summary_context = "Migrated from OpenAI to Claude Agent SDK"

        result = await mock_claude_agent_client.generate_follow_up_questions(
            changed_files=changed_files,
            summary_context=summary_context,
            working_dir=None
        )

        assert result is not None
        assert isinstance(result, list)
        assert len(result) >= 2  # Should generate 2-4 questions
        assert len(result) <= 4
        assert all(isinstance(q, str) for q in result)
        assert all(len(q) > 10 for q in result)  # Questions should be substantial


# =============================================================================
# INTEGRATION TESTS (Real SDK - Manual Run)
# =============================================================================

class TestClaudeAgentClientIntegration:
    """Integration tests for ClaudeAgentClient using real SDK."""

    @pytest.mark.integration
    @pytest.mark.ai
    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY"),
        reason="ANTHROPIC_API_KEY not set - skipping integration test"
    )
    def test_sdk_importable(self):
        """Test that Claude Agent SDK can be imported."""
        try:
            from claude_agent_sdk import query, ClaudeAgentOptions
            assert query is not None
            assert ClaudeAgentOptions is not None
        except ImportError as e:
            pytest.fail(f"Failed to import claude_agent_sdk: {e}")

    @pytest.mark.integration
    @pytest.mark.ai
    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY"),
        reason="ANTHROPIC_API_KEY not set - skipping integration test"
    )
    def test_client_real_initialization(self):
        """Test that real ClaudeAgentClient can be initialized."""
        try:
            from ai.claude_agent_client import ClaudeAgentClient

            client = ClaudeAgentClient(working_dir=Path.cwd())
            assert client is not None
            assert client.working_dir == Path.cwd()
            assert client.is_available() is True
        except Exception as e:
            pytest.fail(f"Failed to initialize ClaudeAgentClient: {e}")

    @pytest.mark.integration
    @pytest.mark.ai
    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY"),
        reason="ANTHROPIC_API_KEY not set - skipping integration test"
    )
    @pytest.mark.asyncio
    async def test_simple_query_real(self):
        """Test a simple query with real SDK to verify connectivity."""
        from ai.claude_agent_client import ClaudeAgentClient

        client = ClaudeAgentClient(working_dir=Path.cwd())

        if not client.is_available():
            pytest.skip("Claude Agent SDK not available")

        try:
            result = await client.ask_question(
                "What is 2 + 2? Just answer with the number.",
                context=None
            )

            assert result is not None
            assert isinstance(result, str)
            assert len(result) > 0
            # Should contain the answer "4" somewhere
            assert "4" in result or "four" in result.lower()
        except Exception as e:
            pytest.fail(f"Simple query failed: {e}")

    @pytest.mark.integration
    @pytest.mark.ai
    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY"),
        reason="ANTHROPIC_API_KEY not set - skipping integration test"
    )
    @pytest.mark.asyncio
    async def test_file_read_capability_real(self, temp_dir):
        """Test that Claude can read files using the Read tool."""
        from ai.claude_agent_client import ClaudeAgentClient

        client = ClaudeAgentClient(working_dir=temp_dir)

        if not client.is_available():
            pytest.skip("Claude Agent SDK not available")

        # Create a test file
        test_file = temp_dir / "test_integration.txt"
        test_content = "Integration test content for Claude Agent SDK"
        test_file.write_text(test_content)

        try:
            result = await client.ask_question(
                f"Read the file 'test_integration.txt' and tell me what it says.",
                context="Use your Read tool to examine the file."
            )

            assert result is not None
            assert isinstance(result, str)
            # Should mention something from the file content
            assert "integration" in result.lower() or "test" in result.lower()
        except Exception as e:
            pytest.fail(f"File read test failed: {e}")
        finally:
            # Cleanup
            if test_file.exists():
                test_file.unlink()

    @pytest.mark.integration
    @pytest.mark.ai
    @pytest.mark.skipif(
        not os.getenv("ANTHROPIC_API_KEY"),
        reason="ANTHROPIC_API_KEY not set - skipping integration test"
    )
    @pytest.mark.asyncio
    async def test_comprehensive_summary_real_minimal(self):
        """Test comprehensive summary with minimal real data."""
        from ai.claude_agent_client import ClaudeAgentClient

        client = ClaudeAgentClient(working_dir=Path.cwd())

        if not client.is_available():
            pytest.skip("Claude Agent SDK not available")

        # Minimal test data
        file_summaries = [
            {
                'file_path': 'README.md',
                'summary': '1 change (+5/-2 lines)'
            }
        ]

        try:
            result = await client.generate_comprehensive_summary(
                changes_context="+ Added documentation\n- Removed outdated info",
                file_summaries=file_summaries,
                time_span="1 hour",
                summary_length="brief"
            )

            assert result is not None
            assert isinstance(result, str)
            assert len(result) > 0
            # Should not start with "Error"
            assert not result.startswith("Error")
        except Exception as e:
            pytest.fail(f"Comprehensive summary integration test failed: {e}\n"
                       f"This may indicate an issue with the Claude CLI or SDK configuration.")


# =============================================================================
# SERVICE LAYER INTEGRATION TESTS
# =============================================================================

class TestComprehensiveSummaryService:
    """Tests for the ComprehensiveSummaryService using Claude Agent SDK."""

    @pytest.mark.unit
    @pytest.mark.ai
    def test_service_initialization(self):
        """Test that ComprehensiveSummaryService can be initialized."""
        from services.comprehensive_summary_service import ComprehensiveSummaryService

        service = ComprehensiveSummaryService()
        assert service is not None

    @pytest.mark.unit
    @pytest.mark.ai
    def test_fingerprint_combined(self):
        """Test fingerprint generation for deduplication."""
        from services.comprehensive_summary_service import ComprehensiveSummaryService

        fp1 = ComprehensiveSummaryService.fingerprint_combined(
            files_count=5,
            total_changes=10,
            combined_diff="test diff content"
        )

        fp2 = ComprehensiveSummaryService.fingerprint_combined(
            files_count=5,
            total_changes=10,
            combined_diff="test diff content"
        )

        # Same inputs should produce same fingerprint
        assert fp1 == fp2
        assert len(fp1) == 64  # SHA256 hex digest

    @pytest.mark.unit
    @pytest.mark.ai
    def test_prepare_combined_diff(self):
        """Test diff combination and truncation."""
        from services.comprehensive_summary_service import ComprehensiveSummaryService

        changes_by_file = {
            'file1.py': [
                {'diff_content': 'diff1', 'timestamp': '2024-01-01'}
            ],
            'file2.py': [
                {'diff_content': 'diff2', 'timestamp': '2024-01-02'}
            ]
        }

        result = ComprehensiveSummaryService.prepare_combined_diff(
            changes_by_file,
            max_len=500
        )

        assert 'file1.py' in result
        assert 'file2.py' in result
        assert len(result) <= 600  # Should respect max_len with buffer

    @pytest.mark.unit
    @pytest.mark.ai
    def test_calculate_time_span(self):
        """Test time span calculation."""
        from services.comprehensive_summary_service import ComprehensiveSummaryService
        from datetime import datetime, timedelta

        end_time = datetime.now()
        start_time = end_time - timedelta(hours=3)

        result = ComprehensiveSummaryService.calculate_time_span(start_time, end_time)

        assert "3 hour" in result

    @pytest.mark.unit
    @pytest.mark.ai
    def test_prepare_file_summaries(self):
        """Test file summary preparation."""
        from services.comprehensive_summary_service import ComprehensiveSummaryService

        changes_by_file = {
            'test.py': [
                {'lines_added': 5, 'lines_removed': 2, 'diff_content': '--- a/test.py\n+++ b/test.py\n+def foo():\n+    return 1\n'},
                {'lines_added': 3, 'lines_removed': 1, 'diff_content': '+# Added documentation\n'}
            ]
        }

        result = ComprehensiveSummaryService.prepare_file_summaries(changes_by_file)

        assert len(result) == 1
        assert result[0]['file_path'] == 'test.py'
        assert result[0]['changes_count'] == 2
        assert result[0]['lines_added'] == 8
        assert result[0]['lines_removed'] == 3
        assert 'def foo():' in result[0]['highlights']

    @pytest.mark.unit
    @pytest.mark.ai
    def test_parse_ai_summary(self):
        """Test AI summary parsing."""
        from services.comprehensive_summary_service import ComprehensiveSummaryService

        ai_response = """**Summary**: Test changes made to the codebase.

**Key Topics**: testing, refactoring, documentation

**Key Keywords**: pytest, mock, fixtures

**Overall Impact**: moderate"""

        parsed = ComprehensiveSummaryService.parse_ai_summary(ai_response)

        assert parsed['summary'] == 'Test changes made to the codebase.'
        assert 'testing' in parsed['topics']
        assert 'pytest' in parsed['keywords']
        assert parsed['impact'] == 'moderate'
