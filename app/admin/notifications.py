"""
Admin Notifications Dashboard

Provides admin interface for monitoring and managing the notification system.
Includes stats, recent notifications, and emergency kill switch.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session

from app.models.notification_event import NotificationEvent
from app.models.eligible_opportunity import EligibleOpportunity
from app.models.user_preferences import UserPreferences
from app.models.notification_receipt import NotificationReceipt, get_telemetry_counters


# =============================================================================
# Kill Switch State (In-memory for fast access, persisted to DB)
# =============================================================================

class NotificationKillSwitch:
    """Global kill switch for emergency notification shutdown."""
    
    _instance = None
    _enabled = False
    _reason = None
    _triggered_at = None
    _triggered_by = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @property
    def enabled(self) -> bool:
        """Check if kill switch is engaged."""
        return self._enabled
    
    def engage(self, reason: str, triggered_by: str):
        """Engage the kill switch to stop all notifications."""
        self._enabled = True
        self._reason = reason
        self._triggered_at = datetime.utcnow()
        self._triggered_by = triggered_by
    
    def disengage(self, triggered_by: str):
        """Disengage the kill switch to resume notifications."""
        self._enabled = False
        self._reason = None
        self._triggered_at = None
        self._triggered_by = triggered_by
    
    def get_status(self) -> Dict[str, Any]:
        """Get current kill switch status."""
        return {
            "enabled": self._enabled,
            "reason": self._reason,
            "triggered_at": self._triggered_at.isoformat() if self._triggered_at else None,
            "triggered_by": self._triggered_by
        }


# Global kill switch instance
_kill_switch = NotificationKillSwitch()


def get_kill_switch() -> NotificationKillSwitch:
    """Get the global kill switch instance."""
    return _kill_switch


# =============================================================================
# Stats Data Classes
# =============================================================================

@dataclass
class NotificationStats:
    """Notification system statistics."""
    total_sent: int
    total_delivered: int
    total_read: int
    total_dismissed: int
    total_failed: int
    delivery_rate: float
    read_rate: float
    opt_out_rate: float
    period_hours: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_sent": self.total_sent,
            "total_delivered": self.total_delivered,
            "total_read": self.total_read,
            "total_dismissed": self.total_dismissed,
            "total_failed": self.total_failed,
            "delivery_rate": round(self.delivery_rate, 2),
            "read_rate": round(self.read_rate, 2),
            "opt_out_rate": round(self.opt_out_rate, 2),
            "period_hours": self.period_hours
        }


@dataclass
class NotificationTrend:
    """Notification trend data point."""
    timestamp: datetime
    sent: int
    delivered: int
    failed: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "sent": self.sent,
            "delivered": self.delivered,
            "failed": self.failed
        }


# =============================================================================
# Stats Functions
# =============================================================================

def get_notification_stats(
    db: Session,
    period_hours: int = 24,
    user_id: Optional[str] = None
) -> NotificationStats:
    """
    Get notification statistics for a given period.
    
    Args:
        db: Database session
        period_hours: Time period to analyze (default 24 hours)
        user_id: Optional user ID to filter by
    
    Returns:
        NotificationStats object with calculated metrics
    """
    since = datetime.utcnow() - timedelta(hours=period_hours)
    
    # Base query
    query = db.query(NotificationEvent).filter(
        NotificationEvent.sent_at >= since
    )
    
    if user_id:
        query = query.filter(NotificationEvent.user_id == user_id)
    
    # Count by status
    total_sent = query.count()
    
    total_delivered = query.filter(
        NotificationEvent.status.in_(['delivered', 'read', 'dismissed'])
    ).count()
    
    total_read = query.filter(
        NotificationEvent.status == 'read'
    ).count()
    
    total_dismissed = query.filter(
        NotificationEvent.status == 'dismissed'
    ).count()
    
    total_failed = query.filter(
        NotificationEvent.status == 'failed'
    ).count()
    
    # Calculate rates
    delivery_rate = (total_delivered / total_sent * 100) if total_sent > 0 else 0.0
    read_rate = (total_read / total_delivered * 100) if total_delivered > 0 else 0.0
    
    # Calculate opt-out rate (users who disabled notifications)
    total_users_with_prefs = db.query(UserPreferences).count()
    opted_out_users = db.query(UserPreferences).filter(
        UserPreferences.notification_rules['enabled'].astext == 'false'
    ).count()
    
    opt_out_rate = (opted_out_users / total_users_with_prefs * 100) if total_users_with_prefs > 0 else 0.0
    
    return NotificationStats(
        total_sent=total_sent,
        total_delivered=total_delivered,
        total_read=total_read,
        total_dismissed=total_dismissed,
        total_failed=total_failed,
        delivery_rate=delivery_rate,
        read_rate=read_rate,
        opt_out_rate=opt_out_rate,
        period_hours=period_hours
    )


def get_notification_trends(
    db: Session,
    period_hours: int = 24,
    interval_minutes: int = 60
) -> List[NotificationTrend]:
    """
    Get notification trends over time.
    
    Args:
        db: Database session
        period_hours: Total time period to analyze
        interval_minutes: Bucket size for grouping
    
    Returns:
        List of trend data points
    """
    since = datetime.utcnow() - timedelta(hours=period_hours)
    
    # Query notifications grouped by time buckets
    results = db.query(
        func.strftime('%Y-%m-%d %H:00:00', NotificationEvent.sent_at).label('hour'),
        func.count().label('sent'),
        func.sum(func.case([(NotificationEvent.status.in_(['delivered', 'read', 'dismissed']), 1)], else_=0)).label('delivered'),
        func.sum(func.case([(NotificationEvent.status == 'failed', 1)], else_=0)).label('failed')
    ).filter(
        NotificationEvent.sent_at >= since
    ).group_by(
        func.strftime('%Y-%m-%d %H:00:00', NotificationEvent.sent_at)
    ).order_by('hour').all()
    
    trends = []
    for row in results:
        trends.append(NotificationTrend(
            timestamp=datetime.fromisoformat(row.hour) if isinstance(row.hour, str) else row.hour,
            sent=row.sent or 0,
            delivered=row.delivered or 0,
            failed=row.failed or 0
        ))
    
    return trends


def get_recent_notifications(
    db: Session,
    limit: int = 50,
    status: Optional[str] = None,
    user_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Get recent notifications with optional filtering.
    
    Args:
        db: Database session
        limit: Maximum number of results
        status: Filter by status (optional)
        user_id: Filter by user (optional)
    
    Returns:
        List of notification dictionaries
    """
    query = db.query(NotificationEvent)
    
    if status:
        query = query.filter(NotificationEvent.status == status)
    
    if user_id:
        query = query.filter(NotificationEvent.user_id == user_id)
    
    notifications = query.order_by(
        NotificationEvent.sent_at.desc()
    ).limit(limit).all()
    
    return [n.to_dict() for n in notifications]


