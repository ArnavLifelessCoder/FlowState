from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class TeamMember(BaseModel):
    """Anonymized team member metrics."""
    anonymous_id: str
    avg_cognitive_load: float
    avg_frustration: float
    avg_attention: float
    total_sessions: int
    total_snapshots: int
    peak_focus_hours: list[int] = Field(default_factory=list)


class TeamAggregate(BaseModel):
    """Aggregate team-level metrics (fully anonymized)."""
    team_id: str
    member_count: int
    avg_cognitive_load: float
    avg_frustration: float
    avg_attention: float
    total_sessions: int
    total_snapshots: int
    stress_hotspots: list[str] = Field(default_factory=list)
    team_peak_hours: list[int] = Field(default_factory=list)
    burnout_risk_count: int = 0
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TeamCreateRequest(BaseModel):
    team_id: str = Field(..., min_length=1, max_length=128)
    user_ids: list[str] = Field(..., min_length=1)


class TeamAnalyticsResponse(BaseModel):
    aggregate: TeamAggregate
    members: list[TeamMember]


class TeamListResponse(BaseModel):
    teams: list[str]
    total: int
