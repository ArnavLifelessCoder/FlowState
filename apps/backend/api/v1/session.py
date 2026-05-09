from fastapi import APIRouter, Depends, HTTPException, Query

from core.auth import require_api_token
from dependencies import session_management_service
from models.session import (
    SessionCreate,
    SessionEndResponse,
    SessionListResponse,
    SessionRecord,
)

router = APIRouter(prefix="/session", tags=["session"])


@router.post("")
def create_session(
    payload: SessionCreate, _: None = Depends(require_api_token)
) -> SessionRecord:
    return session_management_service.create_session(payload)


@router.get("/{session_id}")
def get_session(
    session_id: str, _: None = Depends(require_api_token)
) -> SessionRecord:
    record = session_management_service.get_session(session_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return record


@router.post("/{session_id}/end")
def end_session(
    session_id: str, _: None = Depends(require_api_token)
) -> SessionEndResponse:
    result = session_management_service.end_session(session_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found or already ended",
        )
    return result


@router.get("/user/{user_id}")
def list_user_sessions(
    user_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    active_only: bool = Query(default=False),
    _: None = Depends(require_api_token),
) -> SessionListResponse:
    return session_management_service.list_sessions(
        user_id=user_id, limit=limit, active_only=active_only,
    )
