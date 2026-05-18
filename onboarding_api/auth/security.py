"""Security utilities for authentication and authorization.

Provides password hashing, token verification, and password generation.
"""
import secrets
import string
import bcrypt
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

# Bcrypt limits input to 72 bytes. This helper enforces that limit safely.
MAX_BCRYPT_PASSWORD_BYTES = 72

# Salt rounds for bcrypt
BCRYPT_ROUNDS = 12

# HTTP Bearer for token extraction
security = HTTPBearer()


def _normalize_password(password: str) -> str:
    """Normalize password for bcrypt by truncating to 72 bytes."""
    if not isinstance(password, str):
        password = str(password)
    encoded = password.encode("utf-8")
    if len(encoded) <= MAX_BCRYPT_PASSWORD_BYTES:
        return password
    return encoded[:MAX_BCRYPT_PASSWORD_BYTES].decode("utf-8", errors="ignore")


def get_password_hash(password: str) -> str:
    """Hash a plain text password.
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
    """
    normalized = _normalize_password(password).encode("utf-8")
    hashed = bcrypt.hashpw(normalized, bcrypt.gensalt(rounds=BCRYPT_ROUNDS))
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password from database
        
    Returns:
        bool: True if password matches, False otherwise
    """
    normalized = _normalize_password(plain_password).encode("utf-8")
    return bcrypt.checkpw(normalized, hashed_password.encode("utf-8"))


def generate_strong_password(length: int = 16) -> str:
    """Generate a strong random password.
    
    Password includes uppercase, lowercase, digits, and special characters.
    
    Args:
        length: Length of the password (default 16)
        
    Returns:
        str: Generated password
    """
    # Define character sets
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    special_chars = "!@#$%^&*()-_=+[]{}|;:,.<>?"
    
    # Ensure at least one character from each set
    password = [
        secrets.choice(uppercase),
        secrets.choice(lowercase),
        secrets.choice(digits),
        secrets.choice(special_chars)
    ]
    
    # Fill the rest with random characters from all sets
    all_chars = uppercase + lowercase + digits + special_chars
    password += [secrets.choice(all_chars) for _ in range(length - 4)]
    
    # Shuffle to avoid predictable patterns
    password = list(password)
    for i in range(len(password) - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        password[i], password[j] = password[j], password[i]
    
    return ''.join(password)


def verify_bearer_token(credentials: Optional[HTTPAuthorizationCredentials], expected_token: str) -> bool:
    """Verify a bearer token against an expected token.
    
    Args:
        credentials: HTTPAuthCredentials from request header
        expected_token: Expected token to match against
        
    Returns:
        bool: True if token matches, False otherwise
        
    Raises:
        HTTPException: If credentials are missing
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if credentials.scheme != "Bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication scheme",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if credentials.credentials != expected_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid token",
        )
    
    return True
