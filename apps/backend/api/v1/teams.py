from fastapi import APIRouter, Depends, HTTPException

from core.auth import require_api_token
from dependencies import team_analytics_service
from models.team import (
    TeamAnalyticsResponse,
    TeamAggregate,
    TeamCreateRequest,
    TeamListResponse,
)

router = APIRouter(prefix="/teams", tags=["teams"])


@router.post("")
def create_team(
    request: TeamCreateRequest, _: None = Depends(require_api_token)
) -> TeamAggregate:
    return team_analytics_service.create_team(request)


@router.get("")
def list_teams(
    _: None = Depends(require_api_token),
) -> TeamListResponse:
    return team_analytics_service.list_teams()


@router.get("/{team_id}")
def get_team_analytics(
    team_id: str, _: None = Depends(require_api_token)
) -> TeamAnalyticsResponse:
    result = team_analytics_service.get_analytics(team_id)
    if result.aggregate.member_count == 0:
        raise HTTPException(status_code=404, detail="Team not found or empty")
    return result


@router.delete("/{team_id}")
def delete_team(
    team_id: str, _: None = Depends(require_api_token)
) -> dict[str, bool]:
    deleted = team_analytics_service.delete_team(team_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Team not found")
    return {"deleted": True}
