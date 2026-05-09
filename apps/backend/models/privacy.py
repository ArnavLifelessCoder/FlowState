from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class SensingState(BaseModel):
    """Per-session sensing pause/resume state."""
    session_id: str
    vision_enabled: bool = True
    audio_enabled: bool = True
    behavior_enabled: bool = True
    all_paused: bool = False
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SensingUpdate(BaseModel):
    """Request to update sensing modality toggles."""
    session_id: str = Field(..., min_length=1, max_length=128)
    vision_enabled: bool | None = None
    audio_enabled: bool | None = None
    behavior_enabled: bool | None = None
    all_paused: bool | None = None


class UserDataExport(BaseModel):
    """Complete export of all data for a user."""
    user_id: str
    exported_at: datetime
    sessions: list[dict]
    behavior_snapshots: list[dict]
    adaptation_decisions: list[dict]
    adaptation_feedback: list[dict]
    behavioral_profile: dict | None
    daily_summaries: list[dict]
    sensing_states: list[dict]
    total_records: int


class UserDataDeleteResponse(BaseModel):
    user_id: str
    deleted: bool
    records_deleted: dict[str, int]
    deleted_at: datetime
