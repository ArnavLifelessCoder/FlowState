from __future__ import annotations

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

