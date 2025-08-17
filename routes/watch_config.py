"""
Watch Configuration API routes
Handles interactive management of .obbywatch and .obbyignore files
"""

from flask import Blueprint, jsonify, request
import logging
import os
from pathlib import Path
from utils.watch_handler import WatchHandler
from utils.ignore_handler import IgnoreHandler

logger = logging.getLogger(__name__)

watch_config_bp = Blueprint('watch_config', __name__, url_prefix='/api/watch-config')

# Initialize handlers - they'll point to project root for .obbywatch/.obbyignore files
def get_project_root():
    """Get the project root directory"""
    # Get the directory containing the routes folder (project root)
    return Path(__file__).parent.parent

def get_handlers():
    """Get initialized watch and ignore handlers"""
    project_root = get_project_root()
    from config.settings import get_configured_notes_folder
    notes_folder = get_configured_notes_folder()
    
    watch_handler = WatchHandler(project_root)
    ignore_handler = IgnoreHandler(project_root, notes_folder)
    
    return watch_handler, ignore_handler


@watch_config_bp.route('/watch-patterns', methods=['GET'])
def get_watch_patterns():
    """Get current watch patterns from .obbywatch file"""
    try:
        watch_handler, _ = get_handlers()
        
        # Get patterns as a list
        patterns = list(watch_handler.watch_patterns)
        
        # Also get directories that would be watched based on current patterns
        project_root = get_project_root()
        watch_dirs = [str(path.relative_to(project_root)) for path in watch_handler.get_watch_directories(project_root)]
        
        return jsonify({
            'patterns': patterns,
            'watchDirectories': watch_dirs,
            'watchFile': str(watch_handler.watch_file),
            'success': True
        })
    except Exception as e:
        logger.error(f"Error getting watch patterns: {e}")
        return jsonify({'error': f'Failed to get watch patterns: {str(e)}'}), 500


@watch_config_bp.route('/watch-patterns', methods=['POST'])
def add_watch_pattern():
    """Add a new watch pattern to .obbywatch file"""
    try:
        data = request.get_json()
        if not data or 'pattern' not in data:
            return jsonify({'error': 'Pattern is required'}), 400
        
        pattern = data['pattern'].strip()
        if not pattern:
            return jsonify({'error': 'Pattern cannot be empty'}), 400
        
        watch_handler, _ = get_handlers()
        
        # Check if pattern already exists
        if pattern in watch_handler.watch_patterns:
            return jsonify({'error': 'Pattern already exists'}), 400
        
        # Add pattern to the set
        watch_handler.watch_patterns.add(pattern)
        
        # Write updated patterns to file
        _write_watch_patterns(watch_handler)
        
        logger.info(f"Added watch pattern: {pattern}")
        return jsonify({
            'success': True,
            'message': f'Added watch pattern: {pattern}',
            'patterns': list(watch_handler.watch_patterns)
        })
        
    except Exception as e:
        logger.error(f"Error adding watch pattern: {e}")
        return jsonify({'error': f'Failed to add watch pattern: {str(e)}'}), 500


@watch_config_bp.route('/watch-patterns', methods=['DELETE'])
def remove_watch_pattern():
    """Remove a watch pattern from .obbywatch file"""
    try:
        data = request.get_json()
        if not data or 'pattern' not in data:
            return jsonify({'error': 'Pattern is required'}), 400
        
        pattern = data['pattern'].strip()
        watch_handler, _ = get_handlers()
        
        # Check if pattern exists
        if pattern not in watch_handler.watch_patterns:
            return jsonify({'error': 'Pattern not found'}), 404
        
        # Remove pattern from the set
        watch_handler.watch_patterns.remove(pattern)
        
        # Write updated patterns to file
        _write_watch_patterns(watch_handler)
        
        logger.info(f"Removed watch pattern: {pattern}")
        return jsonify({
            'success': True,
            'message': f'Removed watch pattern: {pattern}',
            'patterns': list(watch_handler.watch_patterns)
        })
        
    except Exception as e:
        logger.error(f"Error removing watch pattern: {e}")
        return jsonify({'error': f'Failed to remove watch pattern: {str(e)}'}), 500


@watch_config_bp.route('/ignore-patterns', methods=['GET'])
def get_ignore_patterns():
    """Get current ignore patterns from .obbyignore file"""
    try:
        _, ignore_handler = get_handlers()
        
        # Get patterns as a list
        patterns = list(ignore_handler.ignore_patterns)
        
        return jsonify({
            'patterns': patterns,
            'ignoreFile': str(ignore_handler.ignore_file),
            'success': True
        })
    except Exception as e:
        logger.error(f"Error getting ignore patterns: {e}")
        return jsonify({'error': f'Failed to get ignore patterns: {str(e)}'}), 500


@watch_config_bp.route('/ignore-patterns', methods=['POST'])
def add_ignore_pattern():
    """Add a new ignore pattern to .obbyignore file"""
    try:
        data = request.get_json()
        if not data or 'pattern' not in data:
            return jsonify({'error': 'Pattern is required'}), 400
        
        pattern = data['pattern'].strip()
        if not pattern:
            return jsonify({'error': 'Pattern cannot be empty'}), 400
        
        _, ignore_handler = get_handlers()
        
        # Check if pattern already exists
        if pattern in ignore_handler.ignore_patterns:
            return jsonify({'error': 'Pattern already exists'}), 400
        
        # Add pattern to the set
        ignore_handler.ignore_patterns.add(pattern)
        
        # Write updated patterns to file
        _write_ignore_patterns(ignore_handler)
        
        logger.info(f"Added ignore pattern: {pattern}")
        return jsonify({
            'success': True,
            'message': f'Added ignore pattern: {pattern}',
            'patterns': list(ignore_handler.ignore_patterns)
        })
        
    except Exception as e:
        logger.error(f"Error adding ignore pattern: {e}")
        return jsonify({'error': f'Failed to add ignore pattern: {str(e)}'}), 500


