"""Emotion pipeline — orchestrates vision, audio, and behavior modalities.

This is the top-level service that coordinates:
1. Per-modality inference (vision, audio, behavior)
2. Multimodal fusion into a single EmotionState
3. Persistence of emotion snapshots
4. Realtime broadcasting via the hub
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from db.behavior_repository import BehaviorRepository
from models.behavior import BehaviorSnapshot
from models.emotion import AudioResult, EmotionState, VisionResult
from services.audio_service import AudioService
from services.behavior_session_service import BehaviorSessionService
from services.emotion_smoother import EmotionSmoother
from services.fusion_service import FusionService
from services.vision_service import VisionService

logger = logging.getLogger(__name__)


class EmotionPipeline:
    """Top-level orchestrator for multimodal emotion inference."""

    def __init__(
        self,
        repository: BehaviorRepository,
        vision_service: VisionService,
        audio_service: AudioService,
        fusion_service: FusionService,
        behavior_sessions: BehaviorSessionService,
        smoother: EmotionSmoother | None = None,
    ) -> None:
        self._repository = repository
        self._vision = vision_service
        self._audio = audio_service
        self._fusion = fusion_service
        self._behavior_sessions = behavior_sessions
        self._smoother = smoother or EmotionSmoother()

    def infer_frame(self, session_id: str, frame_b64: str) -> EmotionState:
        """Process a camera frame and produce a fused emotion state."""
        vision_result = self._vision.infer(frame_b64)
        behavior = self._get_behavior_snapshot(session_id)

        state = self._fusion.fuse(
            session_id=session_id,
            vision=vision_result,
            audio=None,
            behavior=behavior,
        )

        state = self._finalize(state)
        self._persist_and_broadcast(state)
        return state

    def infer_audio(
        self,
        session_id: str,
        audio_b64: str,
        sample_rate: int = 16000,
        duration_ms: int = 2000,
    ) -> EmotionState:
        """Process an audio chunk and produce a fused emotion state."""
        audio_result = self._audio.infer(audio_b64, sample_rate, duration_ms)
        behavior = self._get_behavior_snapshot(session_id)

        state = self._fusion.fuse(
            session_id=session_id,
            vision=None,
            audio=audio_result,
            behavior=behavior,
        )

        state = self._finalize(state)
        self._persist_and_broadcast(state)
        return state

    def infer_multimodal(
        self,
        session_id: str,
        frame_b64: str | None = None,
        audio_b64: str | None = None,
        sample_rate: int = 16000,
        duration_ms: int = 2000,
    ) -> EmotionState:
        """Process both vision and audio together for full multimodal fusion."""
        vision_result: VisionResult | None = None
        audio_result: AudioResult | None = None

        if frame_b64:
            vision_result = self._vision.infer(frame_b64)

        if audio_b64:
            audio_result = self._audio.infer(audio_b64, sample_rate, duration_ms)

        behavior = self._get_behavior_snapshot(session_id)

        state = self._fusion.fuse(
            session_id=session_id,
            vision=vision_result,
            audio=audio_result,
            behavior=behavior,
        )

        state = self._finalize(state)
        self._persist_and_broadcast(state)
        return state

    def get_current(self, session_id: str) -> EmotionState | None:
        """Get the latest stored emotion state for a session."""
        return self._repository.get_emotion_state(session_id)

    def get_history(
        self,
        session_id: str,
        limit: int = 50,
        before_id: int | None = None,
    ) -> tuple[list[EmotionState], bool]:
        """Get emotion history for a session."""
        return self._repository.get_emotion_history(session_id, limit, before_id)

    def end_session(self, session_id: str) -> None:
        """Release smoothing state for a finished session."""
        self._smoother.reset(session_id)

    def _finalize(self, state: EmotionState) -> EmotionState:
        """Temporally smooth the fused state and realign the recommendation.

        Because smoothing changes the continuous metrics, the recommended
        adaptation is recomputed from the *smoothed* values so the advice the
        user sees matches the numbers the user sees.
        """
        smoothed = self._smoother.smooth(state)
        if smoothed.modalities_used:
            smoothed = smoothed.model_copy(
                update={
                    "recommended_adaptation": self._fusion.recommend_adaptation(
                        smoothed.stress_level,
                        smoothed.cognitive_load,
                        smoothed.attention_level,
                    )
                }
            )
        return smoothed

    def _get_behavior_snapshot(self, session_id: str) -> BehaviorSnapshot | None:
        """Try to get current behavior snapshot for the session."""
        try:
            snapshot = self._repository.get(session_id)
            return snapshot
        except Exception:
            logger.debug("No behavior snapshot available for session %s", session_id)
            return None

    def _persist_and_broadcast(self, state: EmotionState) -> None:
        """Save the emotion state to the repository."""
        try:
            self._repository.save_emotion_state(state)
        except Exception:
            logger.exception("Failed to persist emotion state for %s", state.session_id)
