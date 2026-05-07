from __future__ import annotations

from datetime import datetime, timezone

from models.behavior import AdaptationConfigResponse, AdaptationDecision, BehaviorSnapshot, UIConfig


class AdaptationService:
    """Deterministic adaptation policy for zero-cost MVP."""

    def config_for_snapshot(
        self, snapshot: BehaviorSnapshot, decision: AdaptationDecision | None = None
    ) -> AdaptationConfigResponse:
        action = decision.action if decision is not None else snapshot.recommended_adaptation

        ui_config = UIConfig(
            complexity="normal",
            density="normal",
            pace="normal",
            notifications_paused=False,
        )

        if action == "pause_notifications":
            ui_config.notifications_paused = True
            ui_config.density = "sparse"
            ui_config.pace = "slow"
        elif action == "reduce_ui_complexity":
            ui_config.complexity = "minimal"
            ui_config.density = "sparse"
            ui_config.pace = "slow"
        elif action == "enable_focus_mode":
            ui_config.complexity = "minimal"
            ui_config.density = "sparse"
        elif action == "increase_ui_complexity":
            ui_config.complexity = "advanced"
            ui_config.density = "dense"
            ui_config.pace = "fast"

        return AdaptationConfigResponse(
            session_id=snapshot.session_id,
            ui_config=ui_config,
            recommended_adaptation=action,
            generated_at=datetime.now(timezone.utc),
        )