def get_opportunity_stats(db: Session, period_hours: int = 24) -> Dict[str, Any]:
    """
    Get eligible opportunity statistics.
    
    Args:
        db: Database session
        period_hours: Time period to analyze
    
    Returns:
        Dictionary with opportunity statistics
    """
    since = datetime.utcnow() - timedelta(hours=period_hours)
    
    total_detected = db.query(EligibleOpportunity).filter(
        EligibleOpportunity.detected_at >= since
    ).count()
    
    total_notified = db.query(EligibleOpportunity).filter(
        EligibleOpportunity.detected_at >= since,
        EligibleOpportunity.notification_sent == True
    ).count()
    
    total_placed = db.query(EligibleOpportunity).filter(
        EligibleOpportunity.detected_at >= since,
        EligibleOpportunity.status == 'placed'
    ).count()
    
    total_rejected = db.query(EligibleOpportunity).filter(
        EligibleOpportunity.detected_at >= since,
        EligibleOpportunity.status == 'rejected'
    ).count()
    
    conversion_rate = (total_placed / total_notified * 100) if total_notified > 0 else 0.0
    
    return {
        "total_detected": total_detected,
        "total_notified": total_notified,
        "total_placed": total_placed,
        "total_rejected": total_rejected,
        "conversion_rate": round(conversion_rate, 2),
        "period_hours": period_hours
    }


