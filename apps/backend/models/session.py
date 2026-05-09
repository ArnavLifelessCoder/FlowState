from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class BehaviorEventType(str, Enum):
    KEYPRESS = "keypress"
    MOUSE_MOVE = "mouse_move"
    SCROLL = "scroll"
    CLICK = "click"
    FOCUS_CHANGE = "focus_change"


class BehaviorEvent(BaseModel):
    type: BehaviorEventType
    timestamp: float = Field(..., ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ── Session Management ──────────────────────────────────────────────


class SessionCreate(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    platform: str = Field(default="web", max_length=32)


class SessionRecord(BaseModel):
    session_id: str
    user_id: str
    started_at: datetime
    ended_at: datetime | None = None
    platform: str = "web"
    is_active: bool = True


class SessionEndResponse(BaseModel):
    session_id: str
    ended_at: datetime
    duration_seconds: float
    daily_summary_generated: bool


class SessionListResponse(BaseModel):
    user_id: str
    sessions: list[SessionRecord]
    total: int

