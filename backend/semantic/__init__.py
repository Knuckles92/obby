"""
Semantic Insights Module
========================

AI-powered semantic analysis for notes, extracting entities,
discovering connections, and generating actionable insights.

Components:
- scheduler: Manages when and how often semantic processing runs
- processor: Coordinates the processing pipeline
- entity_extractor: AI-powered entity extraction from notes
- embeddings: Vector embeddings for similarity search (Phase 2)
"""

from .scheduler import SemanticInsightScheduler
from .processor import SemanticProcessor
from .entity_extractor import EntityExtractor

__all__ = [
    'SemanticInsightScheduler',
    'SemanticProcessor',
    'EntityExtractor',
]
