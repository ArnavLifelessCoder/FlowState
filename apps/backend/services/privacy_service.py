from __future__ import annotations

import logging
from datetime import datetime, timezone

from db.behavior_repository import BehaviorRepository
from models.privacy import SensingState, SensingUpdate, UserDataDeleteResponse, UserDataExport

logger = logging.getLogger(__name__)


class PrivacyService:
    """GDPR-compliant data export, deletion, and sensing controls."""

    def __init__(self, repository: BehaviorRepository) -> None:
        self._repository = repository

    def export_user_data(self, user_id: str) -> UserDataExport:
        """Export all data for a user as a structured response."""
        raw = self._repository.export_all_user_data(user_id)
        total = sum(
            len(v) if isinstance(v, list) else (1 if v else 0)
            for v in raw.values()
        )
        return UserDataExport(
            user_id=user_id,
            exported_at=datetime.now(timezone.utc),
            sessions=raw["sessions"],
            behavior_snapshots=raw["behavior_snapshots"],
            adaptation_decisions=raw["adaptation_decisions"],
            adaptation_feedback=raw["adaptation_feedback"],
            behavioral_profile=raw["behavioral_profile"],
            daily_summaries=raw["daily_summaries"],
            sensing_states=raw["sensing_states"],
            total_records=total,
        )

    def delete_all_user_data(self, user_id: str) -> UserDataDeleteResponse:
        """Cascade-delete ALL data for a user (GDPR right to erasure)."""
        counts = self._repository.delete_all_user_data(user_id)
        total_deleted = sum(counts.values())
        logger.info(
            "gdpr_delete user_id=%s total_records_deleted=%d counts=%s",
            user_id, total_deleted, counts,
        )
        return UserDataDeleteResponse(
            user_id=user_id,
            deleted=total_deleted > 0,
            records_deleted=counts,
            deleted_at=datetime.now(timezone.utc),
        )

    def get_sensing_state(self, session_id: str) -> SensingState:
        """Get current sensing state, returning defaults if none exists."""
        state = self._repository.get_sensing_state(session_id)
        if state is None:
            return SensingState(session_id=session_id)
        return state

    def update_sensing_state(self, update: SensingUpdate) -> SensingState:
        """Update sensing modality toggles for a session."""
        current = self._repository.get_sensing_state(update.session_id)
        if current is None:
            current = SensingState(session_id=update.session_id)

        # Apply partial updates
        if update.all_paused is not None:
            current.all_paused = update.all_paused
            if update.all_paused:
                current.vision_enabled = False
                current.audio_enabled = False
                current.behavior_enabled = False
        else:
            if update.vision_enabled is not None:
                current.vision_enabled = update.vision_enabled
            if update.audio_enabled is not None:
                current.audio_enabled = update.audio_enabled
            if update.behavior_enabled is not None:
                current.behavior_enabled = update.behavior_enabled
            # Auto-detect if all are disabled
            current.all_paused = not (
                current.vision_enabled or current.audio_enabled or current.behavior_enabled
            )

        current.updated_at = datetime.now(timezone.utc)
        self._repository.upsert_sensing_state(current)
        return current
