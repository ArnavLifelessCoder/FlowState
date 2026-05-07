from __future__ import annotations

import random
from datetime import datetime, timezone

from db.behavior_repository import BehaviorRepository
from models.behavior import AdaptationDecision, BehaviorSnapshot, LearningUpdate


class AdaptationRLService:
    ACTIONS = [
        "reduce_ui_complexity",
        "enable_focus_mode",
        "pause_notifications",
        "slow_content_pacing",
        "increase_ui_complexity",
        "enable_power_features",
        "resume_normal",
        "suggest_break",
    ]

    def __init__(self, repository: BehaviorRepository, alpha: float, gamma: float, epsilon: float) -> None:
        self._repository = repository
        self._alpha = alpha
        self._gamma = gamma
        self._epsilon = epsilon

    def state_key(self, snapshot: BehaviorSnapshot) -> str:
        stress_bucket = self._bucket(snapshot.frustration_score)
        cognitive_bucket = self._bucket(snapshot.cognitive_load)
        attention_bucket = self._bucket(1.0 - snapshot.attention_level)
        return f"{stress_bucket}:{cognitive_bucket}:{attention_bucket}"

    def select_action(self, session_id: str, snapshot: BehaviorSnapshot) -> AdaptationDecision:
        state_key = self.state_key(snapshot)
        q_values = self._repository.get_q_values(session_id, state_key, self.ACTIONS)

        exploration = random.random() < self._epsilon
        if exploration:
            action = random.choice(self.ACTIONS)
        else:
            action = max(q_values.items(), key=lambda item: item[1])[0]
            if all(value == 0.0 for value in q_values.values()):
                action = snapshot.recommended_adaptation

        return AdaptationDecision(
            session_id=session_id,
            state_key=state_key,
            action=action,
            q_values=q_values,
            exploration=exploration,
            generated_at=datetime.now(timezone.utc),
        )

    def record_decision(self, decision: AdaptationDecision) -> None:
        self._repository.add_decision(
            session_id=decision.session_id,
            state_key=decision.state_key,
            action=decision.action,
            exploration=decision.exploration,
            q_values=decision.q_values,
        )

    def update(
        self,
        session_id: str,
        state_key: str,
        action: str,
        reward: float,
        next_snapshot: BehaviorSnapshot,
    ) -> LearningUpdate:
        current_q_values = self._repository.get_q_values(session_id, state_key, self.ACTIONS)
        current_q = current_q_values.get(action, 0.0)

        next_state_key = self.state_key(next_snapshot)
        next_q_values = self._repository.get_q_values(session_id, next_state_key, self.ACTIONS)
        best_next = max(next_q_values.values()) if next_q_values else 0.0

        updated_q = current_q + self._alpha * (reward + self._gamma * best_next - current_q)
        self._repository.upsert_q_value(session_id, state_key, action, updated_q)

        return LearningUpdate(
            session_id=session_id,
            state_key=state_key,
            action=action,
            reward=reward,
            next_state_key=next_state_key,
            updated_q_value=round(updated_q, 6),
            updated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _bucket(value: float) -> str:
        if value < 0.33:
            return "low"
        if value < 0.66:
            return "medium"
        return "high"

