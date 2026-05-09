from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class UserRegister(BaseModel):
    """Registration request."""
    username: str = Field(..., min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str = Field(default="", max_length=128)


class UserLogin(BaseModel):
    """Login request."""
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class UserRecord(BaseModel):
    """Stored user (never includes password hash)."""
    user_id: str
    username: str
    display_name: str
    created_at: datetime


class TokenPair(BaseModel):
    """JWT access + refresh token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class TokenRefresh(BaseModel):
    """Refresh token request."""
    refresh_token: str


class UserInfo(BaseModel):
    """Current user info returned from /me."""
    user_id: str
    username: str
    display_name: str
    created_at: datetime