@watch_config_bp.route('/ignore-patterns', methods=['DELETE'])
def remove_ignore_pattern():
    """Remove an ignore pattern from .obbyignore file"""
    try:
        data = request.get_json()
        if not data or 'pattern' not in data:
            return jsonify({'error': 'Pattern is required'}), 400
        
        pattern = data['pattern'].strip()
        _, ignore_handler = get_handlers()
        
        # Check if pattern exists
        if pattern not in ignore_handler.ignore_patterns:
            return jsonify({'error': 'Pattern not found'}), 404
        
        # Remove pattern from the set
        ignore_handler.ignore_patterns.remove(pattern)
        
        # Write updated patterns to file
        _write_ignore_patterns(ignore_handler)
        
        logger.info(f"Removed ignore pattern: {pattern}")
        return jsonify({
            'success': True,
            'message': f'Removed ignore pattern: {pattern}',
            'patterns': list(ignore_handler.ignore_patterns)
        })
        
    except Exception as e:
        logger.error(f"Error removing ignore pattern: {e}")
        return jsonify({'error': f'Failed to remove ignore pattern: {str(e)}'}), 500


@watch_config_bp.route('/reload', methods=['POST'])
def reload_patterns():
    """Force reload of watch and ignore patterns"""
    try:
        watch_handler, ignore_handler = get_handlers()
        
        # Reload patterns from files
        watch_handler.reload_patterns()
        ignore_handler.load_ignore_patterns()
        
        logger.info("Reloaded watch and ignore patterns")
        return jsonify({
            'success': True,
            'message': 'Patterns reloaded successfully',
            'watchPatterns': list(watch_handler.watch_patterns),
            'ignorePatterns': list(ignore_handler.ignore_patterns)
        })
        
    except Exception as e:
        logger.error(f"Error reloading patterns: {e}")
        return jsonify({'error': f'Failed to reload patterns: {str(e)}'}), 500


@watch_config_bp.route('/validate-pattern', methods=['POST'])
def validate_pattern():
    """Validate a watch or ignore pattern"""
    try:
        data = request.get_json()
        if not data or 'pattern' not in data:
            return jsonify({'error': 'Pattern is required'}), 400
        
        pattern = data['pattern'].strip()
        pattern_type = data.get('type', 'watch')  # 'watch' or 'ignore'
        
        if not pattern:
            return jsonify({'error': 'Pattern cannot be empty'}), 400
        
        # Basic validation
        errors = []
        warnings = []
        
        # Check for invalid characters
        invalid_chars = ['<', '>', ':', '"', '|', '\0']
        for char in invalid_chars:
            if char in pattern:
                errors.append(f"Pattern contains invalid character: {char}")
        
        # Check for directory patterns
        if pattern.endswith('/'):
            if pattern_type == 'watch':
                # For watch patterns, check if directory exists
                project_root = get_project_root()
                dir_path = project_root / pattern.rstrip('/')
                if not dir_path.exists():
                    warnings.append(f"Directory does not exist: {pattern}")
                elif not dir_path.is_dir():
                    errors.append(f"Path exists but is not a directory: {pattern}")
        
        # Check for common mistakes
        if pattern.startswith('./'):
            warnings.append("Relative paths starting with './' may not work as expected")
        
        if pattern.startswith('/') and pattern_type == 'watch':
            warnings.append("Absolute paths may not work as expected for watch patterns")
        
        return jsonify({
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'pattern': pattern
        })
        
    except Exception as e:
        logger.error(f"Error validating pattern: {e}")
        return jsonify({'error': f'Failed to validate pattern: {str(e)}'}), 500


def _write_watch_patterns(watch_handler):
    """Write watch patterns to .obbywatch file"""
    try:
        content = """# Obby watch file
# This file specifies directories that Obby should monitor for changes
# Use glob patterns (* and ?) and one pattern per line
# Lines starting with # are comments

"""
        
        # Add current patterns
        for pattern in sorted(watch_handler.watch_patterns):
            content += f"{pattern}\n"
        
        # Add example patterns as comments if file is empty
        if not watch_handler.watch_patterns:
            content += """
# Example patterns:
# notes/
# docs/
# *.md
# project_notes/
# research/
# writing/
# *.txt
"""
        
        with open(watch_handler.watch_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Updated .obbywatch file with {len(watch_handler.watch_patterns)} patterns")
        
    except Exception as e:
        logger.error(f"Error writing watch patterns: {e}")
        raise


def _write_ignore_patterns(ignore_handler):
    """Write ignore patterns to .obbyignore file"""
    try:
        content = """# Obby ignore file
# This file specifies patterns for files and directories that Obby should ignore
# Use glob patterns (* and ?) and one pattern per line
# Lines starting with # are comments

"""
        
        # Add current patterns
        for pattern in sorted(ignore_handler.ignore_patterns):
            content += f"{pattern}\n"
        
        # Add example patterns as comments if file is empty
        if not ignore_handler.ignore_patterns:
            content += """
# Example patterns:
# *.tmp
# *.temp
# *~
# .DS_Store
# Thumbs.db
# .git/
# .svn/
# .vscode/
# .idea/
# *.swp
# *.swo
# node_modules/
# __pycache__/
"""
        
        with open(ignore_handler.ignore_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Updated .obbyignore file with {len(ignore_handler.ignore_patterns)} patterns")
        
    except Exception as e:
        logger.error(f"Error writing ignore patterns: {e}")
        raise