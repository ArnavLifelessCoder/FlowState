from typing import Literal

from fastapi import APIRouter, Depends, Query

from core.auth import require_api_token
from dependencies import (
    adaptation_feedback_service,
    adaptation_rl_service,
    adaptation_service,
    behavior_sessions,
    intervention_playback_service,
)
from models.behavior import (
    AdaptationConfigResponse,
    AdaptationDecision,
    AdaptationFeedbackIn,
    AdaptationFeedbackRecord,
    InterventionPlaybackResponse,
    LearningUpdate,
)

router = APIRouter(prefix="/adaptation", tags=["adaptation"])


@router.get("/config/{session_id}")
def get_adaptation_config(
    session_id: str, _: None = Depends(require_api_token)
) -> AdaptationConfigResponse:
    snapshot = behavior_sessions.current(session_id)
    decision = adaptation_rl_service.select_action(session_id=session_id, snapshot=snapshot)
    adaptation_rl_service.record_decision(decision)
    return adaptation_service.config_for_snapshot(snapshot=snapshot, decision=decision)


@router.get("/policy/{session_id}")
def get_adaptation_policy(
    session_id: str,
    persist: bool = Query(default=False),
    _: None = Depends(require_api_token),
) -> AdaptationDecision:
    snapshot = behavior_sessions.current(session_id)
    decision = adaptation_rl_service.select_action(session_id=session_id, snapshot=snapshot)
    if persist:
        adaptation_rl_service.record_decision(decision)
    return decision


@router.post("/feedback")
def submit_adaptation_feedback(
    payload: AdaptationFeedbackIn, _: None = Depends(require_api_token)
) -> LearningUpdate:
    adaptation_feedback_service.add_feedback(payload)
    current_snapshot = behavior_sessions.current(payload.session_id)
    return adaptation_feedback_service.apply_learning(
        payload,
        current_snapshot=current_snapshot,
        decision_state_key=payload.decision_state_key,
    )


@router.get("/feedback/{session_id}")
def list_adaptation_feedback(
    session_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    _: None = Depends(require_api_token),
) -> list[AdaptationFeedbackRecord]:
    return adaptation_feedback_service.list_feedback(session_id=session_id, limit=limit)


@router.get("/interventions/{session_id}")
def get_intervention_playback(
    session_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    cursor: str | None = Query(default=None),
    event_type: Literal["all", "decision", "feedback"] = Query(default="all"),
    _: None = Depends(require_api_token),
) -> InterventionPlaybackResponse:
    return intervention_playback_service.timeline(
        session_id=session_id,
        limit=limit,
        cursor=cursor,
        event_type=event_type,
    )

