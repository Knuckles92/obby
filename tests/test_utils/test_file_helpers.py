"""
Unit tests for file helper utilities.

Tests the file helper functions that provide common file operations
throughout the Obby application.
"""

import pytest
from pathlib import Path
from utils.file_helpers import (
    read_lines,
    ensure_directories,
    create_timestamp,
    setup_test_file
)


class TestFileHelpers:
    """Test file helper utility functions."""

    @pytest.mark.unit
    def test_read_lines_existing_file(self, temp_dir):
        """Test reading lines from an existing file."""
        test_file = temp_dir / "test.txt"
        test_content = "line1\nline2\nline3"
        test_file.write_text(test_content)

        lines = read_lines(test_file)

        assert len(lines) == 3
        assert lines[0] == "line1"
        assert lines[1] == "line2"
        assert lines[2] == "line3"

    @pytest.mark.unit
    def test_read_lines_nonexistent_file(self, temp_dir):
        """Test reading lines from a non-existent file."""
        test_file = temp_dir / "nonexistent.txt"

        lines = read_lines(test_file)

        assert lines == []

    @pytest.mark.unit
    def test_ensure_directories_single(self, temp_dir):
        """Test creating a single directory."""
        new_dir = temp_dir / "new_directory"

        ensure_directories(new_dir)

        assert new_dir.exists()
        assert new_dir.is_dir()

    @pytest.mark.unit
    def test_ensure_directories_multiple(self, temp_dir):
        """Test creating multiple directories."""
        dir1 = temp_dir / "dir1"
        dir2 = temp_dir / "dir2"
        dir3 = temp_dir / "dir3"

        ensure_directories(dir1, dir2, dir3)

        assert dir1.exists() and dir1.is_dir()
        assert dir2.exists() and dir2.is_dir()
        assert dir3.exists() and dir3.is_dir()

    @pytest.mark.unit
    def test_ensure_directories_existing(self, temp_dir):
        """Test that ensure_directories doesn't fail on existing directories."""
        existing_dir = temp_dir / "existing"
        existing_dir.mkdir()

        # Should not raise error
        ensure_directories(existing_dir)

        assert existing_dir.exists()

    @pytest.mark.unit
    def test_create_timestamp(self):
        """Test timestamp creation."""
        timestamp = create_timestamp()

        assert isinstance(timestamp, str)
        assert len(timestamp) > 0
        # Should contain date and time components
        assert "_" in timestamp
        assert "-" in timestamp

    @pytest.mark.unit
    def test_create_timestamp_format(self):
        """Test timestamp format matches expected pattern."""
        import re
        timestamp = create_timestamp()

        # Format should be: YYYY-MM-DD_HH-MM-SS
        pattern = r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}'
        assert re.match(pattern, timestamp)

    @pytest.mark.unit
    def test_setup_test_file_creates_file(self, temp_dir):
        """Test that setup_test_file creates a new file."""
        test_file = temp_dir / "test_note.md"

        setup_test_file(test_file)

        assert test_file.exists()
        assert test_file.is_file()

        # Check content
        content = test_file.read_text()
        assert "# My Notes" in content

    @pytest.mark.unit
    def test_setup_test_file_creates_parent_dir(self, temp_dir):
        """Test that setup_test_file creates parent directories."""
        test_file = temp_dir / "subdir" / "another" / "test_note.md"

        setup_test_file(test_file)

        assert test_file.parent.exists()
        assert test_file.exists()

    @pytest.mark.unit
    def test_setup_test_file_skips_existing(self, temp_dir):
        """Test that setup_test_file doesn't overwrite existing files."""
        test_file = temp_dir / "existing.md"
        original_content = "Original content"
        test_file.write_text(original_content)

        setup_test_file(test_file)

        # Content should remain unchanged
        assert test_file.read_text() == original_content