def get_dashboard_summary(db: Session) -> Dict[str, Any]:
    """
    Get complete dashboard summary for admin view.
    
    Args:
        db: Database session
    
    Returns:
        Dictionary with all dashboard data
    """
    # Get stats for different periods
    stats_24h = get_notification_stats(db, period_hours=24)
    stats_7d = get_notification_stats(db, period_hours=24 * 7)
    
    # Get trends
    trends = get_notification_trends(db, period_hours=24, interval_minutes=60)
    
    # Get opportunity stats
    opportunity_stats = get_opportunity_stats(db, period_hours=24)
    
    # Get kill switch status
    kill_switch = get_kill_switch().get_status()
    
    return {
        "stats_24h": stats_24h.to_dict(),
        "stats_7d": stats_7d.to_dict(),
        "trends": [t.to_dict() for t in trends],
        "opportunities": opportunity_stats,
        "kill_switch": kill_switch,
        "generated_at": datetime.utcnow().isoformat()
    }


# =============================================================================
# Admin Actions
# =============================================================================

def toggle_kill_switch(
    db: Session,
    enabled: bool,
    reason: str,
    triggered_by: str
) -> Dict[str, Any]:
    """
    Toggle the notification kill switch.
    
    Args:
        db: Database session
        enabled: True to engage, False to disengage
        reason: Reason for the action
        triggered_by: Admin user ID
    
    Returns:
        Updated kill switch status
    """
    kill_switch = get_kill_switch()
    
    if enabled:
        kill_switch.engage(reason, triggered_by)
    else:
        kill_switch.disengage(triggered_by)
    
    return kill_switch.get_status()


