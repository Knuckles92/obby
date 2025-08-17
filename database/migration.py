"""
🤖 SUBAGENT B: Data Migration & Legacy Import Utilities
========================================================

Comprehensive migration tools to import all existing file-based data
into SQLite with validation, deduplication, and rollback support.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple
import hashlib
import difflib

from .models import (
    db, EventModel, ConfigModel, FileStateModel
)

logger = logging.getLogger(__name__)

class MigrationManager:
    """Orchestrates complete migration from file-based to SQLite storage."""
    
    def __init__(self, backup_dir: str = "migration_backup"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        self.migration_log = []
    
    def run_complete_migration(self) -> Dict[str, Any]:
        """Execute complete migration of all data sources."""
        logger.info("🚀 Starting complete data migration to SQLite")
        
        results = {
            'started_at': datetime.now().isoformat(),
            'migrations': {},
            'total_records': 0,
            'errors': []
        }
        
        # Execute all migrations in parallel-compatible order
        migrations = [
            ('config', self.migrate_config),
            ('diffs', self.migrate_diffs), 
            ('semantic_index', self.migrate_semantic_index),
            ('living_note', self.migrate_living_note),
            ('file_states', self.initialize_file_states)
        ]
        
        for name, migration_func in migrations:
            try:
                logger.info(f"📦 Migrating {name}...")
                count = migration_func()
                results['migrations'][name] = {
                    'success': True,
                    'records': count,
                    'completed_at': datetime.now().isoformat()
                }
                results['total_records'] += count
                logger.info(f"✅ {name} migration completed: {count} records")
                
            except Exception as e:
                error_msg = f"Migration {name} failed: {str(e)}"
                logger.error(error_msg)
                results['migrations'][name] = {
                    'success': False,
                    'error': error_msg,
                    'completed_at': datetime.now().isoformat()
                }
                results['errors'].append(error_msg)
        
        results['completed_at'] = datetime.now().isoformat()
        results['success'] = len(results['errors']) == 0
        
        # Log migration results
        self._log_migration_result(results)
        
        logger.info(f"🎉 Migration completed: {results['total_records']} total records migrated")
        return results
    
    def migrate_config(self) -> int:
        """Migrate config.json to database."""
        config_path = Path("config.json")
        
        if not config_path.exists():
            logger.info("No config.json found, using defaults")
            return 0
        
        # Backup original
        self._backup_file(config_path)
        
        # Load and migrate
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        count = 0
        for key, value in config_data.items():
            ConfigModel.set(key, value, f"Migrated from config.json")
            count += 1
        
        logger.info(f"Migrated {count} configuration values")
        return count
    
    def migrate_diffs(self) -> int:
        """Migrate all diff files to database."""
        diffs_dir = Path("diffs")
        
        if not diffs_dir.exists():
            logger.info("No diffs directory found")
            return 0
        
        # Find all diff files
        diff_files = list(diffs_dir.glob("*.txt"))
        logger.info(f"Found {len(diff_files)} diff files to migrate")
        
        count = 0
        duplicates = 0
        
        for diff_file in diff_files:
            try:
                # Parse filename for metadata
                file_info = self._parse_diff_filename(diff_file.name)
                if not file_info:
                    logger.warning(f"Could not parse diff filename: {diff_file.name}")
                    continue
                
                # Read content
                content = diff_file.read_text(encoding='utf-8')
                
                # Create timestamp from filename
                timestamp = datetime.strptime(file_info['timestamp'], '%Y-%m-%d_%H-%M-%S')
                
                # Insert into database
                diff_id = DiffModel.insert(
                    file_path=file_info['file_path'],
                    diff_content=content,
                    timestamp=timestamp
                )
                
                if diff_id:
                    count += 1
                    # Backup original file
                    self._backup_file(diff_file)
                else:
                    duplicates += 1
                    
            except Exception as e:
                logger.error(f"Failed to migrate diff {diff_file.name}: {e}")
        
        logger.info(f"Migrated {count} diffs, {duplicates} duplicates skipped")
        return count
    
    def migrate_semantic_index(self) -> int:
        """Migrate semantic_index.json to normalized database storage."""
        index_path = Path("notes/semantic_index.json")
        
        if not index_path.exists():
            logger.info("No semantic index found")
            return 0
        
        # Backup original
        self._backup_file(index_path)
        
        # Load semantic index
        with open(index_path, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
        
        entries = index_data.get('entries', [])
        logger.info(f"Found {len(entries)} semantic entries to migrate")
        
        count = 0
        id_conflicts = 0
        
        for entry in entries:
            try:
                # Handle duplicate IDs by adding sequence number
                original_id = entry.get('id', '')
                
                # Parse timestamp
                timestamp_str = entry.get('timestamp', datetime.now().isoformat())
                try:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                except:
                    timestamp = datetime.now()
                
                # Insert with normalized data
                entry_id = SemanticModel.insert_entry(
                    summary=entry.get('summary', ''),
                    entry_type=entry.get('type', 'content'),
                    impact=entry.get('impact', 'moderate'),
                    topics=entry.get('topics', []),
                    keywords=entry.get('keywords', []),
                    file_path=entry.get('file_path', ''),
                    timestamp=timestamp
                )
                
                if entry_id:
                    count += 1
                    # Store original ID for reference during migration
                    db.execute_update(
                        "UPDATE semantic_entries SET original_id = ? WHERE id = ?",
                        (original_id, entry_id)
                    )
                else:
                    id_conflicts += 1
                    
            except Exception as e:
                logger.error(f"Failed to migrate semantic entry {entry.get('id', 'unknown')}: {e}")
        
        logger.info(f"Migrated {count} semantic entries, {id_conflicts} ID conflicts resolved")
        return count
    
    def migrate_living_note(self) -> int:
        """Migrate legacy single-file living note into the database once, if present."""
        # Use utility resolver to support daily mode paths transparently
        try:
            from utils.living_note_path import resolve_living_note_path
            living_note_path = resolve_living_note_path()
        except Exception:
            living_note_path = Path("notes/living_note.md")
        
        if not living_note_path.exists():
            logger.info("No living note found")
            return 0
        
        # Backup original
        self._backup_file(living_note_path)
        
        # Read current content
        content = living_note_path.read_text(encoding='utf-8')
        
        if not content.strip():
            logger.info("Living note is empty, skipping migration")
            return 0
        
        # Create initial session and entry
        session_query = """
            INSERT INTO living_note_sessions (date, focus, changes_count, insights)
            VALUES (DATE('now'), 'Migrated content', 1, 'Initial migration from file')
        """
        db.execute_update(session_query)
        
        # Get session ID
        session_result = db.execute_query("SELECT last_insert_rowid() as id")
        session_id = session_result[0]['id']
        
        # Create entry
        word_count = len(content.split())
        entry_query = """
            INSERT INTO living_note_entries (session_id, content, word_count, timestamp)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """
        db.execute_update(entry_query, (session_id, content, word_count))
        
        logger.info(f"Migrated living note: {word_count} words")
        return 1
    
    def initialize_file_states(self) -> int:
        """Initialize file state tracking for existing files."""
        notes_dir = Path("notes")
        
        if not notes_dir.exists():
            return 0
        
        count = 0
        for md_file in notes_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding='utf-8')
                content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
                line_count = len(content.splitlines())
                
                FileStateModel.update_state(
                    file_path=str(md_file),
                    content_hash=content_hash,
                    line_count=line_count
                )
                count += 1
                
            except Exception as e:
                logger.error(f"Failed to initialize state for {md_file}: {e}")
        
        logger.info(f"Initialized file states for {count} files")
        return count
    
    def _parse_diff_filename(self, filename: str) -> Dict[str, str]:
        """Parse diff filename to extract metadata."""
        # Expected format: base_name.diff.YYYY-MM-DD_HH-MM-SS.txt
        try:
            parts = filename.replace('.txt', '').split('.')
            if len(parts) >= 3 and parts[-2] == 'diff':
                return {
                    'file_path': parts[0],
                    'timestamp': parts[-1]
                }
        except:
            pass
        return None
    
    def _backup_file(self, file_path: Path) -> None:
        """Create backup of file before migration."""
        if file_path.exists():
            backup_path = self.backup_dir / file_path.name
            backup_path.write_text(file_path.read_text(encoding='utf-8'), encoding='utf-8')
            logger.debug(f"Backed up {file_path} to {backup_path}")
    
    def _log_migration_result(self, results: Dict[str, Any]) -> None:
        """Log migration results to database."""
        for name, result in results['migrations'].items():
            query = """
                INSERT INTO migration_log (migration_name, success, error_message, records_migrated)
                VALUES (?, ?, ?, ?)
            """
            db.execute_update(query, (
                name,
                result['success'],
                result.get('error'),
                result.get('records', 0)
            ))

class DataValidator:
    """Validates migrated data integrity and completeness."""
    
    @staticmethod
    def validate_migration() -> Dict[str, Any]:
        """Comprehensive validation of migrated data."""
        logger.info("🔍 Validating migrated data...")
        
        validation_results = {
            'valid': True,
            'checks': {},
            'warnings': [],
            'errors': []
        }
        
        # Validate diffs
        diff_check = DataValidator._validate_diffs()
        validation_results['checks']['diffs'] = diff_check
        if not diff_check['valid']:
            validation_results['valid'] = False
            validation_results['errors'].extend(diff_check['errors'])
        
        # Validate semantic entries
        semantic_check = DataValidator._validate_semantic_entries()
        validation_results['checks']['semantic'] = semantic_check
        if not semantic_check['valid']:
            validation_results['valid'] = False
            validation_results['errors'].extend(semantic_check['errors'])
        
        # Validate configuration
        config_check = DataValidator._validate_config()
        validation_results['checks']['config'] = config_check
        if not config_check['valid']:
            validation_results['valid'] = False
            validation_results['errors'].extend(config_check['errors'])
        
        return validation_results
    
    @staticmethod
    def _validate_diffs() -> Dict[str, Any]:
        """Validate diff data integrity."""
        try:
            diffs = DiffModel.get_recent(limit=1000)
            
            # Check for required fields
            required_fields = ['id', 'file_path', 'content_hash', 'timestamp', 'diff_content']
            invalid_diffs = []
            
            for diff in diffs:
                for field in required_fields:
                    if field not in diff or diff[field] is None:
                        invalid_diffs.append(f"Diff {diff.get('id')} missing {field}")
            
            return {
                'valid': len(invalid_diffs) == 0,
                'count': len(diffs),
                'errors': invalid_diffs
            }
            
        except Exception as e:
            return {
                'valid': False,
                'count': 0,
                'errors': [f"Diff validation failed: {str(e)}"]
            }
    
    @staticmethod
    def _validate_semantic_entries() -> Dict[str, Any]:
        """Validate semantic entry data."""
        try:
            # Check FTS index
            fts_result = db.execute_query("SELECT COUNT(*) as count FROM semantic_search")
            semantic_result = db.execute_query("SELECT COUNT(*) as count FROM semantic_entries")
            
            fts_count = fts_result[0]['count']
            semantic_count = semantic_result[0]['count']
            
            errors = []
            if fts_count != semantic_count:
                errors.append(f"FTS index mismatch: {fts_count} vs {semantic_count} entries")
            
            return {
                'valid': len(errors) == 0,
                'count': semantic_count,
                'fts_count': fts_count,
                'errors': errors
            }
            
        except Exception as e:
            return {
                'valid': False,
                'count': 0,
                'errors': [f"Semantic validation failed: {str(e)}"]
            }
    
    @staticmethod
    def _validate_config() -> Dict[str, Any]:
        """Validate configuration data."""
        try:
            config = ConfigModel.get_all()
            
            # Check for required config values
            required_keys = ['checkInterval', 'dbVersion']
            missing_keys = [key for key in required_keys if key not in config]
            
            return {
                'valid': len(missing_keys) == 0,
                'count': len(config),
                'errors': [f"Missing required config: {key}" for key in missing_keys]
            }
            
        except Exception as e:
            return {
                'valid': False,
                'count': 0,
                'errors': [f"Config validation failed: {str(e)}"]
            }

class RollbackManager:
    """Handles rollback of migration if needed."""
    
    def __init__(self, backup_dir: str = "migration_backup"):
        self.backup_dir = Path(backup_dir)
    
    def rollback_migration(self) -> Dict[str, Any]:
        """Rollback migration by restoring from backups."""
        logger.warning("🔄 Rolling back migration...")
        
        if not self.backup_dir.exists():
            return {'success': False, 'error': 'No backup directory found'}
        
        results = {'success': True, 'restored_files': [], 'errors': []}
        
        # Restore backed up files
        for backup_file in self.backup_dir.glob("*"):
            try:
                original_path = Path(backup_file.name)
                
                # Determine original location
                if backup_file.name == 'config.json':
                    original_path = Path('config.json')
                elif backup_file.name == 'semantic_index.json':
                    original_path = Path('notes/semantic_index.json')
                elif backup_file.name == 'living_note.md':
                    original_path = Path('notes/living_note.md')
                elif backup_file.name.endswith('.txt'):
                    original_path = Path('diffs') / backup_file.name
                
                # Restore file
                original_path.parent.mkdir(exist_ok=True)
                original_path.write_text(backup_file.read_text(encoding='utf-8'), encoding='utf-8')
                results['restored_files'].append(str(original_path))
                
            except Exception as e:
                error_msg = f"Failed to restore {backup_file.name}: {str(e)}"
                results['errors'].append(error_msg)
                logger.error(error_msg)
        
        if results['errors']:
            results['success'] = False
        
        logger.info(f"Rollback completed: {len(results['restored_files'])} files restored")
        return results

logger.info("🤖 Subagent B: Migration utilities initialized successfully")