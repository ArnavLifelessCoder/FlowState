from __future__ import annotations

from db.behavior_repository import BehaviorRepository
from models.behavior import BehaviorHistoryResponse, BehaviorInsightsResponse


class AnalyticsService:
    def __init__(self, repository: BehaviorRepository) -> None:
        self._repository = repository

    def history(
        self, session_id: str, limit: int = 100, cursor: str | None = None
    ) -> BehaviorHistoryResponse:
        before_id = int(cursor) if cursor and cursor.isdigit() else None
        items, has_more = self._repository.get_behavior_history(
            session_id=session_id, limit=limit, before_id=before_id
        )
        next_cursor = str(items[-1].id) if has_more and items else None
        return BehaviorHistoryResponse(
            session_id=session_id,
            items=items,
            has_more=has_more,
            next_cursor=next_cursor,
        )

    def insights(self, session_id: str, lookback: int = 100) -> BehaviorInsightsResponse:
        items, _ = self._repository.get_behavior_history(session_id=session_id, limit=lookback)
        if not items:
            return BehaviorInsightsResponse(
                session_id=session_id,
                sample_count=0,
                avg_cognitive_load=0.0,
                avg_frustration_score=0.0,
                avg_attention_level=0.0,
                latest_recommended_adaptation="resume_normal",
            )

        total = len(items)
        avg_cognitive_load = sum(i.snapshot.cognitive_load for i in items) / total
        avg_frustration = sum(i.snapshot.frustration_score for i in items) / total
        avg_attention = sum(i.snapshot.attention_level for i in items) / total

        return BehaviorInsightsResponse(
            session_id=session_id,
            sample_count=total,
            avg_cognitive_load=round(avg_cognitive_load, 4),
            avg_frustration_score=round(avg_frustration, 4),
            avg_attention_level=round(avg_attention, 4),
            latest_recommended_adaptation=items[0].snapshot.recommended_adaptation,
        )

