from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


class FrameInferRequest(BaseModel):
    """POST /emotion/infer-frame — camera frame for vision inference."""
    session_id: str = Field(..., min_length=1, max_length=128)
    frame_b64: str = Field(..., min_length=1, description="Base64-encoded JPEG frame")


class AudioInferRequest(BaseModel):
    """POST /emotion/infer-audio — audio chunk for vocal emotion inference."""
    session_id: str = Field(..., min_length=1, max_length=128)
    audio_b64: str = Field(..., min_length=1, description="Base64-encoded 16kHz WAV chunk")
    sample_rate: int = Field(default=16000, ge=8000, le=48000)
    duration_ms: int = Field(default=2000, ge=500, le=10000)


class VisionResult(BaseModel):
    """Output of the vision pipeline."""
    emotion: str = "neutral"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    fatigue_score: float = Field(default=0.0, ge=0.0, le=1.0)
    gaze_direction: str = "center"
    landmarks_detected: bool = False


class AudioResult(BaseModel):
    """Output of the audio pipeline."""
    stress_level: float = Field(default=0.0, ge=0.0, le=1.0)
    vocal_emotion: str = "neutral"
    speaking_tempo: float = Field(default=0.0, ge=0.0, description="Words per minute estimate")
    pitch_variance: float = Field(default=0.0, ge=0.0)


class ModalityWeights(BaseModel):
    """Weights for multimodal fusion."""
    vision: float = Field(default=0.4, ge=0.0, le=1.0)
    audio: float = Field(default=0.3, ge=0.0, le=1.0)
    behavior: float = Field(default=0.3, ge=0.0, le=1.0)


class EmotionState(BaseModel):
    """Fused multimodal emotion state — the core output of the emotion pipeline."""
    session_id: str
    emotion: str = "neutral"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    stress_level: float = Field(default=0.0, ge=0.0, le=1.0)
    cognitive_load: float = Field(default=0.0, ge=0.0, le=1.0)
    attention_level: float = Field(default=0.0, ge=0.0, le=1.0)
    burnout_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    recommended_adaptation: str = "resume_normal"
    modalities_used: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Per-modality breakdown (optional, for transparency)
    vision: VisionResult | None = None
    audio: AudioResult | None = None


class EmotionSnapshotRecord(BaseModel):
    """Stored emotion snapshot record."""
    id: int
    session_id: str
    state: EmotionState
    created_at: datetime


class EmotionHistoryResponse(BaseModel):
    """Paginated emotion history."""
    session_id: str
    items: list[EmotionSnapshotRecord]
    total_count: int
    has_more: bool
    next_cursor: str | None
