"""
Notification Templates for S20.
Defines templates for different notification types with consistent formatting.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class TemplateType(str, Enum):
    """Supported notification template types."""
    OPPORTUNITY_ALERT = "opportunity_alert"
    SYSTEM_ALERT = "system_alert"
    CONSTRAINT_VIOLATION = "constraint_violation"


@dataclass
class NotificationTemplate:
    """Template for generating notification content."""
    template_type: TemplateType
    title_template: str
    body_template: str
    priority: str
    default_channels: List[str]
    required_fields: List[str]
    optional_fields: List[str]


class NotificationTemplates:
    """
    Notification Templates Service.
    
    Provides standardized templates for different notification types,
    ensuring consistent messaging across the platform.
    """
    
    def __init__(self):
        self._templates: Dict[TemplateType, NotificationTemplate] = {
            # =================================================================
            # Opportunity Alert Template
            # =================================================================
            TemplateType.OPPORTUNITY_ALERT: NotificationTemplate(
                template_type=TemplateType.OPPORTUNITY_ALERT,
                title_template="🏆 {sport}: {opportunity_type}",
                body_template=("""{player_team} vs {opponent}

📊 Edge: +{edge_percent}% | Confidence: {confidence_score}/100
💰 Suggested: {suggested_bet}
📈 Odds: {odds_display}

{context_note}"""),
                priority="normal",
                default_channels=["in_app"],
                required_fields=[
                    "sport", "opportunity_type", "player_team", "opponent",
                    "edge_percent", "confidence_score", "suggested_bet", "odds_display"
                ],
                optional_fields=[
                    "context_note", "game_time", "market_type", "line_value"
                ]
            ),
            
            # =================================================================
            # System Alert Template
            # =================================================================
            TemplateType.SYSTEM_ALERT: NotificationTemplate(
                template_type=TemplateType.SYSTEM_ALERT,
                title_template="🔔 {alert_level}: {alert_category}",
                body_template="{message}\n\n{details}",
                priority="high",
                default_channels=["in_app"],
                required_fields=["alert_level", "alert_category", "message"],
                optional_fields=["details", "action_required", "action_link"]
            ),
            
            # =================================================================
            # Constraint Violation Template
            # =================================================================
            TemplateType.CONSTRAINT_VIOLATION: NotificationTemplate(
                template_type=TemplateType.CONSTRAINT_VIOLATION,
                title_template="⚠️ Constraint Alert: {constraint_name}",
                body_template=("""Your DNA constraint "{constraint_name}" would be violated by this opportunity.

❌ Issue: {violation_reason}
📊 Your Limit: {constraint_limit}
🎯 This Bet: {bet_value}

