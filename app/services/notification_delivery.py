"""
Notification Delivery Service for S20.
Handles sending notifications through multiple channels with batch processing support.
"""

import logging
import json
import hashlib
import threading
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from queue import Queue, Empty
import time

from app.config import load_config
from app.services.notification_guardrails import get_notification_guardrails, GuardrailResult

logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    """Supported notification channels."""
    IN_APP = "in_app"
    WEBHOOK = "webhook"
    EMAIL = "email"  # Future expansion
    PUSH = "push"    # Future expansion


class NotificationStatus(str, Enum):
    """Notification delivery status."""
    PENDING = "pending"
    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"
    BLOCKED = "blocked"
    DELIVERED = "delivered"
    READ = "read"


@dataclass
class NotificationPayload:
    """Standardized notification payload."""
    notification_id: str
    user_id: str
    notification_type: str  # opportunity_alert, system_alert, constraint_violation
    title: str
    body: str
    data: Dict[str, Any]
    priority: str  # low, normal, high, urgent
    channels: List[NotificationChannel]
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    def compute_content_hash(self) -> str:
        """Compute hash for duplicate detection."""
        content = f"{self.user_id}:{self.notification_type}:{self.title}:{json.dumps(self.data, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()


@dataclass
class DeliveryResult:
    """Result of a notification delivery attempt."""
    notification_id: str
    channel: NotificationChannel
    status: NotificationStatus
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    error_message: Optional[str]
    metadata: Dict[str, Any]


