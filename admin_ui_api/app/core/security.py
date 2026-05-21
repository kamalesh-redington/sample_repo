import bcrypt
import secrets
from typing import Dict, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import joinedload

from app.config.logger import setup_logger
from app.config.timer import log_execution_time
from app.db.session import get_session
from app.models.tables import User

logger = setup_logger(__name__)

_token_store: Dict[str, int] = {}


@log_execution_time(logger)
def hash_password(password: str) -> str:
    logger.debug("Password hashing initiated")

    try:
        salt = bcrypt.gensalt(rounds=12)

        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"),
            salt
        ).decode("utf-8")

        logger.info("Password hashing completed successfully")

        return hashed_password

    except Exception as e:
        logger.exception(f"Password hashing failed: {str(e)}")
        raise


@log_execution_time(logger)
def verify_password(password: str, password_hash: str) -> bool:
    logger.debug("Password verification initiated")

    try:
        result = bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8")
        )

        if result:
            logger.info("Password verification successful")
        else:
            logger.warning("Password verification failed")

        return result

    except Exception as e:
        logger.exception(f"Password verification error: {str(e)}")
        raise


@log_execution_time(logger)
def create_access_token(user_id: int) -> str:
    logger.debug(f"Access token creation initiated for user_id: {user_id}")

    try:
        token = secrets.token_urlsafe(32)

        _token_store[token] = user_id

        logger.info(
            f"Access token created successfully for user_id: {user_id}"
        )

        return token

    except Exception as e:
        logger.exception(
            f"Access token creation failed for user_id {user_id}: {str(e)}"
        )
        raise


@log_execution_time(logger)
def get_user_id_from_token(token: str) -> Optional[int]:
    logger.debug("Fetching user_id from access token")

    try:
        user_id = _token_store.get(token)

        if user_id is not None:
            logger.info(f"User_id retrieved successfully: {user_id}")
        else:
            logger.warning("Invalid or expired token lookup attempted")

        return user_id

    except Exception as e:
        logger.exception(f"Token lookup failed: {str(e)}")
        raise


@log_execution_time(logger)
def get_user_by_token(token: str) -> User:
    logger.info("User authentication via token initiated")

    user_id = get_user_id_from_token(token)

    if user_id is None:
        logger.warning("Authentication failed due to invalid or expired token")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    session = get_session()

    try:
        logger.debug(f"Fetching user details for user_id: {user_id}")

        user = (
            session.query(User)
            .options(joinedload(User.role))
            .filter(User.id == user_id)
            .first()
        )

        if user is None:
            logger.warning(
                f"Authentication failed. User not found for user_id: {user_id}"
            )

            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

        logger.info(
            f"User authenticated successfully for user_id: {user_id}"
        )

        return user

    except HTTPException:
        raise

    except Exception as e:
        logger.exception(
            f"User authentication failed for user_id {user_id}: {str(e)}"
        )
        raise

    finally:
        logger.debug("Closing authentication database session")
        session.close()
        logger.debug("Authentication database session closed")


@log_execution_time(logger)
def logout_token(token: str) -> None:
    logger.info("Logout token invalidation initiated")

    try:
        removed = _token_store.pop(token, None)

        if removed is not None:
            logger.info("Token invalidated successfully")
        else:
            logger.warning("Logout attempted with invalid token")

    except Exception as e:
        logger.exception(f"Token invalidation failed: {str(e)}")
        raise