from __future__ import annotations

from threading import RLock

from models.behavior import BehaviorSnapshot
from models.session import BehaviorEvent
from db.behavior_repository import BehaviorRepository
from services.behavior_service import BehaviorService


class BehaviorSessionService:
    """Maintains per-session behavior processors and snapshots."""

    def __init__(self, repository: BehaviorRepository, window_size: int = 500) -> None:
        self._window_size = window_size
        self._sessions: dict[str, BehaviorService] = {}
        self._repository = repository
        self._lock = RLock()

    def ingest(self, session_id: str, event: BehaviorEvent) -> BehaviorSnapshot:
        service = self._get_or_create(session_id)
        service.ingest(event)
        snapshot = BehaviorSnapshot.from_metrics(session_id, service.snapshot())
        self._repository.upsert(snapshot)
        return snapshot

    def current(self, session_id: str) -> BehaviorSnapshot:
        service = self._get_or_create(session_id)
        if service.event_count() == 0:
            persisted = self._repository.get(session_id)
            if persisted is not None:
                return persisted
        snapshot = BehaviorSnapshot.from_metrics(session_id, service.snapshot())
        self._repository.upsert(snapshot)
        return snapshot

    def _get_or_create(self, session_id: str) -> BehaviorService:
        with self._lock:
            service = self._sessions.get(session_id)
            if service is None:
                service = BehaviorService(window_size=self._window_size)
                self._sessions[session_id] = service
            return service

