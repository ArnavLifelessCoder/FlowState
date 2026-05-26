from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from core.auth import require_api_token
from dependencies import assessment_service
from models.assessment import (
    AssessmentResult,
    AssessmentSubmission,
    AssessmentTrend,
    InstrumentType,
    WellbeingSnapshot,
)

router = APIRouter(prefix="/assessments", tags=["assessments"])


@router.get("/instruments")
def list_instruments(_: None = Depends(require_api_token)):
    """List all available psychometric instruments."""
    instruments = assessment_service.list_instruments()
    return {
        "instruments": [
            {
                "type": inst.instrument_type.value,
                "name": inst.name,
                "description": inst.description,
                "estimated_seconds": inst.estimated_seconds,
                "question_count": len(inst.questions),
                "research_basis": inst.research_basis,
            }
            for inst in instruments
        ]
    }


@router.get("/instruments/{instrument_type}")
def get_instrument(instrument_type: InstrumentType, _: None = Depends(require_api_token)):
    """Get full instrument definition with all questions for rendering."""
    inst = assessment_service.get_instrument(instrument_type)
    if not inst:
        return {"error": "Unknown instrument"}
    return inst.model_dump(mode="json")


@router.post("/submit")
def submit_assessment(
    payload: AssessmentSubmission, _: None = Depends(require_api_token)
):
    """Submit responses for an assessment and receive scored result."""
    try:
        return assessment_service.score(payload)
    except ValueError as e:
        return JSONResponse(status_code=422, content={"error": str(e)})


@router.get("/history/{user_id}")
def get_assessment_history(
    user_id: str,
    instrument_type: InstrumentType | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    _: None = Depends(require_api_token),
):
    """Get assessment history for a user."""
    results = assessment_service.get_history(user_id, instrument_type, limit)
    return {
        "user_id": user_id,
        "assessments": [r.model_dump(mode="json") for r in results],
        "total_count": len(results),
    }


@router.get("/trend/{user_id}/{instrument_type}")
def get_assessment_trend(
    user_id: str,
    instrument_type: InstrumentType,
    _: None = Depends(require_api_token),
) -> AssessmentTrend:
    """Get trend analysis for a specific instrument over time."""
    return assessment_service.get_trend(user_id, instrument_type)


@router.get("/wellbeing/{user_id}")
def get_wellbeing(
    user_id: str,
    session_id: str | None = Query(default=None),
    _: None = Depends(require_api_token),
) -> WellbeingSnapshot:
    """Get composite wellbeing snapshot combining sensors + self-report."""
    return assessment_service.compute_wellbeing(user_id, session_id)
