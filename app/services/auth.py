"""
Authentication service for DNA Bet Engine.
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.models import User, get_session

# JWT Configuration
SECRET_KEY = "your-secret-key-change-in-production"  # TODO: Move to env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_user_by_email(email: str, db: Optional[Session] = None) -> Optional[User]:
    """Get user by email."""
    if db is None:
        db = get_session()
    return db.query(User).filter(User.email == email.lower()).first()


def get_user_by_id(user_id: str, db: Optional[Session] = None) -> Optional[User]:
    """Get user by ID."""
    if db is None:
        db = get_session()
    return db.query(User).filter(User.id == user_id).first()


def register_user(email: str, password: str, name: str, tier: str = "GOOD") -> Tuple[Optional[User], Optional[str]]:
    """
    Register a new user.
    
    Returns:
        (User, None) on success
        (None, error_message) on failure
    """
    db = get_session()
    
    # Check if email exists
    if get_user_by_email(email, db):
        return None, "Email already registered"
    
    # Validate password
    if len(password) < 8:
        return None, "Password must be at least 8 characters"
    
    # Create user
    user = User(
        email=email.lower(),
        password_hash=get_password_hash(password),
        name=name,
        tier=tier
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user, None


def authenticate_user(email: str, password: str) -> Tuple[Optional[User], Optional[str]]:
    """
    Authenticate user with email/password.
    
    Returns:
        (User, None) on success
        (None, error_message) on failure
    """
    db = get_session()
    
    user = get_user_by_email(email, db)
    if not user:
        return None, "Invalid email or password"
    
    if not verify_password(password, user.password_hash):
        return None, "Invalid email or password"
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    return user, None


def get_current_user_from_token(token: str) -> Optional[User]:
    """Get user from JWT token."""
    payload = decode_token(token)
    if not payload:
        return None
    
    user_id = payload.get("sub")
    if not user_id:
        return None
    
    return get_user_by_id(user_id)


def update_user_tier(user_id: str, tier: str) -> bool:
    """Update user tier (for upgrades)."""
    db = get_session()
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        return False
    
    user.tier = tier
    db.commit()
    return True