{recommendation}"""),
                priority="normal",
                default_channels=["in_app"],
                required_fields=[
                    "constraint_name", "violation_reason", "constraint_limit", "bet_value"
                ],
                optional_fields=[
                    "recommendation", "alternative_suggestion", "confidence_impact"
                ]
            ),
        }
        
        logger.info("NotificationTemplates service initialized")
    
    # =========================================================================
    # Template Rendering
    # =========================================================================
    
    def render(
        self,
        template_type: TemplateType,
        data: Dict[str, Any],
        custom_title: Optional[str] = None,
        custom_body: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Render a notification template with provided data.
        
        Args:
            template_type: Type of template to use
            data: Data to populate template fields
            custom_title: Optional override for title
            custom_body: Optional override for body
            
        Returns:
            Dict with rendered title, body, and metadata
        """
        template = self._templates.get(template_type)
        
        if not template:
            logger.error(f"Unknown template type: {template_type}")
            return self._render_fallback(template_type, data)
        
        # Validate required fields
        missing_fields = [
            f for f in template.required_fields
            if f not in data or data[f] is None
        ]
        
        if missing_fields:
            logger.warning(f"Missing required fields for {template_type}: {missing_fields}")
            # Fill with defaults
            for field in missing_fields:
                data[field] = "N/A"
        
        # Render title and body
        try:
            title = custom_title or template.title_template.format(**data)
            body = custom_body or template.body_template.format(**data)
        except KeyError as e:
            logger.error(f"Template rendering error for {template_type}: {e}")
            title = custom_title or f"Notification: {template_type.value}"
            body = custom_body or str(data)
        
        return {
            "title": title,
            "body": body,
            "priority": template.priority,
            "channels": template.default_channels.copy(),
            "template_type": template_type.value,
            "missing_fields": missing_fields,
            "rendered_at": datetime.utcnow().isoformat()
        }
    
    def render_opportunity_alert(
        self,
        sport: str,
        player_team: str,
        opponent: str,
        suggested_bet: str,
        odds_display: str,
        edge_percent: float,
        confidence_score: float,
        opportunity_type: str = "Edge Detected",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Render an opportunity alert notification.
        
        Args:
            sport: Sport name (NBA, NFL, etc.)
            player_team: Player or team name
            opponent: Opposing team
            suggested_bet: The suggested bet description
            odds_display: Formatted odds string
            edge_percent: Edge percentage
            confidence_score: Confidence score (0-100)
            opportunity_type: Type of opportunity
            **kwargs: Optional fields (context_note, game_time, etc.)
            
        Returns:
            Rendered notification dict
        """
        data = {
            "sport": sport,
            "player_team": player_team,
            "opponent": opponent,
            "suggested_bet": suggested_bet,
            "odds_display": odds_display,
            "edge_percent": round(edge_percent, 1),
            "confidence_score": round(confidence_score, 0),
            "opportunity_type": opportunity_type,
            "context_note": kwargs.get("context_note", ""),
            "game_time": kwargs.get("game_time", ""),
            "market_type": kwargs.get("market_type", ""),
            "line_value": kwargs.get("line_value", "")
        }
        
        # Add default context note if not provided
        if not data["context_note"]:
            data["context_note"] = "This opportunity aligns with your DNA preferences."
        
        return self.render(TemplateType.OPPORTUNITY_ALERT, data)
    
    def render_system_alert(
        self,
        alert_level: str,  # info, warning, critical
        alert_category: str,
        message: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Render a system alert notification.
        
        Args:
            alert_level: info, warning, or critical
            alert_category: Category of alert
            message: Main alert message
            **kwargs: Optional fields (details, action_required, etc.)
            
        Returns:
            Rendered notification dict
        """
        # Emoji mapping for alert levels
        level_emojis = {
            "info": "ℹ️",
            "warning": "⚠️",
            "critical": "🚨"
        }
        
        data = {
            "alert_level": f"{level_emojis.get(alert_level.lower(), '🔔')} {alert_level.upper()}",
            "alert_category": alert_category,
            "message": message,
            "details": kwargs.get("details", ""),
            "action_required": kwargs.get("action_required", ""),
            "action_link": kwargs.get("action_link", "")
        }
        
        # Adjust priority based on alert level
        priority_map = {
            "info": "low",
            "warning": "high",
            "critical": "urgent"
        }
        
        result = self.render(TemplateType.SYSTEM_ALERT, data)
        result["priority"] = priority_map.get(alert_level.lower(), "normal")
        
        return result
    
    def render_constraint_violation(
        self,
        constraint_name: str,
        violation_reason: str,
        constraint_limit: str,
        bet_value: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Render a constraint violation notification.
        
        Args:
            constraint_name: Name of the violated constraint
            violation_reason: Explanation of the violation
            constraint_limit: The limit that was set
            bet_value: The value that violated the limit
            **kwargs: Optional fields (recommendation, alternative_suggestion, etc.)
            
        Returns:
            Rendered notification dict
        """
        data = {
            "constraint_name": constraint_name,
            "violation_reason": violation_reason,
            "constraint_limit": constraint_limit,
            "bet_value": bet_value,
            "recommendation": kwargs.get("recommendation", ""),
            "alternative_suggestion": kwargs.get("alternative_suggestion", ""),
            "confidence_impact": kwargs.get("confidence_impact", "")
        }
        
        # Default recommendation if not provided
        if not data["recommendation"]:
            data["recommendation"] = "💡 Tip: Adjust your constraint in DNA settings if this limit no longer fits your strategy."
        
        return self.render(TemplateType.CONSTRAINT_VIOLATION, data)
    
    # =========================================================================
    # Template Management
    # =========================================================================
    
    def get_template(self, template_type: TemplateType) -> Optional[NotificationTemplate]:
        """Get a template by type."""
        return self._templates.get(template_type)
    
    def get_template_fields(self, template_type: TemplateType) -> Dict[str, List[str]]:
        """
        Get required and optional fields for a template.
        
        Returns:
            Dict with 'required' and 'optional' field lists
        """
        template = self._templates.get(template_type)
        
        if not template:
            return {"required": [], "optional": []}
        
        return {
            "required": template.required_fields.copy(),
            "optional": template.optional_fields.copy()
        }
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """List all available templates."""
        return [
            {
                "type": t.template_type.value,
                "priority": t.priority,
                "channels": t.default_channels.copy(),
                "required_fields": t.required_fields.copy(),
                "optional_fields": t.optional_fields.copy()
            }
            for t in self._templates.values()
        ]
    
    def validate_template_data(
        self,
        template_type: TemplateType,
        data: Dict[str, Any]
    ) -> tuple[bool, List[str]]:
        """
        Validate data against template requirements.
        
        Returns:
            Tuple of (is_valid, list_of_missing_fields)
        """
        template = self._templates.get(template_type)
        
        if not template:
            return False, [f"Unknown template type: {template_type}"]
        
        missing = [
            f for f in template.required_fields
            if f not in data or data[f] is None
        ]
        
        return len(missing) == 0, missing
    
    def _render_fallback(
        self,
        template_type: TemplateType,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fallback rendering for unknown template types."""
        return {
            "title": f"Notification: {template_type.value if hasattr(template_type, 'value') else str(template_type)}",
            "body": str(data),
            "priority": "normal",
            "channels": ["in_app"],
            "template_type": "fallback",
            "missing_fields": [],
            "rendered_at": datetime.utcnow().isoformat()
        }


# Singleton instance
_templates_instance: Optional[NotificationTemplates] = None


def get_notification_templates() -> NotificationTemplates:
    """Get or create the singleton NotificationTemplates instance."""
    global _templates_instance
    if _templates_instance is None:
        _templates_instance = NotificationTemplates()
    return _templates_instance


# Convenience functions
def render_opportunity_alert(**kwargs) -> Dict[str, Any]:
    """Convenience function to render an opportunity alert."""
    return get_notification_templates().render_opportunity_alert(**kwargs)


def render_system_alert(**kwargs) -> Dict[str, Any]:
    """Convenience function to render a system alert."""
    return get_notification_templates().render_system_alert(**kwargs)


def render_constraint_violation(**kwargs) -> Dict[str, Any]:
    """Convenience function to render a constraint violation."""
    return get_notification_templates().render_constraint_violation(**kwargs)


# Template examples for documentation
TEMPLATE_EXAMPLES = {
    "opportunity_alert": {
        "title": "🏆 NBA: Edge Detected",
        "body": """Lakers vs Warriors

📊 Edge: +12.5% | Confidence: 85/100
💰 Suggested: LeBron James Over 28.5 Points
📈 Odds: -110

This opportunity aligns with your DNA preferences.""",
        "data": {
            "sport": "NBA",
            "player_team": "Lakers",
            "opponent": "Warriors",
            "suggested_bet": "LeBron James Over 28.5 Points",
            "odds_display": "-110",
            "edge_percent": 12.5,
            "confidence_score": 85
        }
    },
    "system_alert": {
        "title": "🚨 CRITICAL: Service Disruption",
        "body": """Odds data feed is experiencing delays.

We're working to restore full service. Live odds may be temporarily unavailable.""",
        "data": {
            "alert_level": "critical",
            "alert_category": "Service Disruption",
            "message": "Odds data feed is experiencing delays."
        }
    },
    "constraint_violation": {
        "title": "⚠️ Constraint Alert: Max Bet Size",
        "body": """Your DNA constraint "Max Bet Size" would be violated by this opportunity.

❌ Issue: Bet size exceeds your $100 limit
📊 Your Limit: $100
🎯 This Bet: $150

💡 Tip: Adjust your constraint in DNA settings if this limit no longer fits your strategy.""",
        "data": {
            "constraint_name": "Max Bet Size",
            "violation_reason": "Bet size exceeds your $100 limit",
            "constraint_limit": "$100",
            "bet_value": "$150"
        }
    }
}
