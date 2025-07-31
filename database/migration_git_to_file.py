#!/usr/bin/env python3
"""
Database Migration: Git-based to File-based Schema
================================================

Migrates existing git-based Obby database to the new file-based schema.
Preserves relevant data while removing git dependencies.
"""

import sqlite3
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GitToFileMigration:
    """Handles migration from git-based to file-based database schema."""
    
    def __init__(self, db_path: str = "obby.db", backup_suffix: str = ".git-backup"):
        self.db_path = db_path
        self.backup_path = f"{db_path}{backup_suffix}"
        self.new_schema_path = Path(__file__).parent / "schema_new.sql"
        
    def run_migration(self) -> bool:
        """Execute the complete migration process."""
        try:
            logger.info("Starting git-to-file migration...")
            
            # Step 1: Backup existing database
            self.backup_database()
            
            # Step 2: Extract data from git-based tables
            git_data = self.extract_git_data()
            
            # Step 3: Create new schema
            self.create_new_schema()
            
            # Step 4: Migrate preserved data
            self.migrate_data(git_data)
            
            # Step 5: Log migration completion
            self.log_migration_completion()
            
            logger.info("Migration completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            self.restore_backup()
            return False
    
    def backup_database(self) -> None:
        """Create backup of existing database."""
        if not Path(self.db_path).exists():
            logger.warning(f"Database {self.db_path} does not exist, creating new one")
            return
            
        import shutil
        shutil.copy2(self.db_path, self.backup_path)
        logger.info(f"Database backed up to {self.backup_path}")
    
    def extract_git_data(self) -> Dict[str, Any]:
        """Extract relevant data from git-based tables."""
        if not Path(self.db_path).exists():
            return {}
            
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        git_data = {
            'events': [],
            'semantic_entries': [],
            'semantic_topics': [],
            'semantic_keywords': [],
            'config_values': [],
            'living_note_sessions': [],
            'living_note_entries': [],
            'file_states': []
        }
        
        try:
            # Extract events (these can be preserved as-is)
            cursor = conn.execute("SELECT * FROM events")
            git_data['events'] = [dict(row) for row in cursor.fetchall()]
            logger.info(f"Extracted {len(git_data['events'])} events")
            
            # Extract semantic entries (convert git context to file context)
            cursor = conn.execute("SELECT * FROM semantic_entries")
            for row in cursor.fetchall():
                entry = dict(row)
                # Remove git-specific fields
                entry.pop('commit_hash', None)
                entry.pop('author_name', None)
                entry.pop('branch_name', None)
                git_data['semantic_entries'].append(entry)
            logger.info(f"Extracted {len(git_data['semantic_entries'])} semantic entries")
            
            # Extract semantic topics and keywords
            cursor = conn.execute("SELECT * FROM semantic_topics")
            git_data['semantic_topics'] = [dict(row) for row in cursor.fetchall()]
            
            cursor = conn.execute("SELECT * FROM semantic_keywords")
            git_data['semantic_keywords'] = [dict(row) for row in cursor.fetchall()]
            
            # Extract configuration (preserve non-git settings)
            cursor = conn.execute("SELECT * FROM config_values WHERE key NOT LIKE '%git%'")
            git_data['config_values'] = [dict(row) for row in cursor.fetchall()]
            
            # Extract living note data (preserve as-is)
            for table in ['living_note_sessions', 'living_note_entries']:
                try:
                    cursor = conn.execute(f"SELECT * FROM {table}")
                    git_data[table] = [dict(row) for row in cursor.fetchall()]
                except sqlite3.OperationalError:
                    logger.warning(f"Table {table} not found, skipping")
            
            # Extract file states (convert git_hash to content_hash)
            try:
                cursor = conn.execute("SELECT * FROM file_states")
                for row in cursor.fetchall():
                    state = dict(row)
                    # Rename git_hash to content_hash
                    if 'git_hash' in state:
                        state['content_hash'] = state.pop('git_hash')
                    git_data['file_states'].append(state)
            except sqlite3.OperationalError:
                logger.warning("file_states table not found, skipping")
                
        except sqlite3.Error as e:
            logger.warning(f"Error extracting data: {e}")
        finally:
            conn.close()
            
        return git_data
    
    def create_new_schema(self) -> None:
        """Create new file-based database schema."""
        # Remove existing database
        if Path(self.db_path).exists():
            Path(self.db_path).unlink()
            
        # Create new database with file-based schema
        conn = sqlite3.connect(self.db_path)
        try:
            schema_sql = self.new_schema_path.read_text(encoding='utf-8')
            conn.executescript(schema_sql)
            logger.info("New file-based schema created successfully")
        finally:
            conn.close()
    
    def migrate_data(self, git_data: Dict[str, Any]) -> None:
        """Migrate preserved data to new schema."""
        conn = sqlite3.connect(self.db_path)
        try:
            # Migrate events
            if git_data['events']:
                placeholders = "(" + ",".join(["?" for _ in range(6)]) + ")"  # Adjusted for new schema
                conn.executemany(
                    "INSERT INTO events (type, path, timestamp, size, processed, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    [(row['type'], row['path'], row['timestamp'], row.get('size', 0), 
                      row.get('processed', False), row.get('created_at', row['timestamp'])) 
                     for row in git_data['events']]
                )
                logger.info(f"Migrated {len(git_data['events'])} events")
            
            # Migrate semantic entries (without git context)
            if git_data['semantic_entries']:
                conn.executemany(
                    """INSERT INTO semantic_entries 
                       (timestamp, date, time, type, summary, impact, file_path, searchable_text, created_at) 
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    [(row['timestamp'], row['date'], row['time'], row['type'], 
                      row['summary'], row['impact'], row['file_path'], row['searchable_text'],
                      row.get('created_at', row['timestamp'])) 
                     for row in git_data['semantic_entries']]
                )
                logger.info(f"Migrated {len(git_data['semantic_entries'])} semantic entries")
            
            # Migrate topics and keywords
            if git_data['semantic_topics']:
                conn.executemany(
                    "INSERT INTO semantic_topics (entry_id, topic) VALUES (?, ?)",
                    [(row['entry_id'], row['topic']) for row in git_data['semantic_topics']]
                )
                
            if git_data['semantic_keywords']:
                conn.executemany(
                    "INSERT INTO semantic_keywords (entry_id, keyword) VALUES (?, ?)",
                    [(row['entry_id'], row['keyword']) for row in git_data['semantic_keywords']]
                )
            
            # Migrate configuration (update file-based settings)
            if git_data['config_values']:
                for config in git_data['config_values']:
                    conn.execute(
                        "INSERT OR REPLACE INTO config_values (key, value, type, description, updated_at) VALUES (?, ?, ?, ?, ?)",
                        (config['key'], config['value'], config['type'], 
                         config.get('description', ''), config.get('updated_at', datetime.now()))
                    )
            
            # Update configuration for file-based monitoring
            conn.execute(
                "INSERT OR REPLACE INTO config_values (key, value, type, description) VALUES (?, ?, ?, ?)",
                ('fileMonitoringEnabled', 'true', 'bool', 'Enable file-based change tracking')
            )
            
            # Migrate living note data
            for table in ['living_note_sessions', 'living_note_entries']:
                if git_data[table]:
                    if table == 'living_note_sessions':
                        conn.executemany(
                            "INSERT INTO living_note_sessions (date, focus, changes_count, insights, created_at) VALUES (?, ?, ?, ?, ?)",
                            [(row['date'], row.get('focus'), row.get('changes_count', 0), 
                              row.get('insights'), row.get('created_at', datetime.now())) 
                             for row in git_data[table]]
                        )
                    else:
                        conn.executemany(
                            "INSERT INTO living_note_entries (session_id, content, word_count, timestamp, created_at) VALUES (?, ?, ?, ?, ?)",
                            [(row['session_id'], row['content'], row['word_count'], 
                              row['timestamp'], row.get('created_at', row['timestamp'])) 
                             for row in git_data[table]]
                        )
            
            # Migrate file states
            if git_data['file_states']:
                conn.executemany(
                    "INSERT OR REPLACE INTO file_states (file_path, content_hash, last_modified, line_count, file_size, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    [(row['file_path'], row.get('content_hash'), row['last_modified'], 
                      row.get('line_count', 0), 0, row.get('updated_at', datetime.now())) 
                     for row in git_data['file_states']]
                )
                logger.info(f"Migrated {len(git_data['file_states'])} file states")
            
            conn.commit()
            logger.info("Data migration completed successfully")
            
        except sqlite3.Error as e:
            logger.error(f"Error migrating data: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def log_migration_completion(self) -> None:
        """Log migration completion to database."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                "INSERT INTO migration_log (migration_name, success, records_migrated) VALUES (?, ?, ?)",
                ('git_to_file_migration', True, 0)  # Would count records in real implementation
            )
            conn.commit()
        finally:
            conn.close()
    
    def restore_backup(self) -> None:
        """Restore database from backup if migration fails."""
        if Path(self.backup_path).exists():
            import shutil
            shutil.copy2(self.backup_path, self.db_path)
            logger.info("Database restored from backup")

def main():
    """Run the migration script."""
    migration = GitToFileMigration()
    success = migration.run_migration()
    
    if success:
        print("✅ Migration completed successfully!")
        print(f"Original database backed up to: {migration.backup_path}")
        print("Your Obby installation is now using file-based monitoring.")
    else:
        print("❌ Migration failed. Original database has been restored.")
        print("Please check the logs for details.")

if __name__ == "__main__":
    main()