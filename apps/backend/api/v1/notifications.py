from fastapi import APIRouter, Depends, Query

from core.auth import require_api_token
from dependencies import notification_gating_service
from models.notification import (
    GatingPolicy,
    NotificationGateResult,
    NotificationQueueResponse,
    NotificationRequest,
    NotificationStats,
    QueuedNotification,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/evaluate")
def evaluate_notification(
    request: NotificationRequest, _: None = Depends(require_api_token)
) -> NotificationGateResult:
    return notification_gating_service.evaluate(request)


@router.get("/queue/{session_id}")
def get_notification_queue(
    session_id: str,
    pending_only: bool = Query(default=True),
    _: None = Depends(require_api_token),
) -> NotificationQueueResponse:
    return notification_gating_service.get_queued(session_id, pending_only=pending_only)


@router.post("/queue/{session_id}/flush")
def flush_notification_queue(
    session_id: str, _: None = Depends(require_api_token)
) -> list[QueuedNotification]:
    return notification_gating_service.flush_queue(session_id)


@router.get("/stats/{session_id}")
def get_notification_stats(
    session_id: str, _: None = Depends(require_api_token)
) -> NotificationStats:
    return notification_gating_service.get_stats(session_id)


@router.get("/policy")
def get_gating_policy(
    _: None = Depends(require_api_token),
) -> GatingPolicy:
    return notification_gating_service.get_policy()


@router.put("/policy")
def update_gating_policy(
    policy: GatingPolicy, _: None = Depends(require_api_token)
) -> GatingPolicy:
    return notification_gating_service.update_policy(policy)
