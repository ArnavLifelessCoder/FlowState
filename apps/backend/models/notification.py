from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class NotificationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationRequest(BaseModel):
    """Incoming notification to be evaluated by the gating system."""
    session_id: str = Field(..., min_length=1, max_length=128)
    title: str = Field(..., min_length=1, max_length=256)
    body: str = Field(default="", max_length=1024)
    priority: NotificationPriority = NotificationPriority.NORMAL
    source: str = Field(default="system", max_length=64)


class GateDecision(str, Enum):
    DELIVER = "deliver"
    QUEUE = "queue"
    SUPPRESS = "suppress"


class NotificationGateResult(BaseModel):
    """Result of the notification gating evaluation."""
    notification: NotificationRequest
    decision: GateDecision
    reason: str
    cognitive_load: float
    frustration_score: float
    attention_level: float
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class GatingPolicy(BaseModel):
    """Configurable thresholds for the notification gating system."""
    suppress_cognitive_load: float = Field(default=0.75, ge=0.0, le=1.0)
    suppress_frustration: float = Field(default=0.70, ge=0.0, le=1.0)
    queue_cognitive_load: float = Field(default=0.55, ge=0.0, le=1.0)
    queue_attention: float = Field(default=0.80, ge=0.0, le=1.0)
    always_deliver_critical: bool = True


class QueuedNotification(BaseModel):
    """A notification held in the queue for later delivery."""
    id: int
    notification: NotificationRequest
    reason: str
    queued_at: datetime
    delivered: bool = False
    delivered_at: datetime | None = None


class NotificationQueueResponse(BaseModel):
    session_id: str
    queued: list[QueuedNotification]
    total: int


class NotificationStats(BaseModel):
    session_id: str
    total_evaluated: int
    delivered: int
    queued: int
    suppressed: int
