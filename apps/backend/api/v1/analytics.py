from fastapi import APIRouter, Depends, Query

from core.auth import require_api_token
from dependencies import analytics_service
from models.behavior import BehaviorHistoryResponse, BehaviorInsightsResponse

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/emotion-history/{session_id}")
def get_emotion_history(
    session_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    cursor: str | None = Query(default=None),
    _: None = Depends(require_api_token),
) -> BehaviorHistoryResponse:
    return analytics_service.history(session_id=session_id, limit=limit, cursor=cursor)


@router.get("/insights/{session_id}")
def get_session_insights(
    session_id: str,
    lookback: int = Query(default=100, ge=1, le=500),
    _: None = Depends(require_api_token),
) -> BehaviorInsightsResponse:
    return analytics_service.insights(session_id=session_id, lookback=lookback)

