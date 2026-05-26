"""Multimodal fusion — combines vision, audio, and behavior signals.

Uses weighted late fusion with configurable per-modality weights.
The fusion output is a single EmotionState that represents the
combined cognitive+emotional assessment.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from models.behavior import BehaviorSnapshot
from models.emotion import AudioResult, EmotionState, ModalityWeights, VisionResult

logger = logging.getLogger(__name__)

# Mapping from vision emotions to stress contribution
_VISION_STRESS_MAP: dict[str, float] = {
    "angry": 0.85,
    "disgust": 0.65,
    "fear": 0.80,
    "happy": 0.10,
    "neutral": 0.25,
    "sad": 0.55,
    "surprise": 0.40,
}

# Mapping from audio emotions to stress contribution
_AUDIO_STRESS_MAP: dict[str, float] = {
    "calm": 0.10,
    "neutral": 0.25,
    "stressed": 0.80,
    "anxious": 0.75,
    "confident": 0.15,
    "frustrated": 0.85,
}

# Vision emotions → dominant fused emotion label
_EMOTION_PRIORITY = ["angry", "fear", "frustrated", "disgust", "sad", "surprise", "happy", "neutral", "calm", "confident"]


class FusionService:
    """Combines vision, audio, and behavior modality outputs into a single EmotionState."""

    def __init__(self, weights: ModalityWeights | None = None) -> None:
        self._weights = weights or ModalityWeights()
        logger.info(
            "FusionService initialized with weights: vision=%.2f audio=%.2f behavior=%.2f",
            self._weights.vision, self._weights.audio, self._weights.behavior,
        )

    def fuse(
        self,
        session_id: str,
        vision: VisionResult | None = None,
        audio: AudioResult | None = None,
        behavior: BehaviorSnapshot | None = None,
    ) -> EmotionState:
        """Produce a fused EmotionState from available modality outputs.

        If a modality is None, its weight is redistributed proportionally
        among the active modalities.
        """
        modalities_used: list[str] = []
        active_weights: dict[str, float] = {}

        if vision is not None:
            modalities_used.append("vision")
            active_weights["vision"] = self._weights.vision
        if audio is not None:
            modalities_used.append("audio")
            active_weights["audio"] = self._weights.audio
        if behavior is not None:
            modalities_used.append("behavior")
            active_weights["behavior"] = self._weights.behavior

        if not modalities_used:
            return EmotionState(
                session_id=session_id,
                modalities_used=[],
                timestamp=datetime.now(timezone.utc),
            )

        # Normalize weights to sum to 1.0
        total = sum(active_weights.values())
        if total > 0:
            active_weights = {k: v / total for k, v in active_weights.items()}

        # --- Compute stress_level ---
        stress = 0.0
        if vision and "vision" in active_weights:
            vision_stress = _VISION_STRESS_MAP.get(vision.emotion, 0.25)
            stress += active_weights["vision"] * vision_stress
        if audio and "audio" in active_weights:
            stress += active_weights["audio"] * audio.stress_level
        if behavior and "behavior" in active_weights:
            stress += active_weights["behavior"] * behavior.frustration_score

        # --- Compute cognitive_load ---
        cognitive_load = 0.0
        if vision and "vision" in active_weights:
            # Fatigue contributes to cognitive load
            cognitive_load += active_weights["vision"] * (0.6 * vision.fatigue_score + 0.4 * _VISION_STRESS_MAP.get(vision.emotion, 0.25))
        if audio and "audio" in active_weights:
            # High pitch variance = more cognitive load
            cognitive_load += active_weights["audio"] * (0.5 * audio.stress_level + 0.5 * min(audio.pitch_variance * 2, 1.0))
        if behavior and "behavior" in active_weights:
            cognitive_load += active_weights["behavior"] * behavior.cognitive_load

        # --- Compute attention_level ---
        attention = 0.0
        if vision and "vision" in active_weights:
            gaze_attention = 1.0 if vision.gaze_direction == "center" else 0.5
            attention += active_weights["vision"] * (0.6 * gaze_attention + 0.4 * (1.0 - vision.fatigue_score))
        if audio and "audio" in active_weights:
            # Calm/confident = higher attention proxy
            audio_attention = 1.0 - audio.stress_level
            attention += active_weights["audio"] * audio_attention
        if behavior and "behavior" in active_weights:
            attention += active_weights["behavior"] * behavior.attention_level

        # --- Burnout risk ---
        burnout_risk = min(1.0, 0.4 * stress + 0.4 * cognitive_load + 0.2 * (1.0 - attention))

        # --- Dominant emotion label ---
        emotion = self._resolve_emotion(vision, audio, stress)

        # --- Confidence ---
        confidences: list[float] = []
        if vision:
            confidences.append(vision.confidence)
        if audio:
            confidences.append(min(1.0, 0.5 + audio.speaking_tempo / 400))
        if behavior and behavior.sample_size > 0:
            confidences.append(min(1.0, behavior.sample_size / 50))
        confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # --- Recommended adaptation ---
        recommended = self._recommended_adaptation(stress, cognitive_load, attention)

        return EmotionState(
            session_id=session_id,
            emotion=emotion,
            confidence=round(min(1.0, confidence), 3),
            stress_level=round(min(1.0, max(0.0, stress)), 4),
            cognitive_load=round(min(1.0, max(0.0, cognitive_load)), 4),
            attention_level=round(min(1.0, max(0.0, attention)), 4),
            burnout_risk=round(min(1.0, max(0.0, burnout_risk)), 4),
            recommended_adaptation=recommended,
            modalities_used=modalities_used,
            timestamp=datetime.now(timezone.utc),
            vision=vision,
            audio=audio,
        )

    @staticmethod
    def _resolve_emotion(
        vision: VisionResult | None,
        audio: AudioResult | None,
        stress: float,
    ) -> str:
        """Pick the dominant emotion label from available modalities."""
        candidates: list[str] = []
        if vision and vision.landmarks_detected:
            candidates.append(vision.emotion)
        if audio:
            candidates.append(audio.vocal_emotion)

        if not candidates:
            if stress > 0.65:
                return "stressed"
            if stress > 0.4:
                return "neutral"
            return "calm"

        # Pick the first one in priority order
        for emotion in _EMOTION_PRIORITY:
            if emotion in candidates:
                return emotion
        return candidates[0]

    @staticmethod
    def _recommended_adaptation(stress: float, cognitive_load: float, attention: float) -> str:
        if stress >= 0.75:
            return "suggest_break"
        if stress >= 0.6:
            return "pause_notifications"
        if cognitive_load >= 0.65:
            return "reduce_ui_complexity"
        if attention < 0.35:
            return "enable_focus_mode"
        if attention > 0.8 and cognitive_load < 0.35:
            return "increase_ui_complexity"
        return "resume_normal"
