# alerts/__init__.py
"""
Live Signals + Alerts module (Sprint 4).

Provides in-app alerts driven by NBA availability changes.
BEST tier only.
"""

from alerts.models import Alert, AlertType, AlertSeverity
from alerts.service import AlertService, get_alert_service, check_for_alerts

__all__ = [
    "Alert",
    "AlertType",
    "AlertSeverity",
    "AlertService",
    "get_alert_service",
    "check_for_alerts",
]
