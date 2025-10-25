"""
API Key Validation Tests

This module provides layered validation for the OpenAI API key:
1. Soft validation: Checks that the environment variable exists and is not empty
2. Hard validation: Makes a real API call to verify the key works with OpenAI

Usage:
    # Run all tests including integration tests (costs API credits):
    pytest tests/test_ai/test_api_key_validation.py

    # Run only soft validation (no API calls):
    pytest tests/test_ai/test_api_key_validation.py -m "not integration"

    # Run only integration tests:
    pytest tests/test_ai/test_api_key_validation.py -m integration
"""

import pytest
import os
from openai import OpenAI, AuthenticationError, APIError


class TestAPIKeyPresence:
    """Soft validation: Check that API key exists in environment."""

    def test_openai_api_key_exists(self):
        """Test that OPENAI_API_KEY environment variable is set."""
        api_key = os.getenv("OPENAI_API_KEY")
        assert api_key is not None, (
            "OPENAI_API_KEY environment variable is not set. "
            "Please add it to your .env file."
        )

    def test_openai_api_key_not_empty(self):
        """Test that OPENAI_API_KEY is not an empty string."""
        api_key = os.getenv("OPENAI_API_KEY")
        assert api_key, (
            "OPENAI_API_KEY environment variable is empty. "
            "Please add a valid API key to your .env file."
        )

    def test_openai_api_key_format(self):
        """Test that OPENAI_API_KEY has expected format (starts with sk-)."""
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:  # Only check format if key exists
            assert api_key.startswith("sk-"), (
                f"OPENAI_API_KEY appears to have invalid format. "
                f"Expected to start with 'sk-', got: {api_key[:10]}..."
            )


@pytest.mark.integration
class TestAPIKeyValidity:
    """Hard validation: Verify API key works with real OpenAI API calls."""

    def test_api_key_authentication(self):
        """
        Test that the API key successfully authenticates with OpenAI.

        This makes a minimal API call (list models) to verify the key works.
        Marked as integration test because it:
        - Makes real network requests
        - Costs API credits (minimal)
        - Requires internet connection
        """
        api_key = os.getenv("OPENAI_API_KEY")

        # Skip if no API key set (soft validation should catch this)
        if not api_key:
            pytest.skip("OPENAI_API_KEY not set, skipping authentication test")

        try:
            client = OpenAI(api_key=api_key)
            # Make a minimal API call to verify authentication
            # list_models is cheap and doesn't consume tokens
            models = client.models.list()
            assert models is not None, "API call returned None"
            assert len(models.data) > 0, "No models returned from API"

        except AuthenticationError as e:
            pytest.fail(
                f"API key authentication failed: {e}\n"
                f"Please check that your OPENAI_API_KEY in .env is valid."
            )
        except APIError as e:
            pytest.fail(
                f"OpenAI API error: {e}\n"
                f"This might be a temporary service issue."
            )
        except Exception as e:
            pytest.fail(
                f"Unexpected error during API validation: {e}"
            )

    @pytest.mark.slow
    def test_api_key_completion(self):
        """
        Test that the API key can successfully generate completions.

        This makes a real completion request to thoroughly validate the key.
        Marked as slow because it:
        - Takes longer than list_models
        - Costs more API credits
        - Is more thorough validation
        """
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            pytest.skip("OPENAI_API_KEY not set, skipping completion test")

        try:
            client = OpenAI(api_key=api_key)

            # Make a minimal completion request
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Use cheapest model for testing
                messages=[
                    {"role": "user", "content": "Reply with just the word: OK"}
                ],
                max_tokens=5,
                temperature=0
            )

            assert response is not None, "Completion returned None"
            assert len(response.choices) > 0, "No completion choices returned"
            assert response.choices[0].message.content, "Completion content is empty"

            print(f"\n✅ API key validated successfully")
            print(f"   Model used: {response.model}")
            print(f"   Response: {response.choices[0].message.content}")

        except AuthenticationError as e:
            pytest.fail(
                f"API key authentication failed during completion: {e}\n"
                f"Please check that your OPENAI_API_KEY in .env is valid."
            )
        except APIError as e:
            pytest.fail(
                f"OpenAI API error during completion: {e}\n"
                f"This might be a quota or rate limit issue."
            )
        except Exception as e:
            pytest.fail(
                f"Unexpected error during completion test: {e}"
            )
