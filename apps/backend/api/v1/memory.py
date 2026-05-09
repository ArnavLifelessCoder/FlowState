from fastapi import APIRouter, Depends, Query

from core.auth import require_api_token
from dependencies import behavior_repository, memory_service
from models.memory import (
    BehavioralMemoryResponse,
    DailySummary,
    DailySummaryIn,
    ProfileBuildResponse,
    ProfileDeleteResponse,
    ProactiveSuggestion,
)

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/profile/{user_id}")
def get_behavioral_memory(
    user_id: str, _: None = Depends(require_api_token)
) -> BehavioralMemoryResponse:
    return memory_service.get_full_memory(user_id)


@router.post("/profile/{user_id}/build")
def build_behavioral_profile(
    user_id: str,
    session_ids: list[str] | None = None,
    _: None = Depends(require_api_token),
) -> ProfileBuildResponse:
    if session_ids:
        ids = session_ids
    else:
        # Auto-discover sessions for this user from the sessions table,
        # falling back to all distinct session_ids if no sessions are registered.
        ids = behavior_repository.get_session_ids_for_user(user_id)
        if not ids:
            ids = behavior_repository.get_distinct_session_ids()
    return memory_service.build_profile(user_id, ids)


@router.post("/summary")
def record_daily_summary(
    payload: DailySummaryIn, _: None = Depends(require_api_token)
) -> DailySummary:
    return memory_service.record_daily_summary(payload)


@router.get("/suggestions/{user_id}")
def get_proactive_suggestions(
    user_id: str, _: None = Depends(require_api_token)
) -> list[ProactiveSuggestion]:
    return memory_service.get_suggestions_only(user_id)


@router.delete("/profile/{user_id}")
def delete_behavioral_memory(
    user_id: str, _: None = Depends(require_api_token)
) -> ProfileDeleteResponse:
    return memory_service.delete_profile(user_id)
