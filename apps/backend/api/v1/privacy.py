from fastapi import APIRouter, Depends

from core.auth import require_api_token
from dependencies import privacy_service
from models.privacy import SensingState, SensingUpdate, UserDataDeleteResponse, UserDataExport

router = APIRouter(prefix="/privacy", tags=["privacy"])


@router.get("/export/{user_id}")
def export_user_data(
    user_id: str, _: None = Depends(require_api_token)
) -> UserDataExport:
    return privacy_service.export_user_data(user_id)


@router.delete("/data/{user_id}")
def delete_all_user_data(
    user_id: str, _: None = Depends(require_api_token)
) -> UserDataDeleteResponse:
    return privacy_service.delete_all_user_data(user_id)


@router.get("/sensing/{session_id}")
def get_sensing_state(
    session_id: str, _: None = Depends(require_api_token)
) -> SensingState:
    return privacy_service.get_sensing_state(session_id)


@router.put("/sensing")
def update_sensing_state(
    update: SensingUpdate, _: None = Depends(require_api_token)
) -> SensingState:
    return privacy_service.update_sensing_state(update)
