"""
Insights Service - AI-powered contextual insights generation
Leverages Claude Agent SDK for deep content analysis and pattern detection
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)


class InsightCategory:
    ACTION = "action"
    PATTERN = "pattern" 
    RELATIONSHIP = "relationship"
    TEMPORAL = "temporal"
    OPPORTUNITY = "opportunity"
    QUALITY = "quality"
    VELOCITY = "velocity"
    RISK = "risk"
    DOCUMENTATION = "documentation"
    FOLLOW_UPS = "follow-ups"


class Insight:
    def __init__(
        self,
        category: str,
        priority: str,
        title: str,
        content: str,
        related_files: List[str],
        evidence: Dict[str, Any],
        timestamp: datetime = None,
        insight_id: str = None,
        source_section: str = None,
        source_pointers: List[str] = None,
        generated_by_agent: str = None,
        dismissed: bool = False,
        archived: bool = False
    ):
        self.id = insight_id or f"{category}_{datetime.utcnow().timestamp()}"
        self.category = category
        self.priority = priority  # low, medium, high, critical
        self.title = title
        self.content = content
        self.related_files = related_files
        self.evidence = evidence  # AI reasoning and source data
        self.timestamp = timestamp or datetime.utcnow()
        self.dismissed = dismissed
        self.archived = archived
        self.source_section = source_section
        self.source_pointers = source_pointers or []
        self.generated_by_agent = generated_by_agent

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'category': self.category,
            'priority': self.priority,
            'title': self.title,
            'content': self.content,
            'relatedFiles': self.related_files,
            'evidence': self.evidence,
            'timestamp': self.timestamp.isoformat(),
            'dismissed': self.dismissed,
            'archived': self.archived,
            'sourceSection': self.source_section,
            'sourcePointers': self.source_pointers,
            'generatedByAgent': self.generated_by_agent
        }


class InsightsGenerator:
    """Generates contextual insights using Claude Agent SDK"""
    
    def __init__(self):
        # Initialize aggregator for real implementation
        from .insights_aggregator import InsightsAggregator
        self.aggregator = InsightsAggregator()
        
    async def generate_insights(self,
                               time_range_days: int = 7,
                               max_insights: int = 12,
                               progress_callback=None) -> List[Insight]:
        """Generate insights for the specified time range"""
        try:
            # Collect signals from all sources
            insights = await self.aggregator.collect_all_signals_and_generate_insights(
                time_range_days=time_range_days,
                max_insights=max_insights,
                progress_callback=progress_callback
            )
            
            # Convert to Insight objects
            insight_objects = []
            for insight_data in insights:
                insight = Insight(
                    category=insight_data['category'],
                    priority=insight_data['priority'],
                    title=insight_data['title'],
                    content=insight_data['content'],
                    related_files=insight_data.get('related_files', []),
                    evidence=insight_data.get('evidence', {}),
                    timestamp=datetime.fromisoformat(insight_data['timestamp']) if insight_data.get('timestamp') else None,
                    source_section=insight_data.get('source_section', 'aggregated'),
                    source_pointers=insight_data.get('source_pointers', []),
                    generated_by_agent=insight_data.get('generated_by_agent', 'claude-sdk')
                )
                insight_objects.append(insight)
            
            logger.info(f"Generated {len(insight_objects)} insights")
            return insight_objects
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return []


class InsightsService:
    """Main service for insights operations"""
    
    def __init__(self):
        self.generator = InsightsGenerator()
        
    async def get_insights(self,
                          time_range_days: int = 7,
                          max_insights: int = 12,
                          include_dismissed: bool = False,
                          category: str = None,
                          priority: str = None,
                          source_section: str = None) -> List[Dict[str, Any]]:
        """Get insights for the specified time range"""
        try:
            from database.models import InsightModel

            # Fetch insights from database with filters
            insights = InsightModel.get_insights(
                limit=max_insights,
                category=category,
                priority=priority,
                source_section=source_section,
                include_dismissed=include_dismissed,
                include_archived=False,  # Don't include archived by default
                max_age_days=time_range_days
            )

            return insights

        except Exception as e:
            logger.error(f"Error getting insights: {e}")
            return []
    
    async def dismiss_insight(self, insight_id: str) -> bool:
        """Mark an insight as dismissed"""
        try:
            from database.models import InsightModel
            success = InsightModel.dismiss_insight(int(insight_id))
            
            if success:
                logger.info(f"Dismissed insight {insight_id}")
            else:
                logger.warning(f"Insight {insight_id} not found for dismissal")
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to dismiss insight {insight_id}: {e}")
            return False
    
    async def archive_insight(self, insight_id: str) -> bool:
        """Archive an insight"""
        try:
            from database.models import InsightModel
            success = InsightModel.archive_insight(int(insight_id))
            
            if success:
                logger.info(f"Archived insight {insight_id}")
            else:
                logger.warning(f"Insight {insight_id} not found for archiving")
                
            return success
            
        except Exception as e:
            logger.error(f"Failed to archive insight {insight_id}: {e}")
            return False
    
    async def refresh_insights(self, time_range_days: int = 7, max_insights: int = 12,
                         force_refresh: bool = False, progress_callback=None) -> Dict[str, Any]:
        """Force refresh of insights generation"""
        try:
            from database.models import ConfigModel, InsightModel

            # Check if refresh is needed
            if not force_refresh:
                last_refresh = ConfigModel.get('insights_last_refresh', None)
                if last_refresh:
                    last_refresh_time = datetime.fromisoformat(last_refresh)
                    time_since_refresh = datetime.now() - last_refresh_time
                    refresh_interval = ConfigModel.get('insights_refresh_interval', 3600)  # 1 hour default

                    if time_since_refresh.total_seconds() < refresh_interval:
                        return {
                            'success': True,
                            'message': 'Insights refresh not needed yet',
                            'last_refresh': last_refresh
                        }

            # Clean up old insights
            max_age_days = ConfigModel.get('insights_max_age_days', 30)
            InsightModel.cleanup_old_insights(max_age_days)

            # Generate new insights with progress callback
            insights = await self.generator.generate_insights(
                time_range_days=time_range_days,
                max_insights=max_insights,
                progress_callback=progress_callback
            )
            
            # Store generated insights
            for insight_data in insights:
                try:
                    # Parse timestamp with error handling
                    timestamp = None
                    if insight_data.get('timestamp'):
                        try:
                            timestamp = datetime.fromisoformat(insight_data['timestamp'])
                        except (ValueError, TypeError) as e:
                            logger.warning(f"Invalid timestamp format: {insight_data.get('timestamp')}, using current time")
                            timestamp = datetime.now()

                    insight_id = InsightModel.create(
                        category=insight_data['category'],
                        priority=insight_data['priority'],
                        title=insight_data['title'],
                        content=insight_data['content'],
                        evidence_payload=insight_data.get('evidence_payload'),
                        related_entities=','.join(insight_data.get('related_files', [])),
                        source_section=insight_data.get('source_section', 'aggregated'),
                        source_pointers=','.join(insight_data.get('source_pointers', [])),
                        generated_by_agent=insight_data.get('generated_by_agent', 'claude-sdk'),
                        timestamp=timestamp
                    )
                    
                    if insight_id:
                        insight_data['id'] = str(insight_id)
                        logger.debug(f"Stored insight {insight_id}: {insight_data['title']}")
                        
                except Exception as e:
                    logger.error(f"Failed to store insight: {e}")
            
            # Update last refresh timestamp
            ConfigModel.set('insights_last_refresh', datetime.now().isoformat(), 'Last insights refresh timestamp')
            
            return {
                'success': True,
                'message': f'Refreshed insights with {len(insights)} items',
                'insights': [
                    insight.to_dict() if hasattr(insight, 'to_dict') else insight
                    for insight in insights
                ],
                'last_refresh': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to refresh insights: {e}")
            return {
                'success': False,
                'message': f'Failed to refresh insights: {str(e)}'
            }
    
    async def get_insights_stats(self) -> Dict[str, Any]:
        """Get statistics about insights"""
        try:
            from database.models import InsightModel
            return InsightModel.get_insights_stats()
            
        except Exception as e:
            logger.error(f"Failed to get insights stats: {e}")
            return {}