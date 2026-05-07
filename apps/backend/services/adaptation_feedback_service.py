from services.adaptation_rl_service import AdaptationRLService
from db.behavior_repository import BehaviorRepository
from models.behavior import AdaptationFeedbackIn, AdaptationFeedbackRecord, BehaviorSnapshot, LearningUpdate


class AdaptationFeedbackService:
    def __init__(self, repository: BehaviorRepository, rl_service: AdaptationRLService) -> None:
        self._repository = repository
        self._rl_service = rl_service

    def add_feedback(self, payload: AdaptationFeedbackIn) -> AdaptationFeedbackRecord:
        return self._repository.add_feedback(payload)

    def list_feedback(self, session_id: str, limit: int = 50) -> list[AdaptationFeedbackRecord]:
        return self._repository.get_feedback(session_id=session_id, limit=limit)

    def apply_learning(
        self,
        payload: AdaptationFeedbackIn,
        current_snapshot: BehaviorSnapshot,
        decision_state_key: str | None = None,
    ) -> LearningUpdate:
        state_key = decision_state_key or self._rl_service.state_key(current_snapshot)
        return self._rl_service.update(
            session_id=payload.session_id,
            state_key=state_key,
            action=payload.action,
            reward=payload.reward,
            next_snapshot=current_snapshot,
        )

