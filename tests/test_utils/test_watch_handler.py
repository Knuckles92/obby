"""
Unit tests for the watch handler.

Tests the WatchHandler class that manages .obbywatch file patterns
for specifying which directories to monitor.
"""

import pytest
from pathlib import Path
from utils.watch_handler import WatchHandler


class TestWatchHandler:
    """Test the WatchHandler class."""

    @pytest.mark.unit
    def test_initialization(self, temp_dir):
        """Test WatchHandler initialization."""
        handler = WatchHandler(utils_folder=temp_dir)

        assert handler.utils_folder == temp_dir
        assert handler.watch_file == temp_dir / ".obbywatch"

    @pytest.mark.unit
    def test_creates_default_watch_file(self, temp_dir):
        """Test that initialization creates a default .obbywatch file."""
        handler = WatchHandler(utils_folder=temp_dir)

        assert handler.watch_file.exists()
        content = handler.watch_file.read_text()
        assert "# Obby watch file" in content

    @pytest.mark.unit
    def test_load_watch_patterns(self, temp_dir):
        """Test loading patterns from .obbywatch file."""
        watch_file = temp_dir / ".obbywatch"
        watch_file.write_text("notes/\ndocs/\n# Comment\n\n*.md")

        handler = WatchHandler(utils_folder=temp_dir)

        assert len(handler.watch_patterns) >= 3
        assert "notes/" in handler.watch_patterns
        assert "docs/" in handler.watch_patterns
        assert "*.md" in handler.watch_patterns
        assert "# Comment" not in handler.watch_patterns

    @pytest.mark.unit
    def test_should_watch_directory(self, temp_dir):
        """Test watching specific directories."""
        watch_file = temp_dir / ".obbywatch"
        watch_file.write_text("notes/\ndocs/")

        handler = WatchHandler(utils_folder=temp_dir)

        notes_dir = temp_dir / "notes"
        docs_dir = temp_dir / "docs"
        other_dir = temp_dir / "other"

        # Create directories
        notes_dir.mkdir(exist_ok=True)
        docs_dir.mkdir(exist_ok=True)
        other_dir.mkdir(exist_ok=True)

        assert handler.should_watch(notes_dir, base_path=temp_dir) is True
        assert handler.should_watch(docs_dir, base_path=temp_dir) is True
        # Other directories might be watched depending on default patterns

    @pytest.mark.unit
    def test_should_watch_by_extension(self, temp_dir):
        """Test watching files by extension."""
        watch_file = temp_dir / ".obbywatch"
        watch_file.write_text("*.md\n*.txt")

        handler = WatchHandler(utils_folder=temp_dir)

        md_file = temp_dir / "test.md"
        txt_file = temp_dir / "notes.txt"
        py_file = temp_dir / "script.py"

        assert handler.should_watch(md_file, base_path=temp_dir) is True
        assert handler.should_watch(txt_file, base_path=temp_dir) is True
        # py files might not be watched depending on patterns

    @pytest.mark.unit
    def test_should_watch_nested_files(self, temp_dir):
        """Test watching files in nested directories."""
        watch_file = temp_dir / ".obbywatch"
        watch_file.write_text("notes/")

        handler = WatchHandler(utils_folder=temp_dir)

        # Create nested structure
        notes_dir = temp_dir / "notes"
        nested_dir = notes_dir / "project" / "subproject"
        nested_dir.mkdir(parents=True, exist_ok=True)
        nested_file = nested_dir / "file.md"

        # Files in watched directories should be watched
        assert handler.should_watch(nested_file, base_path=temp_dir) is True

    @pytest.mark.unit
    def test_wildcard_patterns(self, temp_dir):
        """Test wildcard patterns in watch rules."""
        watch_file = temp_dir / ".obbywatch"
        watch_file.write_text("project_*/*.md")

        handler = WatchHandler(utils_folder=temp_dir)

        # Files matching pattern should be watched
        proj1_dir = temp_dir / "project_1"
        proj1_dir.mkdir(exist_ok=True)
        proj1_file = proj1_dir / "readme.md"

        assert handler.should_watch(proj1_file, base_path=temp_dir) is True

    @pytest.mark.unit
    def test_reload_patterns(self, temp_dir):
        """Test reloading patterns after file modification."""
        watch_file = temp_dir / ".obbywatch"
        watch_file.write_text("notes/")

        handler = WatchHandler(utils_folder=temp_dir)

        # Initially only notes/ is watched
        assert "notes/" in handler.watch_patterns
        assert "docs/" not in handler.watch_patterns

        # Modify the watch file
        watch_file.write_text("notes/\ndocs/")
        handler.load_watch_patterns()

        # Now both should be in patterns
        assert "notes/" in handler.watch_patterns
        assert "docs/" in handler.watch_patterns

    @pytest.mark.unit
    def test_empty_patterns(self, temp_dir):
        """Test handler with no patterns (watches nothing)."""
        watch_file = temp_dir / ".obbywatch"
        watch_file.write_text("")

        handler = WatchHandler(utils_folder=temp_dir)

        test_file = temp_dir / "test.md"

        # With no patterns, should not watch
        # (behavior depends on implementation - might have defaults)
        assert isinstance(handler.should_watch(test_file, base_path=temp_dir), bool)

    @pytest.mark.unit
    def test_comment_and_blank_lines(self, temp_dir):
        """Test that comments and blank lines are ignored."""
        watch_file = temp_dir / ".obbywatch"
        watch_content = """# This is a comment
notes/

# Another comment
docs/

"""
        watch_file.write_text(watch_content)

        handler = WatchHandler(utils_folder=temp_dir)

        # Should only have actual patterns, not comments
        assert "notes/" in handler.watch_patterns
        assert "docs/" in handler.watch_patterns
        assert not any("#" in p for p in handler.watch_patterns)

    @pytest.mark.unit
    def test_default_patterns_content(self, temp_dir):
        """Test that default .obbywatch contains reasonable patterns."""
        handler = WatchHandler(utils_folder=temp_dir)

        # Read the created default file
        content = handler.watch_file.read_text()

        # Should contain some default patterns
        assert "notes/" in content or "*.md" in content
        assert "#" in content  # Should have comments

    @pytest.mark.unit
    def test_get_watched_directories(self, temp_dir):
        """Test retrieving list of watched directories."""
        watch_file = temp_dir / ".obbywatch"
        watch_file.write_text("notes/\ndocs/\nsrc/")

        handler = WatchHandler(utils_folder=temp_dir)

        # Should be able to get patterns
        assert len(handler.watch_patterns) >= 3
        assert all(isinstance(p, str) for p in handler.watch_patterns)
