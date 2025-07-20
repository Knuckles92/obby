"""
SQLite Database Layer for Obby
==============================

This module provides database infrastructure for migrating from file-based storage
to SQLite, eliminating data loss, ID collisions, and performance issues.

Parallel Subagent Architecture:
- Subagent A: Schema Design & Database Infrastructure  
- Subagent B: Data Migration & Legacy Import
- Subagent C: API Integration & Query Optimization
"""

__version__ = "1.0.0"
__all__ = ["models", "migration", "queries"]