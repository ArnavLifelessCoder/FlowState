from fastapi import APIRouter, Depends

from core.auth import require_api_token
from dependencies import behavior_sessions, realtime_hub
from models.behavior import BehaviorEventIn, BehaviorSnapshot

router = APIRouter(prefix="/behavior", tags=["behavior"])


@router.post("/event")
async def ingest_behavior_event(
    payload: BehaviorEventIn, _: None = Depends(require_api_token)
) -> BehaviorSnapshot:
    snapshot = behavior_sessions.ingest(payload.session_id, payload.event)
    await realtime_hub.publish(payload.session_id, snapshot)
    return snapshot


@router.get("/current/{session_id}")
def get_current_behavior_state(
    session_id: str, _: None = Depends(require_api_token)
) -> BehaviorSnapshot:
    return behavior_sessions.current(session_id)

