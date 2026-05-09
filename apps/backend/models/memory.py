from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class UserBehavioralProfile(BaseModel):
    user_id: str
    peak_focus_hours: list[int] = Field(default_factory=list)
    stress_triggers: dict[str, float] = Field(default_factory=dict)
    preferred_pace: str = "normal"
    avg_cognitive_load: float = 0.0
    total_sessions: int = 0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DailySummaryIn(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    session_id: str = Field(..., min_length=1, max_length=128)
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")


class DailySummary(BaseModel):
    user_id: str
    session_id: str
    date: str
    avg_cognitive_load: float
    avg_frustration: float
    avg_attention: float
    snapshot_count: int
    peak_hour: int | None = None
    dominant_adaptation: str = "resume_normal"


class ProactiveSuggestion(BaseModel):
    type: str
    severity: str
    message: str
    data: dict


class BehavioralMemoryResponse(BaseModel):
    user_id: str
    profile: UserBehavioralProfile | None
    suggestions: list[ProactiveSuggestion]
    daily_trend: list[DailySummary]


class ProfileBuildResponse(BaseModel):
    user_id: str
    profile: UserBehavioralProfile
    sessions_analyzed: int


class ProfileDeleteResponse(BaseModel):
    user_id: str
    deleted: bool
