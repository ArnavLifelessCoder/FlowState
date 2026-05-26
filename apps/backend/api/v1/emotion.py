from fastapi import APIRouter, Depends, Query

from core.auth import require_api_token
from dependencies import emotion_pipeline
from models.emotion import AudioInferRequest, EmotionState, FrameInferRequest

router = APIRouter(prefix="/emotion", tags=["emotion"])


@router.post("/infer-frame")
def infer_frame(
    payload: FrameInferRequest, _: None = Depends(require_api_token)
) -> EmotionState:
    """Process a camera frame and return fused emotion state."""
    return emotion_pipeline.infer_frame(payload.session_id, payload.frame_b64)


@router.post("/infer-audio")
def infer_audio(
    payload: AudioInferRequest, _: None = Depends(require_api_token)
) -> EmotionState:
    """Process an audio chunk and return fused emotion state."""
    return emotion_pipeline.infer_audio(
        payload.session_id,
        payload.audio_b64,
        payload.sample_rate,
        payload.duration_ms,
    )


@router.get("/current/{session_id}")
def get_current_emotion(
    session_id: str, _: None = Depends(require_api_token)
) -> EmotionState:
    """Get the latest emotion state for a session."""
    state = emotion_pipeline.get_current(session_id)
    if state is None:
        return EmotionState(session_id=session_id, modalities_used=[])
    return state


@router.get("/history/{session_id}")
def get_emotion_history(
    session_id: str,
    limit: int = Query(default=50, ge=1, le=500),
    before_id: int | None = Query(default=None),
    _: None = Depends(require_api_token),
) -> dict:
    """Get paginated emotion history for a session."""
    states, has_more = emotion_pipeline.get_history(session_id, limit, before_id)
    return {
        "session_id": session_id,
        "items": [s.model_dump(mode="json") for s in states],
        "total_count": len(states),
        "has_more": has_more,
        "next_cursor": str(states[-1].session_id) if has_more and states else None,
    }
