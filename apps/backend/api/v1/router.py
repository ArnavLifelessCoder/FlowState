from fastapi import APIRouter

from api.v1.adaptation import router as adaptation_router
from api.v1.analytics import router as analytics_router
from api.v1.behavior import router as behavior_router

api_v1_router = APIRouter()
api_v1_router.include_router(behavior_router)
api_v1_router.include_router(adaptation_router)
api_v1_router.include_router(analytics_router)

