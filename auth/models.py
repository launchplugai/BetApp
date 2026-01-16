# auth/models.py
"""
User and Session models for authentication.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional
import uuid


@dataclass
class User:
    """
    User account model.

    Attributes:
        id: Unique user ID (UUID)
        email: User's email (unique, used for login)
        password_hash: Bcrypt-hashed password
        tier: User's subscription tier (GOOD, BETTER, BEST)
        created_at: Account creation timestamp
        updated_at: Last update timestamp
        stripe_customer_id: Stripe customer ID (for billing)
        stripe_subscription_id: Active Stripe subscription ID
        tier_updated_at: When tier was last changed
    """
    id: str
    email: str
    password_hash: str
    tier: str = "GOOD"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    tier_updated_at: Optional[datetime] = None

    @classmethod
    def new(cls, email: str, password_hash: str, tier: str = "GOOD") -> User:
        """Create a new user with generated ID."""
        now = datetime.utcnow()
        return cls(
            id=str(uuid.uuid4()),
            email=email.lower().strip(),
            password_hash=password_hash,
            tier=tier.upper(),
            created_at=now,
            updated_at=now,
            stripe_customer_id=None,
            stripe_subscription_id=None,
            tier_updated_at=None,
        )

    @property
    def has_active_subscription(self) -> bool:
        """Check if user has an active Stripe subscription."""
        return bool(self.stripe_subscription_id)

    def to_dict(self) -> dict:
        """Convert to dictionary (excludes password_hash for safety)."""
        return {
            "id": self.id,
            "email": self.email,
            "tier": self.tier,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "has_subscription": self.has_active_subscription,
        }


@dataclass
class Session:
    """
    User session model.

    Attributes:
        id: Unique session ID (used as cookie value)
        user_id: Associated user ID
        created_at: Session creation timestamp
        expires_at: Session expiration timestamp
        ip_address: Client IP (optional, for audit)
        user_agent: Client user agent (optional, for audit)
    """
    id: str
    user_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(default_factory=lambda: datetime.utcnow() + timedelta(days=7))
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    @classmethod
    def new(
        cls,
        user_id: str,
        duration_days: int = 7,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Session:
        """Create a new session with generated ID."""
        now = datetime.utcnow()
        return cls(
            id=str(uuid.uuid4()),
            user_id=user_id,
            created_at=now,
            expires_at=now + timedelta(days=duration_days),
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @property
    def is_valid(self) -> bool:
        """Check if session is still valid (not expired)."""
        return datetime.utcnow() < self.expires_at

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
        }
