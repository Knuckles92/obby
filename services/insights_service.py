"""
Insights Service Layer

Manages the insights plugin system, providing registration, discovery,
and calculation of insights across all available plugins.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

from backend.insights.base import BaseInsight, InsightResult
from backend.insights.plugins import (
    FileActivityInsight,
    PeakActivityInsight,
    TrendingFilesInsight,
    CodeMetricsInsight,
    StaleTodosInsight,
    OrphanMentionsInsight,
)

logger = logging.getLogger(__name__)


class InsightsService:
    """
    Service layer for managing and executing insight calculations.

    This service maintains a registry of all available insight plugins
    and provides methods to discover, configure, and execute them.
    """

    def __init__(self):
        """Initialize the insights service and register all plugins."""
        self._registry: Dict[str, BaseInsight] = {}
        self._register_default_plugins()

    def _register_default_plugins(self) -> None:
        """Register all default insight plugins."""
        # Activity plugins (Tier 1)
        activity_plugins = [
            FileActivityInsight(),
            PeakActivityInsight(),
            TrendingFilesInsight(),
            CodeMetricsInsight(),
        ]

        # Semantic plugins (Tier 2)
        semantic_plugins = [
            StaleTodosInsight(),
            OrphanMentionsInsight(),
        ]

        all_plugins = activity_plugins + semantic_plugins
        for plugin in all_plugins:
            self.register_plugin(plugin)

        logger.info(f"Registered {len(all_plugins)} insight plugins "
                   f"({len(activity_plugins)} activity, {len(semantic_plugins)} semantic)")

    def register_plugin(self, plugin: BaseInsight) -> None:
        """
        Register a new insight plugin.

        Args:
            plugin: Instance of an insight plugin

        Raises:
            ValueError: If plugin ID is already registered
        """
        plugin_id = plugin.id
        if plugin_id in self._registry:
            logger.warning(f"Plugin {plugin_id} is already registered, replacing")

        self._registry[plugin_id] = plugin
        logger.info(f"Registered insight plugin: {plugin_id}")

    def get_plugin(self, plugin_id: str) -> Optional[BaseInsight]:
        """
        Get a specific insight plugin by ID.

        Args:
            plugin_id: Unique identifier of the plugin

        Returns:
            BaseInsight instance or None if not found
        """
        return self._registry.get(plugin_id)

    def get_available_insights(self) -> List[Dict[str, Any]]:
        """
        Get metadata for all available insight plugins.

        Returns:
            List of insight metadata dictionaries
        """
        return [
            plugin.metadata.to_dict()
            for plugin in self._registry.values()
        ]

    def calculate_insight(
        self,
        insight_id: str,
        start_date: datetime,
        end_date: datetime,
        config: Optional[Dict[str, Any]] = None
    ) -> InsightResult:
        """
        Calculate a specific insight.

        Args:
            insight_id: ID of the insight to calculate
            start_date: Start of analysis period
            end_date: End of analysis period
            config: Optional configuration parameters

        Returns:
            InsightResult with calculated data

        Raises:
            ValueError: If insight_id is not found
        """
        plugin = self.get_plugin(insight_id)
        if not plugin:
            raise ValueError(f"Insight plugin '{insight_id}' not found")

        logger.info(f"Calculating insight: {insight_id} from {start_date} to {end_date}")

        result = plugin.execute(start_date, end_date, config)

        if result.error:
            logger.error(f"Error calculating {insight_id}: {result.error}")
        else:
            logger.info(f"Successfully calculated {insight_id}")

        return result

    def calculate_multiple(
        self,
        insight_ids: List[str],
        start_date: datetime,
        end_date: datetime,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, InsightResult]:
        """
        Calculate multiple insights in batch.

        Args:
            insight_ids: List of insight IDs to calculate
            start_date: Start of analysis period
            end_date: End of analysis period
            config: Optional configuration parameters

        Returns:
            Dictionary mapping insight IDs to their results
        """
        results = {}

        for insight_id in insight_ids:
            try:
                result = self.calculate_insight(insight_id, start_date, end_date, config)
                results[insight_id] = result
            except Exception as e:
                logger.error(f"Error calculating insight {insight_id}: {e}")
                # Return error result for failed insights
                plugin = self.get_plugin(insight_id)
                if plugin:
                    results[insight_id] = InsightResult(
                        data={},
                        metadata=plugin.metadata,
                        error=str(e)
                    )

        logger.info(f"Calculated {len(results)} insights successfully")
        return results

    def get_insight_schema(self, insight_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the data schema for a specific insight.

        Args:
            insight_id: ID of the insight

        Returns:
            Schema dictionary or None if insight not found
        """
        plugin = self.get_plugin(insight_id)
        if not plugin:
            return None

        return plugin.get_schema()

    def get_default_layout_config(self, layout_name: str) -> Dict[str, Any]:
        """
        Get default insight configuration for a specific layout.

        Args:
            layout_name: Name of the layout (e.g., 'masonry', 'dashboard')

        Returns:
            Default configuration dictionary
        """
        # Define sensible defaults for each layout
        layout_defaults = {
            "masonry": {
                "insights": [
                    {"id": "file_activity", "position": 0, "enabled": True},
                    {"id": "peak_activity", "position": 1, "enabled": True},
                    {"id": "code_metrics", "position": 2, "enabled": True},
                    {"id": "trending_files", "position": 3, "enabled": True},
                ]
            },
            "dashboard": {
                "insights": [
                    {"id": "file_activity", "position": 0, "enabled": True},
                    {"id": "peak_activity", "position": 1, "enabled": True},
                    {"id": "code_metrics", "position": 2, "enabled": True},
                    {"id": "trending_files", "position": 3, "enabled": True},
                ]
            },
            "minimalist": {
                "insights": [
                    {"id": "file_activity", "position": 0, "enabled": True},
                    {"id": "peak_activity", "position": 1, "enabled": True},
                ]
            },
            "timeline": {
                "insights": [
                    {"id": "file_activity", "position": 0, "enabled": True},
                    {"id": "peak_activity", "position": 1, "enabled": True},
                    {"id": "trending_files", "position": 2, "enabled": True},
                ]
            },
        }

        # Return layout-specific defaults or general default
        return layout_defaults.get(
            layout_name,
            {
                "insights": [
                    {"id": "file_activity", "position": 0, "enabled": True},
                    {"id": "peak_activity", "position": 1, "enabled": True},
                ]
            }
        )


# Singleton instance
_insights_service = None


def get_insights_service() -> InsightsService:
    """
    Get the singleton insights service instance.

    Returns:
        InsightsService instance
    """
    global _insights_service
    if _insights_service is None:
        _insights_service = InsightsService()
    return _insights_service



