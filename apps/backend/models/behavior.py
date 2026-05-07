from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from models.session import BehaviorEvent


class BehaviorEventIn(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    event: BehaviorEvent


class BehaviorSnapshot(BaseModel):
    session_id: str
    typing_wpm: float
    error_rate: float
    hesitation_index: float
    task_switches_per_minute: float
    cognitive_load: float
    frustration_score: float
    attention_level: float
    recommended_adaptation: str
    sample_size: int
    updated_at: datetime

    @classmethod
    def from_metrics(cls, session_id: str, metrics: dict[str, float]) -> "BehaviorSnapshot":
        return cls(
            session_id=session_id,
            typing_wpm=metrics["typing_wpm"],
            error_rate=metrics["error_rate"],
            hesitation_index=metrics["hesitation_index"],
            task_switches_per_minute=metrics["task_switches_per_minute"],
            cognitive_load=metrics["cognitive_load"],
            frustration_score=metrics["frustration_score"],
            attention_level=metrics["attention_level"],
            recommended_adaptation=metrics["recommended_adaptation"],
            sample_size=int(metrics["sample_size"]),
            updated_at=datetime.now(timezone.utc),
        )


class UIConfig(BaseModel):
    complexity: str
    density: str
    pace: str
    notifications_paused: bool


class AdaptationConfigResponse(BaseModel):
    session_id: str
    ui_config: UIConfig
    recommended_adaptation: str
    generated_at: datetime


class AdaptationFeedbackIn(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    action: str = Field(..., min_length=1, max_length=64)
    reward: float = Field(..., ge=-1.0, le=1.0)
    decision_state_key: str | None = Field(default=None, max_length=64)
    task_completion_delta: float = Field(default=0.0, ge=-1.0, le=1.0)
    emotional_stability_delta: float = Field(default=0.0, ge=-1.0, le=1.0)


class AdaptationFeedbackRecord(BaseModel):
    id: int
    session_id: str
    action: str
    reward: float
    task_completion_delta: float
    emotional_stability_delta: float
    created_at: datetime


class AdaptationDecision(BaseModel):
    session_id: str
    state_key: str
    action: str
    q_values: dict[str, float]
    exploration: bool
    generated_at: datetime


class LearningUpdate(BaseModel):
    session_id: str
    state_key: str
    action: str
    reward: float
    next_state_key: str
    updated_q_value: float
    updated_at: datetime


class AdaptationDecisionRecord(BaseModel):
    id: int
    session_id: str
    state_key: str
    action: str
    exploration: bool
    q_values: dict[str, float]
    created_at: datetime


class InterventionPlaybackItem(BaseModel):
    event_type: str
    occurred_at: datetime
    payload: dict


class InterventionPlaybackResponse(BaseModel):
    session_id: str
    total_items: int
    has_more: bool
    next_cursor: str | None
    items: list[InterventionPlaybackItem]


class BehaviorSnapshotRecord(BaseModel):
    id: int
    session_id: str
    snapshot: BehaviorSnapshot


class BehaviorHistoryResponse(BaseModel):
    session_id: str
    items: list[BehaviorSnapshotRecord]
    has_more: bool
    next_cursor: str | None


class BehaviorInsightsResponse(BaseModel):
    session_id: str
    sample_count: int
    avg_cognitive_load: float
    avg_frustration_score: float
    avg_attention_level: float
    latest_recommended_adaptation: str

