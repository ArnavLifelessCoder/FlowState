from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from db.behavior_repository import BehaviorRepository
from models.memory import DailySummaryIn
from models.session import SessionCreate, SessionEndResponse, SessionListResponse, SessionRecord
from services.memory_service import MemoryService

logger = logging.getLogger(__name__)


class SessionManagementService:
    """Manages session lifecycle: create, end, list, and auto-triggers daily summaries."""

    def __init__(self, repository: BehaviorRepository, memory_service: MemoryService) -> None:
        self._repository = repository
        self._memory_service = memory_service

    def create_session(self, payload: SessionCreate) -> SessionRecord:
        session_id = str(uuid.uuid4())
        record = self._repository.create_session(
            session_id=session_id,
            user_id=payload.user_id,
            platform=payload.platform,
        )
        logger.info(
            "session_created session_id=%s user_id=%s platform=%s",
            session_id, payload.user_id, payload.platform,
        )
        return record

    def end_session(self, session_id: str) -> SessionEndResponse | None:
        record = self._repository.end_session(session_id)
        if record is None:
            return None

        duration = 0.0
        if record.ended_at and record.started_at:
            duration = (record.ended_at - record.started_at).total_seconds()

        # Auto-generate daily summary for the behavioral memory system
        daily_summary_generated = False
        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            summary_payload = DailySummaryIn(
                user_id=record.user_id,
                session_id=session_id,
                date=today,
            )
            self._memory_service.record_daily_summary(summary_payload)
            daily_summary_generated = True
            logger.info(
                "daily_summary_auto_generated session_id=%s user_id=%s date=%s",
                session_id, record.user_id, today,
            )
        except Exception:
            logger.exception("daily_summary_auto_generation_failed session_id=%s", session_id)

        return SessionEndResponse(
            session_id=session_id,
            ended_at=record.ended_at or datetime.now(timezone.utc),
            duration_seconds=round(duration, 2),
            daily_summary_generated=daily_summary_generated,
        )

    def get_session(self, session_id: str) -> SessionRecord | None:
        return self._repository.get_session(session_id)

    def list_sessions(
        self, user_id: str, limit: int = 50, active_only: bool = False,
    ) -> SessionListResponse:
        sessions = self._repository.list_sessions(
            user_id=user_id, limit=limit, active_only=active_only,
        )
        return SessionListResponse(
            user_id=user_id,
            sessions=sessions,
            total=len(sessions),
        )
