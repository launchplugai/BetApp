"""
Authentication service for DNA Bet Engine.
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
import hashlib
import uuid

from app.models import User, RefreshToken, TokenBlacklist, get_session

# JWT Configuration
SECRET_KEY = "your-secret-key-change-in-production"  # TODO: Move to env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15  # Short-lived access tokens
REFRESH_TOKEN_EXPIRE_DAYS = 30    # Long-lived refresh tokens

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> Tuple[str, str]:
    """
    Create JWT access token with JTI for blacklist support.
    
    Returns:
        (token, jti) tuple
    """
    to_encode = data.copy()
    jti = str(uuid.uuid4())
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "jti": jti,
        "type": "access"
    })
    
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token, jti


def create_refresh_token(user_id: str, device_info: Optional[str] = None, ip_address: Optional[str] = None) -> str:
    """
    Create a refresh token and store it in database.
    
    Returns:
        Plain text refresh token (store securely!)
    """
    db = get_session()
    
    # Generate random token
    plain_token = uuid.uuid4().hex + uuid.uuid4().hex
    token_hash = hashlib.sha256(plain_token.encode()).hexdigest()
    
    # Store in database
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    refresh_token = RefreshToken(
        token_hash=token_hash,
        user_id=user_id,
        device_info=device_info,
        ip_address=ip_address,
        expires_at=expires_at
    )
    
    db.add(refresh_token)
    db.commit()
    
    return plain_token


def validate_refresh_token(plain_token: str) -> Optional[User]:
    """
    Validate a refresh token and return associated user.
    
    Returns None if token is invalid, expired, or revoked.
    """
    db = get_session()
    
    # Hash the token to look it up
    token_hash = hashlib.sha256(plain_token.encode()).hexdigest()
    
    # Find token in database
    rt = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.is_revoked == 0,
        RefreshToken.expires_at > datetime.utcnow()
    ).first()
    
    if not rt:
        return None
    
    # Update last used timestamp
    rt.last_used_at = datetime.utcnow()
    db.commit()
    
    # Return associated user
    return get_user_by_id(rt.user_id, db)


def revoke_refresh_token(plain_token: str) -> bool:
    """Revoke a refresh token (logout)."""
    db = get_session()
    
    token_hash = hashlib.sha256(plain_token.encode()).hexdigest()
    
    rt = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash
    ).first()
    
    if rt:
        rt.is_revoked = 1
        db.commit()
        return True
    
    return False


def revoke_all_user_refresh_tokens(user_id: str) -> int:
    """Revoke all refresh tokens for a user (logout all devices)."""
    db = get_session()
    
    tokens = db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.is_revoked == 0
    ).all()
    
    count = 0
    for rt in tokens:
        rt.is_revoked = 1
        count += 1
    
    db.commit()
    return count


def blacklist_access_token(token: str, reason: str = "logout") -> bool:
    """
    Blacklist an access token (for logout).
    
    Returns True if token was blacklisted, False if already expired/invalid.
    """
    try:
        # Decode without verification to get JTI and exp
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        
        jti = payload.get("jti")
        user_id = payload.get("sub")
        exp_timestamp = payload.get("exp")
        
        if not jti or not user_id or not exp_timestamp:
            return False
        
        # Check if already blacklisted
        db = get_session()
        existing = db.query(TokenBlacklist).filter(TokenBlacklist.token_jti == jti).first()
        if existing:
            return True
        
        # Add to blacklist
        expires_at = datetime.utcfromtimestamp(exp_timestamp)
        
        blacklist_entry = TokenBlacklist(
            token_jti=jti,
            user_id=user_id,
            expires_at=expires_at,
            reason=reason
        )
        
        db.add(blacklist_entry)
        db.commit()
        
        return True
        
    except JWTError:
        return False


def is_token_blacklisted(token: str) -> bool:
    """Check if an access token is blacklisted."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        jti = payload.get("jti")
        
        if not jti:
            return True  # Treat tokens without JTI as blacklisted
        
        db = get_session()
        existing = db.query(TokenBlacklist).filter(TokenBlacklist.token_jti == jti).first()
        
        return existing is not None
        
    except JWTError:
        return True


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


def register_user(email: str, password: str, name: str, tier: str = "GOOD", device_info: Optional[str] = None, ip_address: Optional[str] = None) -> Tuple[Optional[User], Optional[str], Optional[str], Optional[str]]:
    """
    Register a new user.
    
    Returns:
        (User, access_token, refresh_token, None) on success
        (None, None, None, error_message) on failure
    """
    db = get_session()
    
    # Check if email exists
    if get_user_by_email(email, db):
        return None, None, None, "Email already registered"
    
    # Validate password
    if len(password) < 8:
        return None, None, None, "Password must be at least 8 characters"
    
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
    
    # Create tokens
    access_token, _ = create_access_token({"sub": user.id})
    refresh_token = create_refresh_token(user.id, device_info, ip_address)
    
    return user, access_token, refresh_token, None


def authenticate_user(email: str, password: str, device_info: Optional[str] = None, ip_address: Optional[str] = None) -> Tuple[Optional[User], Optional[str], Optional[str], Optional[str]]:
    """
    Authenticate user with email/password.
    
    Returns:
        (User, access_token, refresh_token, None) on success
        (None, None, None, error_message) on failure
    """
    db = get_session()
    
    user = get_user_by_email(email, db)
    if not user:
        return None, None, None, "Invalid email or password"
    
    if not verify_password(password, user.password_hash):
        return None, None, None, "Invalid email or password"
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    # Create tokens
    access_token, _ = create_access_token({"sub": user.id})
    refresh_token = create_refresh_token(user.id, device_info, ip_address)
    
    return user, access_token, refresh_token, None


def get_current_user_from_token(token: str) -> Optional[User]:
    """
    Get user from JWT token.
    
    Validates token and checks blacklist.
    Returns None if token is invalid, expired, or blacklisted.
    """
    # Check if blacklisted first (fast check)
    if is_token_blacklisted(token):
        return None
    
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
