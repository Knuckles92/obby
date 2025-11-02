"""
Pluggable insights system for Obby.

This package provides a flexible architecture for calculating and displaying
various insights about file monitoring activity, code changes, and work patterns.
"""

from .base import (
    BaseInsight,
    InsightCategory,
    InsightMetadata,
    InsightResult,
    InsightSize,
)

__all__ = [
    "BaseInsight",
    "InsightCategory",
    "InsightMetadata",
    "InsightResult",
    "InsightSize",
]
