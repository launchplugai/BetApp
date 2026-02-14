"""
Notifications API router for S20.
Manages user notifications and notification preferences.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.services.auth import get_current_user_from_token
from app.models import get_session
from app.models.notification_event import NotificationEvent
from app.models.notification_preferences import NotificationPreferences
from app.models.eligible_opportunity import EligibleOpportunity
from app.services.notification_guardrails import get_notification_guardrails

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])
security = HTTPBearer()


# =============================================================================
# Pydantic Schemas
# =============================================================================

class NotificationItem(BaseModel):
    """Notification item in list response."""
    id: str
    type: str
    category: str
    priority: str
    title: str
    body: str
    data: Dict[str, Any]
    status: str
    sent_at: str
    read_at: Optional[str]
    opportunity_id: Optional[str]
    bet_id: Optional[str]


class NotificationListResponse(BaseModel):
    """Response for listing notifications."""
    notifications: List[NotificationItem]
    total: int
    unread_count: int
    page: int
    per_page: int


class OpportunityAlert(BaseModel):
    """Opportunity alert settings."""
    enabled: bool = True
    min_confidence: float = 70.0
    min_edge_percent: Optional[float] = 5.0
    sports: List[str] = []
    bet_types: List[str] = ["moneyline", "spread", "total", "prop"]
    odds_range: Dict[str, Optional[int]] = {"min": -300, "max": 500}
    max_notifications_per_day: int = 10
    cooldown_minutes: int = 60


class BetOutcomeSettings(BaseModel):
    """Bet outcome notification settings."""
    enabled: bool = True
    wins: bool = True
    losses: bool = True


class GameReminderSettings(BaseModel):
    """Game reminder notification settings."""
    enabled: bool = False
    before_minutes: int = 30


class QuietHoursSettings(BaseModel):
    """Quiet hours settings."""
    enabled: bool = True
    start: str = "22:00"
    end: str = "08:00"


class NotificationPreferencesResponse(BaseModel):
    """Response for notification preferences."""
    enabled: bool
    opportunity_alerts: OpportunityAlert
    bet_outcomes: BetOutcomeSettings
    game_reminders: GameReminderSettings
    quiet_hours: QuietHoursSettings


class NotificationPreferencesInput(BaseModel):
    """Input for updating notification preferences."""
    enabled: Optional[bool] = None
    opportunity_alerts: Optional[OpportunityAlert] = None
    bet_outcomes: Optional[BetOutcomeSettings] = None
    game_reminders: Optional[GameReminderSettings] = None
    quiet_hours: Optional[QuietHoursSettings] = None


class MarkReadResponse(BaseModel):
    """Response for marking notification as read."""
    success: bool
    notification_id: str


class DismissResponse(BaseModel):
    """Response for dismissing notification."""
    success: bool
    notification_id: str


# =============================================================================
# Routes
# =============================================================================

@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    status: Optional[str] = Query(None, description="Filter by status: sent, delivered, read, dismissed"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page")
):
    """
    List user's notifications with pagination.
    
    Query params:
        - status: Filter by status
        - page: Page number (default 1)
        - per_page: Items per page (default 20, max 100)
    
    Returns:
        {
            "notifications": [...],
            "total": 100,
            "unread_count": 5,
            "page": 1,
            "per_page": 20
        }
    """
    user = get_current_user_from_token(credentials.credentials)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    db = get_session()
    
    try:
        # Build query
        query = db.query(NotificationEvent).filter(
            NotificationEvent.user_id == user.id
        )
        
        if status:
            query = query.filter(NotificationEvent.status == status.lower())
        
        # Get total count
        total = query.count()
        
        # Get unread count
        unread_count = db.query(NotificationEvent).filter(
            NotificationEvent.user_id == user.id,
            NotificationEvent.status.in_(["sent", "delivered"])
        ).count()
        
        # Pagination
        offset = (page - 1) * per_page
        notifications = query.order_by(
            NotificationEvent.sent_at.desc()
        ).offset(offset).limit(per_page).all()
        
        # Map to response
        items = [
            NotificationItem(
                id=n.id,
                type=n.type,
                category=n.category,
                priority=n.priority,
                title=n.title,
                body=n.body,
                data=n.data or {},
                status=n.status,
                sent_at=n.sent_at.isoformat() if n.sent_at else "",
                read_at=n.read_at.isoformat() if n.read_at else None,
                opportunity_id=n.opportunity_id,
                bet_id=n.bet_id
            )
            for n in notifications
        ]
        
        return NotificationListResponse(
            notifications=items,
            total=total,
            unread_count=unread_count,
            page=page,
            per_page=per_page
        )
    
    finally:
        db.close()


@router.get("/preferences", response_model=NotificationPreferencesResponse)
async def get_notification_preferences(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get user's notification preferences."""
    from app.models.user_preferences import UserPreferences
    
    user = get_current_user_from_token(credentials.credentials)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    db = get_session()
    
    try:
        prefs = db.query(UserPreferences).filter_by(user_id=user.id).first()
        
        if not prefs:
            # Return defaults
            return NotificationPreferencesResponse(
                enabled=True,
                opportunity_alerts=OpportunityAlert(),
                bet_outcomes=BetOutcomeSettings(),
                game_reminders=GameReminderSettings(),
                quiet_hours=QuietHoursSettings()
            )
        
        rules = prefs.get_notification_rules()
        
        return NotificationPreferencesResponse(
            enabled=rules.get("enabled", True),
            opportunity_alerts=OpportunityAlert(
                **rules.get("opportunity_alerts", {})
            ),
            bet_outcomes=BetOutcomeSettings(
                **rules.get("bet_outcomes", {})
            ),
            game_reminders=GameReminderSettings(
                **rules.get("game_reminders", {})
            ),
            quiet_hours=QuietHoursSettings(
                **rules.get("quiet_hours", {})
            )
        )
    
    finally:
        db.close()