def mark_notification_status(
    db: Session,
    notification_id: str,
    status: str,
    error_message: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Manually update notification status (for admin overrides).
    
    Args:
        db: Database session
        notification_id: Notification event ID
        status: New status (pending, sent, delivered, read, dismissed, failed)
        error_message: Optional error message for failed status
    
    Returns:
        Updated notification dict or None if not found
    """
    notification = db.query(NotificationEvent).filter(
        NotificationEvent.id == notification_id
    ).first()
    
    if not notification:
        return None
    
    notification.status = status
    
    if status == 'delivered':
        notification.mark_delivered()
    elif status == 'read':
        notification.mark_read()
    elif status == 'dismissed':
        notification.mark_dismissed()
    elif status == 'failed' and error_message:
        notification.mark_failed(error_message)
    
    db.commit()
    
    return notification.to_dict()


def get_user_notification_summary(
    db: Session,
    user_id: str
) -> Dict[str, Any]:
    """
    Get notification summary for a specific user.

    Args:
        db: Database session
        user_id: User ID

    Returns:
        User notification summary
    """
    stats = get_notification_stats(db, period_hours=24 * 30, user_id=user_id)
    recent = get_recent_notifications(db, limit=10, user_id=user_id)

    # Get user preferences
    prefs = db.query(UserPreferences).filter(
        UserPreferences.user_id == user_id
    ).first()

    return {
        "user_id": user_id,
        "stats": stats.to_dict(),
        "recent_notifications": recent,
        "preferences": prefs.to_dict() if prefs else None,
        "generated_at": datetime.utcnow().isoformat()
    }


# =============================================================================
# Telemetry Dashboard (S20-P4)
# =============================================================================

def get_telemetry_counters_db(db: Session, period_hours: int = 24) -> Dict[str, Any]:
    """
    Get telemetry counters from database for a given period.

    Args:
        db: Database session
        period_hours: Time period to analyze (default 24 hours)

    Returns:
        Dictionary with telemetry counts
    """
    since = datetime.utcnow() - timedelta(hours=period_hours)

    # Count receipts by status
    detected = db.query(NotificationReceipt).filter(
        NotificationReceipt.detected_at >= since
    ).count()

    eligible = db.query(NotificationReceipt).filter(
        NotificationReceipt.eligible_at >= since
    ).count()

    sent = db.query(NotificationReceipt).filter(
        NotificationReceipt.sent_at >= since
    ).count()

    suppressed = db.query(NotificationReceipt).filter(
        NotificationReceipt.status == 'suppressed',
        NotificationReceipt.updated_at >= since
    ).count()

    return {
        "detected": detected,
        "eligible": eligible,
        "sent": sent,
        "suppressed": suppressed,
        "period_hours": period_hours
    }


def get_suppression_breakdown(db: Session, period_hours: int = 24) -> Dict[str, Any]:
    """
    Get breakdown of suppression reasons.

    Args:
        db: Database session
        period_hours: Time period to analyze (default 24 hours)

    Returns:
        Dictionary with suppression breakdown
    """
    since = datetime.utcnow() - timedelta(hours=period_hours)

    # Query suppressed receipts grouped by suppression reason
    results = db.query(
        NotificationReceipt.suppression_reason,
        func.count().label('count')
    ).filter(
        NotificationReceipt.status == 'suppressed',
        NotificationReceipt.updated_at >= since
    ).group_by(
        NotificationReceipt.suppression_reason
    ).all()

    breakdown = {}
    for reason, count in results:
        # Categorize the reason
        if reason:
            if 'cooldown' in reason.lower():
                category = 'suppressed_cooldown'
            elif 'daily cap' in reason.lower() or 'cap reached' in reason.lower():
                category = 'suppressed_daily_cap'
            elif 'quiet hours' in reason.lower():
                category = 'suppressed_quiet_hours'
            elif 'constraint' in reason.lower() or 'rule' in reason.lower():
                category = 'suppressed_constraints'
            elif 'beta' in reason.lower() or 'kill switch' in reason.lower():
                category = 'suppressed_beta_gate'
            else:
                category = 'suppressed_other'
        else:
            category = 'suppressed_other'

        if category not in breakdown:
            breakdown[category] = 0
        breakdown[category] += count

    # Ensure all categories exist
    for category in ['suppressed_cooldown', 'suppressed_daily_cap', 'suppressed_quiet_hours',
                     'suppressed_constraints', 'suppressed_beta_gate', 'suppressed_other']:
        if category not in breakdown:
            breakdown[category] = 0

    return {
        "breakdown": breakdown,
        "total_suppressed": sum(breakdown.values()),
        "period_hours": period_hours
    }


def get_daily_telemetry_summary(db: Session, days: int = 7) -> List[Dict[str, Any]]:
    """
    Get daily telemetry summary for the past N days.

    Args:
        db: Database session
        days: Number of days to analyze

    Returns:
        List of daily telemetry summaries
    """
    since = datetime.utcnow() - timedelta(days=days)

    # Query daily counts
    results = db.query(
        func.strftime('%Y-%m-%d', NotificationReceipt.created_at).label('date'),
        func.count().label('total'),
        func.sum(func.case([(NotificationReceipt.status == 'sent', 1)], else_=0)).label('sent'),
        func.sum(func.case([(NotificationReceipt.status == 'suppressed', 1)], else_=0)).label('suppressed'),
        func.sum(func.case([(NotificationReceipt.status == 'eligible', 1)], else_=0)).label('eligible'),
        func.sum(func.case([(NotificationReceipt.status == 'detected', 1)], else_=0)).label('detected')
    ).filter(
        NotificationReceipt.created_at >= since
    ).group_by(
        func.strftime('%Y-%m-%d', NotificationReceipt.created_at)
    ).order_by('date').all()

    daily_summary = []
    for row in results:
        daily_summary.append({
            "date": row.date,
            "total": row.total or 0,
            "sent": row.sent or 0,
            "suppressed": row.suppressed or 0,
            "eligible": row.eligible or 0,
            "detected": row.detected or 0,
            "delivery_rate": round((row.sent or 0) / (row.total or 1) * 100, 2)
        })

    return daily_summary


def get_telemetry_dashboard(db: Session) -> Dict[str, Any]:
    """
    Get complete telemetry dashboard data.

    Args:
        db: Database session

    Returns:
        Dictionary with all telemetry data
    """
    # Get in-memory counters (real-time)
    memory_counters = get_telemetry_counters().to_dict()

    # Get database counters (past 24h)
    db_counters_24h = get_telemetry_counters_db(db, period_hours=24)

    # Get suppression breakdown
    suppression_breakdown = get_suppression_breakdown(db, period_hours=24)

    # Get daily summary (past 7 days)
    daily_summary = get_daily_telemetry_summary(db, days=7)

    # Get recent receipts
    recent_receipts = db.query(NotificationReceipt).order_by(
        NotificationReceipt.created_at.desc()
    ).limit(50).all()

    return {
        "real_time_counters": memory_counters,
        "db_counters_24h": db_counters_24h,
        "suppression_breakdown": suppression_breakdown,
        "daily_summary": daily_summary,
        "recent_receipts": [r.to_dict() for r in recent_receipts],
        "generated_at": datetime.utcnow().isoformat()
    }
