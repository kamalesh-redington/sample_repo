import hashlib
import secrets
from typing import Dict, Optional

from fastapi import HTTPException, status

from app.db.session import get_session
from app.models.tables import User

_token_store: Dict[str, int] = {}


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def create_access_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    _token_store[token] = user_id
    return token


def get_user_id_from_token(token: str) -> Optional[int]:
    return _token_store.get(token)


def get_user_by_token(token: str) -> User:
    user_id = get_user_id_from_token(token)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    session = get_session()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication token")
        return user
    finally:
        session.close()


def logout_token(token: str) -> None:
    _token_store.pop(token, None)
