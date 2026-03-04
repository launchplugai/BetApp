"""
Protocol Observer Service for S20.
Watches for opportunities and filters them through user DNA constraints.
Emits EligibleOpportunity events when opportunities match user criteria.
"""

import logging
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta

from app.models import get_session
from app.models.user_preferences import UserPreferences
from app.models.eligible_opportunity import EligibleOpportunity
from app.models.user_dna_snapshot import UserDnaSnapshot
from app.models.notification_receipt import NotificationReceipt, get_telemetry_counters
from app.services.notification_types import (
    OpportunityStatus, RawOpportunity, OpportunityResult
)
from app.services.notification_rules import NotificationRulesEngine
from app.services.notification_guardrails import NotificationGuardrails
from app.config import is_beta_user, load_config

logger = logging.getLogger(__name__)


class ProtocolObserver:
    """
    Protocol Observer watches for betting opportunities and filters them
    through user DNA constraints to find eligible matches.
    """
    
    def __init__(self):
        self.rules_engine = NotificationRulesEngine()
        self.guardrails = NotificationGuardrails()
        self._handlers: List[Callable[[EligibleOpportunity], None]] = []
        self._telemetry = get_telemetry_counters()
    
    def watch_protocol(self, protocol_id: str, opportunities: List[RawOpportunity]) -> List[OpportunityResult]:
        """
        Watch a protocol for opportunities and process them.
        
        Args:
            protocol_id: The protocol being watched (e.g., "nba_ml_v1")
            opportunities: List of raw opportunities from the protocol
            
        Returns:
            List of OpportunityResult for each processed opportunity
        """
        results = []
        
        for opp in opportunities:
            # Log detection counter
            self._telemetry.detected += 1
            # Check confidence threshold
            if not self.check_confidence_threshold(opp):
                results.append(OpportunityResult(
                    success=False,
                    reason=f"Confidence {opp.confidence_score} below threshold"
                ))
                continue
            
            # Check misalignment if available
            if not self.check_misalignment(opp):
                results.append(OpportunityResult(
                    success=False,
                    reason="Misalignment check failed"
                ))
                continue
            
            # Process for all users with matching preferences
            user_results = self._process_for_users(opp)
            results.extend(user_results)
        
        return results
    
    def check_confidence_threshold(self, opportunity: RawOpportunity, 
                                    min_confidence: float = 70.0) -> bool:
        """
        Check if opportunity meets minimum confidence threshold.
        
        Args:
            opportunity: The opportunity to check
            min_confidence: Minimum confidence score (0-100)
            
        Returns:
            True if confidence meets threshold
        """
        return opportunity.confidence_score >= min_confidence
    
    def check_misalignment(self, opportunity: RawOpportunity,
                           max_misalignment: float = 50.0) -> bool:
        """
        Check if opportunity passes misalignment check.
        High misalignment may indicate stale odds or market movement.
        
        Args:
            opportunity: The opportunity to check
            max_misalignment: Maximum allowed misalignment score
            
        Returns:
            True if misalignment is acceptable
        """
        # If no misalignment data, assume it's ok
        if opportunity.edge_percent is None:
            return True
        
        # Calculate misalignment score (inverse of edge for now)
        # This can be made more sophisticated based on actual market data
        misalignment = abs(opportunity.edge_percent) if opportunity.edge_percent else 0
        
        return misalignment <= max_misalignment
    
    def _process_for_users(self, opportunity: RawOpportunity) -> List[OpportunityResult]:
        """Process an opportunity for all users with matching preferences."""
        results = []
        session = get_session()

        # Load config for beta user checking (S20-P2)
        config = load_config(fail_fast=False)

        try:
            # Get all users with notification-enabled preferences
            all_prefs = session.query(UserPreferences).all()

            for prefs in all_prefs:
                notification_rules = prefs.get_notification_rules()

                # Skip if notifications disabled
                if not notification_rules.get("enabled", True):
                    continue

                # Check beta gate status (S20-P2)
                beta_gate_pass = is_beta_user(prefs.user_id, config.notifications_beta_user_ids)

                # Log beta gate status for opportunity evaluation
                logger.debug(
                    "OPPORTUNITY_BETA_GATE_CHECK",
                    extra={
                        "user_id": prefs.user_id,
                        "game_id": opportunity.game_id,
                        "beta_gate_pass": beta_gate_pass,
                        "beta_allowlist_empty": len(config.notifications_beta_user_ids) == 0
                    }
                )

                # Create receipt at detection stage
                receipt = NotificationReceipt.create_for_detection(
                    user_id=prefs.user_id,
                    confidence=opportunity.confidence_score,
                    reason_codes=["opportunity_detected"],
                    weight_tier=self._calculate_weight_tier(opportunity.confidence_score),
                    metadata={
                        "protocol_id": opportunity.protocol_id,
                        "game_id": opportunity.game_id,
                        "bet_type": opportunity.bet_type,
                        "selection": opportunity.selection
                    }
                )
                session.add(receipt)
                session.flush()  # Get receipt ID

                # Check if opportunity matches user's notification rules
                match_result = self.rules_engine.matches_rules(
                    opportunity,
                    notification_rules.get("opportunity_alerts", {})
                )

                if not match_result.matches:
                    receipt.mark_suppressed(f"Rule mismatch: {match_result.reason}")
                    self._telemetry.increment_suppressed(f"constraints: {match_result.reason}")
                    results.append(OpportunityResult(
                        success=False,
                        reason=f"User {prefs.user_id}: {match_result.reason}"
                    ))
                    continue

                # Mark as eligible after constraints pass
                receipt.mark_eligible()
                receipt.constraints_applied = match_result.matched_criteria
                self._telemetry.eligible_after_constraints += 1

                # Check guardrails (includes beta gate check)
                guardrail_check = self.guardrails.can_notify(
                    user_id=prefs.user_id,
                    game_id=opportunity.game_id,
                    opportunity_type="opportunity_alert"
                )

                if not guardrail_check.allowed:
                    receipt.mark_suppressed(guardrail_check.reason)
                    self._telemetry.increment_suppressed(guardrail_check.reason)
                    results.append(OpportunityResult(
                        success=False,
                        passed_guardrails=False,
                        guardrail_reason=guardrail_check.reason,
                        reason=f"Guardrails blocked for user {prefs.user_id}"
                    ))
                    continue
                
                # Create eligible opportunity record
                eligible_opp = self._create_eligible_opportunity(
                    session, prefs, opportunity, match_result.matched_criteria
                )
                
                if eligible_opp:
                    # Link receipt to opportunity
                    receipt.opportunity_id = eligible_opp.id
                    
                    # Notify handlers
                    self._notify_handlers(eligible_opp)
                    
                    results.append(OpportunityResult(
                        success=True,
                        opportunity_id=eligible_opp.id,
                        reason=f"Created for user {prefs.user_id}"
                    ))
                else:
                    receipt.mark_suppressed("Failed to create eligible opportunity")
                    self._telemetry.increment_suppressed("other")
                    results.append(OpportunityResult(
                        success=False,
                        reason="Failed to create eligible opportunity"
                    ))
            
            session.commit()
        
        except Exception as e:
            session.rollback()
            logger.error(f"Error processing opportunities: {e}")
        finally:
            session.close()
        
        return results
    
    def _calculate_weight_tier(self, confidence: float) -> str:
        """Calculate weight tier based on confidence score."""
        if confidence >= 85:
            return "A"
        elif confidence >= 75:
            return "B"
        elif confidence >= 65:
            return "C"
        else:
            return "D"
    
    def _create_eligible_opportunity(self, session, prefs: UserPreferences,
                                     opportunity: RawOpportunity,
                                     matched_criteria: List[str]) -> Optional[EligibleOpportunity]:
        """Create an EligibleOpportunity record in the database."""
        try:
            # Create DNA snapshot
            snapshot = UserDnaSnapshot(
                user_id=prefs.user_id,
                preferences=prefs.to_dict()
            )
            session.add(snapshot)
            session.flush()  # Get snapshot ID
            
            # Calculate expires time (default to event time or 1 hour)
            expires_at = opportunity.event_time
            
            eligible = EligibleOpportunity(
                user_id=prefs.user_id,
                protocol_id=opportunity.protocol_id,
                protocol_source=opportunity.protocol_source,
                game_id=opportunity.game_id,
                sport=opportunity.sport,
                league=opportunity.league,
                home_team=opportunity.home_team,
                away_team=opportunity.away_team,
                event_time=opportunity.event_time,
                bet_type=opportunity.bet_type,
                market=opportunity.market,
                selection=opportunity.selection,
                odds=opportunity.odds,
                odds_decimal=opportunity.odds_decimal,
                line=opportunity.line,
                confidence_score=opportunity.confidence_score,
                edge_percent=opportunity.edge_percent,
                misalignment_score=None,  # Could be calculated
                matched_criteria=matched_criteria,
                dna_snapshot_id=snapshot.id,
                expires_at=expires_at
            )
            
            session.add(eligible)
            session.commit()
            session.refresh(eligible)
            
            logger.info(
                "ELIGIBLE_OPPORTUNITY_CREATED",
                extra={
                    "opportunity_id": eligible.id,
                    "user_id": prefs.user_id,
                    "protocol": opportunity.protocol_id,
                    "game": opportunity.game_id,
                    "confidence": opportunity.confidence_score
                }
            )
            
            return eligible
            
        except Exception as e:
            session.rollback()
            logger.error(
                "ELIGIBLE_OPPORTUNITY_FAILED",
                extra={"error": str(e), "user_id": prefs.user_id}
            )
            return None
    
    def add_handler(self, handler: Callable[[EligibleOpportunity], None]):
        """Add a handler to be called when eligible opportunities are created."""
        self._handlers.append(handler)
    
    def _notify_handlers(self, opportunity: EligibleOpportunity):
        """Notify all registered handlers."""
        for handler in self._handlers:
            try:
                handler(opportunity)
            except Exception as e:
                logger.error(f"Handler error: {e}")
    
    def get_active_opportunities(self, user_id: str, 
                                  sport: Optional[str] = None) -> List[EligibleOpportunity]:
        """
        Get active eligible opportunities for a user.
        
        Args:
            user_id: The user to get opportunities for
            sport: Optional sport filter
            
        Returns:
            List of active EligibleOpportunity records
        """
        session = get_session()
        try:
            query = session.query(EligibleOpportunity).filter(
                EligibleOpportunity.user_id == user_id,
                EligibleOpportunity.status.in_(["active", "notified"]),
                EligibleOpportunity.expires_at > datetime.utcnow()
            )
            
            if sport:
                query = query.filter(EligibleOpportunity.sport == sport)
            
            return query.order_by(EligibleOpportunity.confidence_score.desc()).all()
        finally:
            session.close()
    
    def expire_old_opportunities(self) -> int:
        """
        Mark expired opportunities as expired.
        
        Returns:
            Number of opportunities marked as expired
        """
        session = get_session()
        try:
            expired = session.query(EligibleOpportunity).filter(
                EligibleOpportunity.status.in_(["active", "notified"]),
                EligibleOpportunity.expires_at <= datetime.utcnow()
            ).all()
            
            count = 0
            for opp in expired:
                opp.mark_expired()
                count += 1
            
            session.commit()
            
            if count > 0:
                logger.info(f"Expired {count} old opportunities")
            
            return count
        finally:
            session.close()


# Singleton instance for application use
_observer_instance: Optional[ProtocolObserver] = None


def get_protocol_observer() -> ProtocolObserver:
    """Get or create the singleton ProtocolObserver instance."""
    global _observer_instance
    if _observer_instance is None:
        _observer_instance = ProtocolObserver()
    return _observer_instance
