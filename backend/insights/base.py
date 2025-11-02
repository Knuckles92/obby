"""
Base classes for the pluggable insights system.

This module defines the abstract interface that all insight plugins must implement,
enabling a flexible and extensible insights architecture.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum


class InsightSize(str, Enum):
    """Standard sizes for insight cards in layouts."""
    SMALL = "small"      # 1x1 grid space
    MEDIUM = "medium"    # 2x1 grid space
    LARGE = "large"      # 2x2 grid space
    WIDE = "wide"        # Full width


class InsightCategory(str, Enum):
    """Categories for organizing insights."""
    ACTIVITY = "activity"
    CODE = "code"
    SEMANTIC = "semantic"
    TRENDS = "trends"
    PERFORMANCE = "performance"
    SESSION = "session"


class InsightMetadata:
    """Metadata describing an insight card's appearance and behavior."""

    def __init__(
        self,
        id: str,
        title: str,
        description: str,
        icon: str,
        color: str,
        category: InsightCategory,
        default_size: InsightSize = InsightSize.MEDIUM,
        supports_drill_down: bool = False
    ):
        self.id = id
        self.title = title
        self.description = description
        self.icon = icon  # Lucide icon name
        self.color = color  # CSS color or theme variable
        self.category = category
        self.default_size = default_size
        self.supports_drill_down = supports_drill_down

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary for API responses."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "icon": self.icon,
            "color": self.color,
            "category": self.category.value,
            "defaultSize": self.default_size.value,
            "supportsDrillDown": self.supports_drill_down
        }


class InsightResult:
    """Standardized result from an insight calculation."""

    def __init__(
        self,
        data: Dict[str, Any],
        metadata: InsightMetadata,
        calculated_at: Optional[datetime] = None,
        error: Optional[str] = None
    ):
        self.data = data
        self.metadata = metadata
        self.calculated_at = calculated_at or datetime.now()
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary for API responses."""
        return {
            "data": self.data,
            "metadata": self.metadata.to_dict(),
            "calculatedAt": self.calculated_at.isoformat(),
            "error": self.error
        }


class BaseInsight(ABC):
    """
    Abstract base class for all insight plugins.

    Each insight plugin must implement this interface to be compatible
    with the insights system. Insights are self-contained calculators
    that analyze monitoring data and return structured results.
    """

    def __init__(self):
        """Initialize the insight plugin."""
        self._metadata = self.get_metadata()

    @abstractmethod
    def get_metadata(self) -> InsightMetadata:
        """
        Return metadata describing this insight.

        Returns:
            InsightMetadata: Metadata including title, icon, color, etc.
        """
        pass

    @abstractmethod
    def calculate(
        self,
        start_date: datetime,
        end_date: datetime,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calculate the insight for the given time range.

        Args:
            start_date: Start of analysis period
            end_date: End of analysis period
            config: Optional configuration parameters specific to this insight

        Returns:
            Dict containing the calculated insight data with the following structure:
            {
                "value": <primary metric value>,
                "label": <optional label for the value>,
                "trend": <optional trend indicator: "up", "down", "stable">,
                "trendValue": <optional numeric trend percentage>,
                "chart": <optional chart data>,
                "details": <optional detailed breakdown>,
                "status": <optional status: "success", "warning", "error">,
                "message": <optional human-readable message>
            }
        """
        pass

    def get_schema(self) -> Dict[str, Any]:
        """
        Return the expected data schema for this insight.

        This helps frontend components understand what data to expect
        and how to render it appropriately.

        Returns:
            Dict describing the data structure returned by calculate()
        """
        return {
            "value": "string | number",
            "label": "string?",
            "trend": "'up' | 'down' | 'stable'?",
            "trendValue": "number?",
            "chart": "object?",
            "details": "object?",
            "status": "'success' | 'warning' | 'error'?",
            "message": "string?"
        }

    def validate_date_range(self, start_date: datetime, end_date: datetime) -> None:
        """
        Validate the provided date range.

        Args:
            start_date: Start of analysis period
            end_date: End of analysis period

        Raises:
            ValueError: If date range is invalid
        """
        if start_date > end_date:
            raise ValueError("start_date must be before or equal to end_date")

        if end_date > datetime.now():
            raise ValueError("end_date cannot be in the future")

    def execute(
        self,
        start_date: datetime,
        end_date: datetime,
        config: Optional[Dict[str, Any]] = None
    ) -> InsightResult:
        """
        Execute the insight calculation with error handling.

        This is the main entry point for calculating insights. It wraps
        the calculate() method with validation and error handling.

        Args:
            start_date: Start of analysis period
            end_date: End of analysis period
            config: Optional configuration parameters

        Returns:
            InsightResult: Standardized result object
        """
        try:
            # Validate inputs
            self.validate_date_range(start_date, end_date)

            # Calculate the insight
            data = self.calculate(start_date, end_date, config)

            # Return success result
            return InsightResult(
                data=data,
                metadata=self._metadata,
                calculated_at=datetime.now(),
                error=None
            )

        except Exception as e:
            # Return error result
            return InsightResult(
                data={},
                metadata=self._metadata,
                calculated_at=datetime.now(),
                error=str(e)
            )

    @property
    def id(self) -> str:
        """Get the unique identifier for this insight."""
        return self._metadata.id

    @property
    def metadata(self) -> InsightMetadata:
        """Get the metadata for this insight."""
        return self._metadata
