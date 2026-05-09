from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone, timedelta

import bcrypt
import jwt

from config import get_settings
from db.behavior_repository import BehaviorRepository
from models.user import TokenPair, UserInfo, UserRecord, UserRegister

logger = logging.getLogger(__name__)


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
JWT_ALGORITHM = "HS256"


class AuthService:
    """JWT auth with user registration, login, and token refresh."""

    def __init__(self, repository: BehaviorRepository) -> None:
        self._repository = repository
        self._settings = get_settings()

    @property
    def _secret(self) -> str:
        return self._settings.jwt_secret

    def register(self, payload: UserRegister) -> UserRecord:
        """Register a new user. Raises ValueError if username taken."""
        existing = self._repository.get_user_by_username(payload.username)
        if existing is not None:
            raise ValueError(f"Username '{payload.username}' already taken")

        user_id = str(uuid.uuid4())
        password_hash = _hash_password(payload.password)
        record = self._repository.create_user(
            user_id=user_id,
            username=payload.username,
            password_hash=password_hash,
            display_name=payload.display_name or payload.username,
        )
        logger.info("user_registered user_id=%s username=%s", user_id, payload.username)
        return record

    def login(self, username: str, password: str) -> TokenPair | None:
        """Authenticate and return tokens. Returns None if credentials invalid."""
        user = self._repository.get_user_by_username(username)
        if user is None:
            return None

        stored_hash = self._repository.get_password_hash(user.user_id)
        if stored_hash is None or not _verify_password(password, stored_hash):
            return None

        return self._issue_tokens(user.user_id)

    def refresh(self, refresh_token: str) -> TokenPair | None:
        """Validate refresh token and issue new token pair."""
        try:
            payload = jwt.decode(refresh_token, self._secret, algorithms=[JWT_ALGORITHM])
            if payload.get("type") != "refresh":
                return None
            user_id = payload.get("sub")
            if not user_id:
                return None
            # Verify user still exists
            user = self._repository.get_user_by_id(user_id)
            if user is None:
                return None
            return self._issue_tokens(user_id)
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def verify_access_token(self, token: str) -> str | None:
        """Verify an access token and return the user_id, or None."""
        try:
            payload = jwt.decode(token, self._secret, algorithms=[JWT_ALGORITHM])
            if payload.get("type") != "access":
                return None
            return payload.get("sub")
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    def get_user_info(self, user_id: str) -> UserInfo | None:
        user = self._repository.get_user_by_id(user_id)
        if user is None:
            return None
        return UserInfo(
            user_id=user.user_id,
            username=user.username,
            display_name=user.display_name,
            created_at=user.created_at,
        )

    def _issue_tokens(self, user_id: str) -> TokenPair:
        now = datetime.now(timezone.utc)
        access_payload = {
            "sub": user_id,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        }
        refresh_payload = {
            "sub": user_id,
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        }
        access_token = jwt.encode(access_payload, self._secret, algorithm=JWT_ALGORITHM)
        refresh_token = jwt.encode(refresh_payload, self._secret, algorithm=JWT_ALGORITHM)
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )
