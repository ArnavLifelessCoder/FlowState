from __future__ import annotations

from typing import Literal

from db.behavior_repository import BehaviorRepository
from models.behavior import InterventionPlaybackItem, InterventionPlaybackResponse


class InterventionPlaybackService:
    def __init__(self, repository: BehaviorRepository) -> None:
        self._repository = repository

    def timeline(
        self,
        session_id: str,
        limit: int = 100,
        cursor: str | None = None,
        event_type: Literal["all", "decision", "feedback"] = "all",
    ) -> InterventionPlaybackResponse:
        safe_limit = max(1, min(limit, 500))
        decision_before_id, feedback_before_id = self._decode_cursor(cursor)

        decisions = (
            self._repository.get_decisions(
                session_id=session_id,
                limit=safe_limit + 1,
                before_id=decision_before_id,
            )
            if event_type in ("all", "decision")
            else []
        )
        feedback = (
            self._repository.get_feedback(
                session_id=session_id,
                limit=safe_limit + 1,
                before_id=feedback_before_id,
            )
            if event_type in ("all", "feedback")
            else []
        )

        items: list[InterventionPlaybackItem] = []
        for d in decisions:
            items.append(
                InterventionPlaybackItem(
                    event_type="decision",
                    occurred_at=d.created_at,
                    payload={
                        "id": d.id,
                        "state_key": d.state_key,
                        "action": d.action,
                        "exploration": d.exploration,
                        "q_values": d.q_values,
                    },
                )
            )
        for f in feedback:
            items.append(
                InterventionPlaybackItem(
                    event_type="feedback",
                    occurred_at=f.created_at,
                    payload={
                        "id": f.id,
                        "action": f.action,
                        "reward": f.reward,
                        "task_completion_delta": f.task_completion_delta,
                        "emotional_stability_delta": f.emotional_stability_delta,
                    },
                )
            )

        items.sort(key=lambda item: item.occurred_at, reverse=True)
        has_more = len(items) > safe_limit
        items = items[:safe_limit]
        next_cursor = self._build_cursor(items) if has_more and items else None
        return InterventionPlaybackResponse(
            session_id=session_id,
            total_items=len(items),
            has_more=has_more,
            next_cursor=next_cursor,
            items=items,
        )

    @staticmethod
    def _decode_cursor(cursor: str | None) -> tuple[int | None, int | None]:
        if not cursor:
            return None, None
        try:
            parts = cursor.split("|")
            decision_id: int | None = None
            feedback_id: int | None = None
            for part in parts:
                if part.startswith("d:"):
                    decision_id = int(part.removeprefix("d:"))
                elif part.startswith("f:"):
                    feedback_id = int(part.removeprefix("f:"))
            return decision_id, feedback_id
        except ValueError:
            return None, None
        return None, None

    @staticmethod
    def _build_cursor(items: list[InterventionPlaybackItem]) -> str | None:
        min_decision_id: int | None = None
        min_feedback_id: int | None = None
        for item in items:
            event_id = item.payload.get("id")
            if not isinstance(event_id, int):
                continue
            if item.event_type == "decision":
                min_decision_id = (
                    event_id if min_decision_id is None else min(min_decision_id, event_id)
                )
            elif item.event_type == "feedback":
                min_feedback_id = (
                    event_id if min_feedback_id is None else min(min_feedback_id, event_id)
                )
        parts: list[str] = []
        if min_decision_id is not None:
            parts.append(f"d:{min_decision_id}")
        if min_feedback_id is not None:
            parts.append(f"f:{min_feedback_id}")
        return "|".join(parts) if parts else None

