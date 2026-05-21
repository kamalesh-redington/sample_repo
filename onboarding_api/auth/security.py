"""Security utilities for authentication and authorization.

Provides password hashing, token verification,
and password generation.
"""

from config.logger import setup_logger

logger = setup_logger(__name__)
from config.timer import log_execution_time

import secrets
import string
import bcrypt

from fastapi import HTTPException, status

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from typing import Optional

# ────────────────────────────────────────────────────────────────────────────────
# Constants
# ────────────────────────────────────────────────────────────────────────────────

# Bcrypt limits input to 72 bytes
MAX_BCRYPT_PASSWORD_BYTES = 72

# Salt rounds for bcrypt
BCRYPT_ROUNDS = 12

# HTTP Bearer for token extraction
security = HTTPBearer()

# ────────────────────────────────────────────────────────────────────────────────
# Normalize Password
# ────────────────────────────────────────────────────────────────────────────────


@log_execution_time(logger)
def _normalize_password(password: str) -> str:
    """Normalize password for bcrypt."""

    logger.debug("Normalizing password for bcrypt")

    if not isinstance(password, str):

        logger.warning("Password received is not string, converting")

        password = str(password)

    encoded = password.encode("utf-8")

    logger.debug(f"Password encoded length: {len(encoded)} bytes")

    if len(encoded) <= MAX_BCRYPT_PASSWORD_BYTES:

        logger.debug("Password within bcrypt byte limit")

        return password

    logger.warning("Password exceeds bcrypt limit, truncating")

    return encoded[:MAX_BCRYPT_PASSWORD_BYTES].decode("utf-8", errors="ignore")


# ────────────────────────────────────────────────────────────────────────────────
# Password Hashing
# ────────────────────────────────────────────────────────────────────────────────


@log_execution_time(logger)
def get_password_hash(password: str) -> str:
    """Hash plain text password."""

    try:

        logger.info("Generating password hash")

        logger.debug("Normalizing password before hashing")

        normalized = _normalize_password(password).encode("utf-8")

        logger.debug("Generating bcrypt salt")

        hashed = bcrypt.hashpw(normalized, bcrypt.gensalt(rounds=BCRYPT_ROUNDS))

        logger.info("Password hash generated successfully")

        logger.debug(f"Generated hash length: {len(hashed)}")

        return hashed.decode("utf-8")

    except Exception as e:

        logger.exception("Password hashing failed")

        raise


# ────────────────────────────────────────────────────────────────────────────────
# Verify Password
# ────────────────────────────────────────────────────────────────────────────────


@log_execution_time(logger)
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against stored hash."""

    try:

        logger.info("Verifying password")

        logger.debug("Normalizing plain password")

        normalized = _normalize_password(plain_password).encode("utf-8")

        logger.debug("Executing bcrypt password verification")

        is_valid = bcrypt.checkpw(normalized, hashed_password.encode("utf-8"))

        logger.info(f"Password verification result: {is_valid}")

        return is_valid

    except Exception as e:

        logger.exception("Password verification failed")

        raise


# ────────────────────────────────────────────────────────────────────────────────
# Generate Strong Password
# ────────────────────────────────────────────────────────────────────────────────


@log_execution_time(logger)
def generate_strong_password(length: int = 16) -> str:
    """Generate strong random password."""

    try:

        logger.info("Generating strong password")

        logger.debug(f"Requested password length: {length}")

        # Character sets
        uppercase = string.ascii_uppercase
        lowercase = string.ascii_lowercase
        digits = string.digits
        special_chars = "!@#$%^&*()-_=+[]{}|;:,.<>?"

        logger.debug("Character sets initialized")

        # Ensure mandatory characters
        password = [
            secrets.choice(uppercase),
            secrets.choice(lowercase),
            secrets.choice(digits),
            secrets.choice(special_chars),
        ]

        logger.debug("Mandatory password characters added")

        # Remaining characters
        all_chars = uppercase + lowercase + digits + special_chars

        password += [secrets.choice(all_chars) for _ in range(length - 4)]

        logger.debug("Random password characters generated")

        # Shuffle
        password = list(password)

        for i in range(len(password) - 1, 0, -1):

            j = secrets.randbelow(i + 1)

            password[i], password[j] = (password[j], password[i])

        logger.debug("Password characters shuffled")

        final_password = "".join(password)

        logger.info("Strong password generated successfully")

        logger.debug(f"Generated password length: {len(final_password)}")

        return final_password

    except Exception as e:

        logger.exception("Strong password generation failed")

        raise


# ────────────────────────────────────────────────────────────────────────────────
# Verify Bearer Token
# ────────────────────────────────────────────────────────────────────────────────


@log_execution_time(logger)
def verify_bearer_token(
    credentials: Optional[HTTPAuthorizationCredentials], expected_token: str
) -> bool:
    """Verify bearer token."""

    try:

        logger.info("Validating bearer token")

        # Missing credentials
        if not credentials:

            logger.warning("Authentication credentials missing")

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.debug(f"Authentication scheme received: {credentials.scheme}")

        # Invalid scheme
        if credentials.scheme != "Bearer":

            logger.warning(f"Invalid authentication scheme: {credentials.scheme}")

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
                headers={"WWW-Authenticate": "Bearer"},
            )

        logger.debug("Comparing bearer token with expected token")

        # Invalid token
        if credentials.credentials != expected_token:

            logger.warning("Invalid bearer token received")

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid token",
            )

        logger.info("Bearer token validated successfully")

        return True

    except HTTPException:

        raise

    except Exception as e:

        logger.exception("Bearer token validation failed")

        raise