class NotificationDelivery:
    """
    Notification Delivery Service.
    
    Features:
    - Multi-channel delivery (in-app, webhook)
    - Batch processing queue
    - Delivery tracking and receipts
    - Integration with guardrails
    - Async processing support
    """
    
    def __init__(self, max_queue_size: int = 1000, batch_size: int = 10):
        self.config = load_config(fail_fast=False)
        self.guardrails = get_notification_guardrails()
        
        # Queue for batch processing
        self._queue: Queue = Queue(maxsize=max_queue_size)
        self._batch_size = batch_size
        
        # Delivery tracking
        self._delivery_log: Dict[str, List[DeliveryResult]] = {}
        self._pending_notifications: Dict[str, NotificationPayload] = {}
        
        # Channel handlers
        self._channel_handlers: Dict[NotificationChannel, Callable] = {
            NotificationChannel.IN_APP: self._send_in_app,
            NotificationChannel.WEBHOOK: self._send_webhook,
        }
        
        # Webhook configuration (would be loaded from config)
        self._webhook_url: Optional[str] = None
        self._webhook_secret: Optional[str] = None
        
        # Processing state
        self._processing = False
        self._processor_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        logger.info("NotificationDelivery service initialized")
    
    # =========================================================================
    # Public API
    # =========================================================================
    
    def send_notification(
        self,
        user_id: str,
        notification_type: str,
        title: str,
        body: str,
        data: Dict[str, Any],
        channels: Optional[List[NotificationChannel]] = None,
        priority: str = "normal",
        game_id: Optional[str] = None,
        expires_in_minutes: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send a notification through specified channels.
        
        Args:
            user_id: Target user
            notification_type: Type of notification (opportunity_alert, etc.)
            title: Notification title
            body: Notification body
            data: Additional data payload
            channels: List of channels to send through (default: [IN_APP])
            priority: Priority level (low, normal, high, urgent)
            game_id: Associated game ID for cooldown tracking
            expires_in_minutes: Optional expiration time
            
        Returns:
            Dict with notification_id, status, and delivery details
        """
        # Check if notifications are enabled
        if not self.config.notifications_enabled:
            return {
                "notification_id": None,
                "status": "blocked",
                "reason": "Notifications disabled via feature flag",
                "deliveries": []
            }
        
        # Check kill switch
        if self.config.notifications_kill_switch:
            return {
                "notification_id": None,
                "status": "blocked",
                "reason": "Kill switch active",
                "deliveries": []
            }
        
        # Generate notification ID
        notification_id = self._generate_notification_id(user_id, notification_type)
        
        # Default channels
        if channels is None:
            channels = [NotificationChannel.IN_APP]
        
        # Build payload
        payload = NotificationPayload(
            notification_id=notification_id,
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
            data=data,
            priority=priority,
            channels=channels,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=expires_in_minutes) if expires_in_minutes else None
        )
        
        # Check guardrails
        content_hash = payload.compute_content_hash()
        guardrail_result = self.guardrails.can_notify(
            user_id=user_id,
            game_id=game_id or "unknown",
            opportunity_type=notification_type,
            content_hash=content_hash
        )
        
        if not guardrail_result.allowed:
            return {
                "notification_id": notification_id,
                "status": "blocked",
                "reason": guardrail_result.reason,
                "remaining_today": guardrail_result.remaining_today,
                "deliveries": []
            }
        
        # Queue for processing
        with self._lock:
            self._pending_notifications[notification_id] = payload
        
        self._queue.put(payload)
        
        # Start processor if not running
        self._ensure_processor_running()
        
        return {
            "notification_id": notification_id,
            "status": "queued",
            "channels": [c.value for c in channels],
            "estimated_delivery": "async",
            "deliveries": []
        }
    
    def track_delivery(
        self,
        notification_id: str,
        channel: NotificationChannel,
        status: NotificationStatus,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DeliveryResult:
        """
        Track a delivery attempt result.
        
        Args:
            notification_id: The notification ID
            channel: Channel used
            status: Delivery status
            error_message: Error message if failed
            metadata: Additional metadata
            
        Returns:
            DeliveryResult record
        """
        result = DeliveryResult(
            notification_id=notification_id,
            channel=channel,
            status=status,
            sent_at=datetime.utcnow() if status in [NotificationStatus.SENT, NotificationStatus.DELIVERED] else None,
            delivered_at=datetime.utcnow() if status == NotificationStatus.DELIVERED else None,
            error_message=error_message,
            metadata=metadata or {}
        )
        
        with self._lock:
            if notification_id not in self._delivery_log:
                self._delivery_log[notification_id] = []
            self._delivery_log[notification_id].append(result)
        
        # Log based on status
        if status == NotificationStatus.FAILED:
            logger.error(f"Delivery failed: {notification_id} on {channel}: {error_message}")
        elif status == NotificationStatus.DELIVERED:
            logger.debug(f"Delivered: {notification_id} on {channel}")
        
        return result
    
    def get_delivery_status(self, notification_id: str) -> Dict[str, Any]:
        """
        Get delivery status for a notification.
        
        Args:
            notification_id: The notification ID
            
        Returns:
            Status dict with delivery details
        """
        with self._lock:
            payload = self._pending_notifications.get(notification_id)
            deliveries = self._delivery_log.get(notification_id, [])
        
        if not payload and not deliveries:
            return {
                "notification_id": notification_id,
                "found": False,
                "status": "unknown"
            }
        
        return {
            "notification_id": notification_id,
            "found": True,
            "notification_type": payload.notification_type if payload else None,
            "channels_requested": [c.value for c in payload.channels] if payload else [],
            "created_at": payload.created_at.isoformat() if payload else None,
            "deliveries": [
                {
                    "channel": d.channel.value,
                    "status": d.status.value,
                    "sent_at": d.sent_at.isoformat() if d.sent_at else None,
                    "error": d.error_message
                }
                for d in deliveries
            ]
        }
    
    def get_delivery_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get delivery statistics.
        
        Args:
            user_id: Optional user filter
            
        Returns:
            Statistics dict
        """
        with self._lock:
            total_notifications = len(self._delivery_log)
            
            channel_stats: Dict[str, Dict[str, int]] = {}
            status_counts: Dict[str, int] = {}
            
            for deliveries in self._delivery_log.values():
                for d in deliveries:
                    # Channel stats
                    ch = d.channel.value
                    if ch not in channel_stats:
                        channel_stats[ch] = {"sent": 0, "failed": 0}
                    
                    if d.status == NotificationStatus.DELIVERED:
                        channel_stats[ch]["sent"] += 1
                    elif d.status == NotificationStatus.FAILED:
                        channel_stats[ch]["failed"] += 1
                    
                    # Status counts
                    status_key = d.status.value
                    status_counts[status_key] = status_counts.get(status_key, 0) + 1
        
        return {
            "total_notifications": total_notifications,
            "channel_breakdown": channel_stats,
            "status_counts": status_counts,
            "queue_size": self._queue.qsize(),
            "processor_running": self._processing
        }
    
    def process_queue_sync(self, max_items: Optional[int] = None) -> int:
        """
        Process queued notifications synchronously.
        
        Args:
            max_items: Maximum items to process (None for all)
            
        Returns:
            Number of items processed
        """
        processed = 0
        
        while True:
            if max_items is not None and processed >= max_items:
                break
            
            try:
                payload = self._queue.get(timeout=0.1)
            except Empty:
                break
            
            self._process_notification(payload)
            processed += 1
        
        return processed
    
    def start_batch_processor(self):
        """Start the background batch processor thread."""
        if self._processing:
            return
        
        self._processing = True
        self._processor_thread = threading.Thread(target=self._batch_processor_loop, daemon=True)
        self._processor_thread.start()
        logger.info("Notification batch processor started")
    
    def stop_batch_processor(self):
        """Stop the background batch processor."""
        self._processing = False
        if self._processor_thread:
            self._processor_thread.join(timeout=5.0)
        logger.info("Notification batch processor stopped")
    
    def configure_webhook(self, url: str, secret: Optional[str] = None):
        """Configure webhook endpoint."""
        self._webhook_url = url
        self._webhook_secret = secret
        logger.info(f"Webhook configured: {url}")
    
    # =========================================================================
    # Private Methods
    # =========================================================================
    
    def _generate_notification_id(self, user_id: str, notification_type: str) -> str:
        """Generate a unique notification ID."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        base = f"{user_id}:{notification_type}:{timestamp}"
        return hashlib.sha256(base.encode()).hexdigest()[:32]
    
    def _ensure_processor_running(self):
        """Ensure the batch processor is running."""
        if not self._processing:
            self.start_batch_processor()
    
    def _batch_processor_loop(self):
        """Background loop for batch processing."""
        while self._processing:
            try:
                batch: List[NotificationPayload] = []
                
                # Collect batch
                for _ in range(self._batch_size):
                    try:
                        item = self._queue.get(timeout=0.5)
                        batch.append(item)
                    except Empty:
                        break
                
                # Process batch
                for payload in batch:
                    self._process_notification(payload)
                
                # Small delay between batches
                if not batch:
                    time.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Error in batch processor: {e}")
                time.sleep(1.0)
    
    def _process_notification(self, payload: NotificationPayload):
        """Process a single notification through all channels."""
        for channel in payload.channels:
            handler = self._channel_handlers.get(channel)
            
            if not handler:
                self.track_delivery(
                    payload.notification_id,
                    channel,
                    NotificationStatus.FAILED,
                    error_message=f"No handler for channel: {channel}"
                )
                continue
            
            try:
                result = handler(payload)
                
                if result.get("success"):
                    self.track_delivery(
                        payload.notification_id,
                        channel,
                        NotificationStatus.DELIVERED,
                        metadata=result.get("metadata", {})
                    )
                else:
                    self.track_delivery(
                        payload.notification_id,
                        channel,
                        NotificationStatus.FAILED,
                        error_message=result.get("error", "Unknown error"),
                        metadata=result.get("metadata", {})
                    )
                
            except Exception as e:
                logger.exception(f"Error sending notification on {channel}")
                self.track_delivery(
                    payload.notification_id,
                    channel,
                    NotificationStatus.FAILED,
                    error_message=str(e)
                )
        
        # Record notification with guardrails
        game_id = payload.data.get("game_id", "unknown")
        self.guardrails.record_notification(
            user_id=payload.user_id,
            game_id=game_id,
            notification_id=payload.notification_id
        )
    
    def _send_in_app(self, payload: NotificationPayload) -> Dict[str, Any]:
        """
        Send notification through in-app channel.
        Stores in database for retrieval by frontend.
        """
        try:
            # In a real implementation, this would save to a notifications table
            # For now, we simulate success
            
            # TODO: Implement actual database storage
            # from app.models.notification_event import NotificationEvent
            # event = NotificationEvent(...)
            # session.add(event)
            # session.commit()
            
            return {
                "success": True,
                "metadata": {
                    "channel": "in_app",
                    "stored_at": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "metadata": {}
            }
    
    def _send_webhook(self, payload: NotificationPayload) -> Dict[str, Any]:
        """
        Send notification through webhook.
        """
        if not self._webhook_url:
            return {
                "success": False,
                "error": "Webhook not configured",
                "metadata": {}
            }
        
        try:
            import requests
            
            headers = {
                "Content-Type": "application/json"
            }
            
            if self._webhook_secret:
                headers["X-Webhook-Signature"] = self._sign_payload(payload)
            
            webhook_payload = {
                "notification_id": payload.notification_id,
                "user_id": payload.user_id,
                "type": payload.notification_type,
                "title": payload.title,
                "body": payload.body,
                "data": payload.data,
                "priority": payload.priority,
                "timestamp": payload.created_at.isoformat()
            }
            
            # In production, this would make an actual HTTP request
            # response = requests.post(
            #     self._webhook_url,
            #     json=webhook_payload,
            #     headers=headers,
            #     timeout=10
            # )
            # response.raise_for_status()
            
            # Simulated success for now
            return {
                "success": True,
                "metadata": {
                    "channel": "webhook",
                    "url": self._webhook_url,
                    "sent_at": datetime.utcnow().isoformat()
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "metadata": {}
            }
    
    def _sign_payload(self, payload: NotificationPayload) -> str:
        """Sign payload for webhook security."""
        if not self._webhook_secret:
            return ""
        
        import hmac
        
        message = f"{payload.notification_id}:{payload.user_id}:{payload.created_at.isoformat()}"
        signature = hmac.new(
            self._webhook_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature


# Singleton instance
_delivery_instance: Optional[NotificationDelivery] = None


def get_notification_delivery() -> NotificationDelivery:
    """Get or create the singleton NotificationDelivery instance."""
    global _delivery_instance
    if _delivery_instance is None:
        _delivery_instance = NotificationDelivery()
    return _delivery_instance


# Convenience functions
def send_notification(
    user_id: str,
    notification_type: str,
    title: str,
    body: str,
    data: Dict[str, Any],
    **kwargs
) -> Dict[str, Any]:
    """Convenience function to send a notification."""
    return get_notification_delivery().send_notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        body=body,
        data=data,
        **kwargs
    )


def track_delivery(
    notification_id: str,
    channel: NotificationChannel,
    status: NotificationStatus,
    **kwargs
) -> DeliveryResult:
    """Convenience function to track a delivery."""
    return get_notification_delivery().track_delivery(
        notification_id=notification_id,
        channel=channel,
        status=status,
        **kwargs
    )
