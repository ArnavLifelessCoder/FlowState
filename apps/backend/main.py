import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.v1.router import api_v1_router
from api.websockets.adaptation_ws import router as adaptation_ws_router
from api.websockets.emotion_ws import router as emotion_ws_router
from config import get_settings
from core.middleware import RequestContextMiddleware
from core.logging import setup_logging
from dependencies import behavior_repository

settings = get_settings()
setup_logging(settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestContextMiddleware)
app.include_router(api_v1_router, prefix="/api/v1")
app.include_router(emotion_ws_router, prefix="/ws")
app.include_router(adaptation_ws_router, prefix="/ws")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "-")
    logger.exception(
        "unhandled_exception path=%s method=%s", request.url.path, request.method, extra={"request_id": request_id}
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
    )


@app.get("/health")
def health() -> dict[str, str | bool]:
    db_ok = behavior_repository.ping()
    status_value = "ok" if db_ok else "degraded"
    return {"status": status_value, "db_ok": db_ok, "environment": settings.environment}