@router.post("/preferences", response_model=NotificationPreferencesResponse)
async def update_notification_preferences(
    input_data: NotificationPreferencesInput,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Update user's notification preferences."""
    from app.models.user_preferences import UserPreferences
    from app.services.notification_rules import NotificationRulesEngine
    
    user = get_current_user_from_token(credentials.credentials)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Validate input
    engine = NotificationRulesEngine()
    
    new_rules = {}
    
    if input_data.enabled is not None:
        new_rules["enabled"] = input_data.enabled
    
    if input_data.opportunity_alerts:
        alert_dict = input_data.opportunity_alerts.dict()
        is_valid, errors = engine.validate_notification_rules({
            "opportunity_alerts": alert_dict
        })
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid rules: {', '.join(errors)}")
        new_rules["opportunity_alerts"] = alert_dict
    
    if input_data.bet_outcomes:
        new_rules["bet_outcomes"] = input_data.bet_outcomes.dict()
    
    if input_data.game_reminders:
        new_rules["game_reminders"] = input_data.game_reminders.dict()
    
    if input_data.quiet_hours:
        new_rules["quiet_hours"] = input_data.quiet_hours.dict()
    
    db = get_session()
    
    try:
        prefs = db.query(UserPreferences).filter_by(user_id=user.id).first()
        
        if not prefs:
            # Create new preferences
            prefs = UserPreferences(
                user_id=user.id,
                notification_rules=new_rules
            )
            db.add(prefs)
        else:
            # Merge with existing rules
            existing = prefs.get_notification_rules()
            existing.update(new_rules)
            prefs.notification_rules = existing
            prefs.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(prefs)
        
        # Return updated preferences
        rules = prefs.get_notification_rules()
        
        return NotificationPreferencesResponse(
            enabled=rules.get("enabled", True),
            opportunity_alerts=OpportunityAlert(
                **rules.get("opportunity_alerts", {})
            ),
            bet_outcomes=BetOutcomeSettings(
                **rules.get("bet_outcomes", {})
            ),
            game_reminders=GameReminderSettings(
                **rules.get("game_reminders", {})
            ),
            quiet_hours=QuietHoursSettings(
                **rules.get("quiet_hours", {})
            )
        )
    
    finally:
        db.close()


@router.post("/{notification_id}/read", response_model=MarkReadResponse)
async def mark_notification_read(
    notification_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Mark a notification as read."""
    user = get_current_user_from_token(credentials.credentials)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    db = get_session()
    
    try:
        notification = db.query(NotificationEvent).filter(
            NotificationEvent.id == notification_id,
            NotificationEvent.user_id == user.id
        ).first()
        
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        notification.mark_read()
        db.commit()
        
        log.info(
            "NOTIFICATION_MARKED_READ",
            extra={"notification_id": notification_id, "user_id": user.id}
        )
        
        return MarkReadResponse(
            success=True,
            notification_id=notification_id
        )
    
    finally:
        db.close()


@router.delete("/{notification_id}", response_model=DismissResponse)
async def dismiss_notification(
    notification_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Dismiss (delete) a notification."""
    user = get_current_user_from_token(credentials.credentials)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    db = get_session()
    
    try:
        notification = db.query(NotificationEvent).filter(
            NotificationEvent.id == notification_id,
            NotificationEvent.user_id == user.id
        ).first()
        
        if not notification:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        notification.mark_dismissed()
        db.commit()
        
        log.info(
            "NOTIFICATION_DISMISSED",
            extra={"notification_id": notification_id, "user_id": user.id}
        )
        
        return DismissResponse(
            success=True,
            notification_id=notification_id
        )
    
    finally:
        db.close()


@router.get("/opportunities/active")
async def get_active_opportunities(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    sport: Optional[str] = Query(None, description="Filter by sport")
):
    """Get active eligible opportunities for the user."""
    from app.services.protocol_observer import get_protocol_observer
    
    user = get_current_user_from_token(credentials.credentials)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    observer = get_protocol_observer()
    opportunities = observer.get_active_opportunities(user.id, sport)
    
    return {
        "opportunities": [opp.to_dict() for opp in opportunities],
        "count": len(opportunities)
    }


@router.post("/opportunities/{opportunity_id}/dismiss")
async def dismiss_opportunity(
    opportunity_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Dismiss an eligible opportunity without betting on it."""
    user = get_current_user_from_token(credentials.credentials)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    db = get_session()
    
    try:
        opportunity = db.query(EligibleOpportunity).filter(
            EligibleOpportunity.id == opportunity_id,
            EligibleOpportunity.user_id == user.id
        ).first()
        
        if not opportunity:
            raise HTTPException(status_code=404, detail="Opportunity not found")
        
        opportunity.mark_dismissed()
        db.commit()
        
        log.info(
            "OPPORTUNITY_DISMISSED",
            extra={"opportunity_id": opportunity_id, "user_id": user.id}
        )
        
        return {
            "success": True,
            "opportunity_id": opportunity_id,
            "status": "rejected"
        }
    
    finally:
        db.close()
