from fastapi import APIRouter

from api.v1.adaptation import router as adaptation_router
from api.v1.analytics import router as analytics_router
from api.v1.assessments import router as assessments_router
from api.v1.auth import router as auth_router
from api.v1.behavior import router as behavior_router
from api.v1.emotion import router as emotion_router
from api.v1.memory import router as memory_router
from api.v1.notifications import router as notifications_router
from api.v1.privacy import router as privacy_router
from api.v1.session import router as session_router
from api.v1.teams import router as teams_router

api_v1_router = APIRouter()
api_v1_router.include_router(auth_router)
api_v1_router.include_router(session_router)
api_v1_router.include_router(behavior_router)
api_v1_router.include_router(emotion_router)
api_v1_router.include_router(assessments_router)
api_v1_router.include_router(adaptation_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(memory_router)
api_v1_router.include_router(notifications_router)
api_v1_router.include_router(teams_router)
api_v1_router.include_router(privacy_router)






