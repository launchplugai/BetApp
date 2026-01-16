# auth/password.py
"""
Secure password hashing using bcrypt.

Bcrypt is designed for password hashing with:
- Automatic salt generation
- Configurable work factor (cost)
- Resistance to rainbow tables
"""

from __future__ import annotations

import bcrypt
import logging

_logger = logging.getLogger(__name__)

# Work factor (cost) - higher = slower but more secure
# 12 is a good balance for 2024 hardware
BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Bcrypt hash string (includes salt)
    """
    if not password:
        raise ValueError("Password cannot be empty")

    # Encode to bytes and hash
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    hashed = bcrypt.hashpw(password_bytes, salt)

    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        password: Plain text password to verify
        password_hash: Stored bcrypt hash

    Returns:
        True if password matches, False otherwise
    """
    if not password or not password_hash:
        return False

    try:
        password_bytes = password.encode("utf-8")
        hash_bytes = password_hash.encode("utf-8")
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except Exception as e:
        _logger.warning(f"Password verification error: {e}")
        return False


def is_password_strong(password: str) -> tuple[bool, str]:
    """
    Check if a password meets minimum strength requirements.

    Requirements:
    - At least 8 characters
    - Contains at least one letter
    - Contains at least one digit

    Args:
        password: Password to check

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password:
        return False, "Password cannot be empty"

    if len(password) < 8:
        return False, "Password must be at least 8 characters"

    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)

    if not has_letter:
        return False, "Password must contain at least one letter"

    if not has_digit:
        return False, "Password must contain at least one digit"

    return True, ""
