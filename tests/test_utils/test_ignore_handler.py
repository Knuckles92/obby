"""
Unit tests for the ignore handler.

Tests the IgnoreHandler class that manages .obbyignore file patterns
for excluding files from monitoring.
"""

import pytest
from pathlib import Path
from utils.ignore_handler import IgnoreHandler


class TestIgnoreHandler:
    """Test the IgnoreHandler class."""

    @pytest.mark.unit
    def test_initialization(self, temp_dir):
        """Test IgnoreHandler initialization."""
        handler = IgnoreHandler(utils_folder=temp_dir, notes_folder=temp_dir)

        assert handler.utils_folder == temp_dir
        assert handler.notes_folder == temp_dir
        assert handler.ignore_file == temp_dir / ".obbyignore"

    @pytest.mark.unit
    def test_creates_default_ignore_file(self, temp_dir):
        """Test that initialization creates a default .obbyignore file."""
        handler = IgnoreHandler(utils_folder=temp_dir, notes_folder=temp_dir)

        assert handler.ignore_file.exists()
        content = handler.ignore_file.read_text()
        assert "# Obby ignore file" in content

    @pytest.mark.unit
    def test_load_ignore_patterns(self, temp_dir):
        """Test loading patterns from .obbyignore file."""
        ignore_file = temp_dir / ".obbyignore"
        ignore_file.write_text("*.tmp\n*.log\n# Comment line\n\n*.bak")

        handler = IgnoreHandler(utils_folder=temp_dir, notes_folder=temp_dir)

        assert len(handler.ignore_patterns) >= 3
        assert "*.tmp" in handler.ignore_patterns
        assert "*.log" in handler.ignore_patterns
        assert "*.bak" in handler.ignore_patterns
        assert "# Comment line" not in handler.ignore_patterns

    @pytest.mark.unit
    def test_should_ignore_by_extension(self, temp_dir):
        """Test ignoring files by extension pattern."""
        ignore_file = temp_dir / ".obbyignore"
        ignore_file.write_text("*.tmp")

        handler = IgnoreHandler(utils_folder=temp_dir, notes_folder=temp_dir)

        # Create test files
        tmp_file = temp_dir / "test.tmp"
        py_file = temp_dir / "test.py"

        assert handler.should_ignore(tmp_file) is True
        assert handler.should_ignore(py_file) is False

    @pytest.mark.unit
    def test_should_ignore_by_filename(self, temp_dir):
        """Test ignoring specific filenames."""
        ignore_file = temp_dir / ".obbyignore"
        ignore_file.write_text("session_summary.md\n.DS_Store")

        handler = IgnoreHandler(utils_folder=temp_dir, notes_folder=temp_dir)

        session_file = temp_dir / "session_summary.md"
        ds_store = temp_dir / ".DS_Store"
        other_file = temp_dir / "notes.md"

        assert handler.should_ignore(session_file) is True
        assert handler.should_ignore(ds_store) is True
        assert handler.should_ignore(other_file) is False

    @pytest.mark.unit
    def test_should_ignore_directory(self, temp_dir):
        """Test ignoring entire directories."""
        ignore_file = temp_dir / ".obbyignore"
        ignore_file.write_text(".git/\nnode_modules/")

        handler = IgnoreHandler(utils_folder=temp_dir, notes_folder=temp_dir)

        git_dir = temp_dir / ".git"
        git_dir.mkdir(exist_ok=True)
        node_dir = temp_dir / "node_modules"
        node_dir.mkdir(exist_ok=True)
        regular_dir = temp_dir / "src"
        regular_dir.mkdir(exist_ok=True)

        assert handler.should_ignore(git_dir) is True
        assert handler.should_ignore(node_dir) is True
        assert handler.should_ignore(regular_dir) is False

    @pytest.mark.unit
    def test_should_ignore_nested_paths(self, temp_dir):
        """Test ignoring files in nested directories."""
        ignore_file = temp_dir / ".obbyignore"
        ignore_file.write_text("*.tmp")

        handler = IgnoreHandler(utils_folder=temp_dir, notes_folder=temp_dir)

        # Create nested structure
        nested_dir = temp_dir / "level1" / "level2"
        nested_dir.mkdir(parents=True, exist_ok=True)
        nested_tmp = nested_dir / "test.tmp"

        assert handler.should_ignore(nested_tmp) is True

    @pytest.mark.unit
    def test_empty_patterns(self, temp_dir):
        """Test handler with no patterns."""
        ignore_file = temp_dir / ".obbyignore"
        ignore_file.write_text("")

        handler = IgnoreHandler(utils_folder=temp_dir, notes_folder=temp_dir)

        test_file = temp_dir / "test.md"

        # With no patterns, nothing should be ignored
        assert handler.should_ignore(test_file) is False

    @pytest.mark.unit
    def test_wildcard_patterns(self, temp_dir):
        """Test wildcard patterns in ignore rules."""
        ignore_file = temp_dir / ".obbyignore"
        ignore_file.write_text("test_*.py\n*_backup.*")

        handler = IgnoreHandler(utils_folder=temp_dir, notes_folder=temp_dir)

        assert handler.should_ignore(temp_dir / "test_foo.py") is True
        assert handler.should_ignore(temp_dir / "test_bar.py") is True
        assert handler.should_ignore(temp_dir / "data_backup.json") is True
        assert handler.should_ignore(temp_dir / "main.py") is False

    @pytest.mark.unit
    def test_reload_patterns(self, temp_dir):
        """Test reloading patterns after file modification."""
        ignore_file = temp_dir / ".obbyignore"
        ignore_file.write_text("*.tmp")

        handler = IgnoreHandler(utils_folder=temp_dir, notes_folder=temp_dir)

        # Initially only .tmp files are ignored
        assert "*.tmp" in handler.ignore_patterns
        assert "*.log" not in handler.ignore_patterns

        # Modify the ignore file
        ignore_file.write_text("*.tmp\n*.log")
        handler.load_ignore_patterns()

        # Now both should be in patterns
        assert "*.tmp" in handler.ignore_patterns
        assert "*.log" in handler.ignore_patterns

    @pytest.mark.unit
    def test_file_outside_notes_folder(self, temp_dir):
        """Test that files outside the notes folder are not ignored."""
        notes_dir = temp_dir / "notes"
        notes_dir.mkdir(exist_ok=True)
        outside_dir = temp_dir / "outside"
        outside_dir.mkdir(exist_ok=True)

        ignore_file = temp_dir / ".obbyignore"
        ignore_file.write_text("*.tmp")

        handler = IgnoreHandler(utils_folder=temp_dir, notes_folder=notes_dir)

        # File outside notes folder should not be ignored
        outside_file = outside_dir / "test.tmp"
        assert handler.should_ignore(outside_file) is False

        # File inside notes folder should be ignored
        inside_file = notes_dir / "test.tmp"
        assert handler.should_ignore(inside_file) is True
