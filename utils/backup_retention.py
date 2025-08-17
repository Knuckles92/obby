#!/usr/bin/env python3
"""
Database Backup Retention Policy
================================

Manages automated cleanup of database backup files and log files
based on configurable retention policies.
"""

import os
import glob
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class BackupRetentionManager:
    """Manages backup file retention and cleanup."""
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        
        # Default retention policies (days)
        self.retention_policies = {
            'database_backups': 7,    # Keep database backups for 7 days
            'log_backups': 3,         # Keep log backups for 3 days
            'general_logs': 14        # Keep general logs for 14 days
        }
    
    def get_backup_files(self) -> Dict[str, List[Path]]:
        """Get all backup files categorized by type."""
        patterns = {
            'database_backups': ['*.db.backup_*', '*.backup_*.db'],
            'log_backups': ['*.log.backup*'],
            'general_logs': ['*.log', '!*.log.backup*']  # Exclude backup logs
        }
        
        results = {}
        for category, pattern_list in patterns.items():
            files = []
            for pattern in pattern_list:
                if pattern.startswith('!'):
                    # Exclusion pattern - skip for now
                    continue
                files.extend(self.base_dir.glob(pattern))
            results[category] = files
        
        return results
    
    def parse_backup_timestamp(self, filepath: Path) -> datetime:
        """Extract timestamp from backup filename."""
        filename = filepath.name
        
        # Try different timestamp formats
        formats = [
            '%Y%m%d_%H%M%S',  # backup_20250817_124404
            '%Y-%m-%d_%H-%M-%S',
            '%Y%m%d'
        ]
        
        for fmt in formats:
            for part in filename.split('_'):
                try:
                    return datetime.strptime(part, fmt)
                except ValueError:
                    continue
        
        # Fallback to file modification time
        return datetime.fromtimestamp(filepath.stat().st_mtime)
    
    def should_delete(self, filepath: Path, category: str) -> bool:
        """Determine if a backup file should be deleted based on retention policy."""
        retention_days = self.retention_policies.get(category, 7)
        file_date = self.parse_backup_timestamp(filepath)
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        return file_date < cutoff_date
    
    def cleanup_old_backups(self, dry_run: bool = True) -> Dict[str, Any]:
        """Clean up old backup files according to retention policy."""
        results = {
            'deleted_files': [],
            'kept_files': [],
            'errors': [],
            'dry_run': dry_run
        }
        
        backup_files = self.get_backup_files()
        
        for category, files in backup_files.items():
            logger.info(f"Processing {category}: {len(files)} files")
            
            for filepath in files:
                try:
                    if self.should_delete(filepath, category):
                        if not dry_run:
                            filepath.unlink()
                            logger.info(f"Deleted old backup: {filepath}")
                        results['deleted_files'].append({
                            'path': str(filepath),
                            'category': category,
                            'age_days': (datetime.now() - self.parse_backup_timestamp(filepath)).days
                        })
                    else:
                        results['kept_files'].append({
                            'path': str(filepath),
                            'category': category
                        })
                        
                except Exception as e:
                    error_msg = f"Error processing {filepath}: {str(e)}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)
        
        return results
    
    def get_retention_summary(self) -> Dict[str, Any]:
        """Get summary of current backup files and retention status."""
        backup_files = self.get_backup_files()
        summary = {}
        
        for category, files in backup_files.items():
            retention_days = self.retention_policies[category]
            category_summary = {
                'total_files': len(files),
                'retention_days': retention_days,
                'files_to_delete': 0,
                'files_to_keep': 0,
                'oldest_file': None,
                'newest_file': None
            }
            
            if files:
                file_dates = [self.parse_backup_timestamp(f) for f in files]
                category_summary['oldest_file'] = min(file_dates).isoformat()
                category_summary['newest_file'] = max(file_dates).isoformat()
                
                for filepath in files:
                    if self.should_delete(filepath, category):
                        category_summary['files_to_delete'] += 1
                    else:
                        category_summary['files_to_keep'] += 1
            
            summary[category] = category_summary
        
        return summary

def main():
    """Demo of backup retention manager."""
    manager = BackupRetentionManager()
    
    print("Current Backup Status:")
    print("=" * 30)
    summary = manager.get_retention_summary()
    for category, info in summary.items():
        print(f"\n{category}:")
        print(f"  Files: {info['total_files']}")
        print(f"  Retention: {info['retention_days']} days")
        print(f"  To delete: {info['files_to_delete']}")
        print(f"  To keep: {info['files_to_keep']}")
    
    print("\nDry Run Cleanup:")
    print("=" * 20)
    results = manager.cleanup_old_backups(dry_run=True)
    print(f"Would delete: {len(results['deleted_files'])} files")
    print(f"Would keep: {len(results['kept_files'])} files")

if __name__ == "__main__":
    main()