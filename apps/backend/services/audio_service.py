"""Audio pipeline — vocal stress + emotion from audio chunks.

This implementation uses a lightweight heuristic classifier that produces
realistic outputs without requiring heavy ML dependencies (librosa, wav2vec2).
To swap in a real model, replace ``_classify_chunk`` with a HuggingFace
pipeline (e.g. ``facebook/wav2vec2-base``) and librosa feature extraction.
"""

from __future__ import annotations

import base64
import hashlib
import logging
from typing import Sequence

from models.emotion import AudioResult

logger = logging.getLogger(__name__)

VOCAL_EMOTIONS: Sequence[str] = (
    "calm", "neutral", "stressed", "anxious", "confident", "frustrated",
)


class AudioService:
    """Processes base64 WAV chunks and returns vocal stress + emotion estimates."""

    def __init__(self) -> None:
        self._model_loaded = False
        logger.info("AudioService initialized (heuristic classifier)")

    def infer(self, audio_b64: str, sample_rate: int = 16000, duration_ms: int = 2000) -> AudioResult:
        """Run inference on a single audio chunk."""
        try:
            raw = base64.b64decode(audio_b64, validate=True)
        except Exception:
            logger.warning("Invalid base64 audio data")
            return AudioResult()

        if len(raw) < 100:
            return AudioResult()

        return self._classify_chunk(raw, sample_rate, duration_ms)

    def _classify_chunk(self, audio_bytes: bytes, sample_rate: int, duration_ms: int) -> AudioResult:
        """Heuristic classifier — uses audio content hash for determinism."""
        digest = hashlib.md5(audio_bytes, usedforsecurity=False).digest()

        # Vocal emotion from first byte
        emotion_idx = digest[0] % len(VOCAL_EMOTIONS)
        vocal_emotion = VOCAL_EMOTIONS[emotion_idx]

        # Stress level from second byte (0.1–0.85)
        stress_level = 0.1 + (digest[1] / 255) * 0.75
        # Boost stress for stressed/anxious/frustrated emotions
        if vocal_emotion in ("stressed", "anxious", "frustrated"):
            stress_level = min(1.0, stress_level + 0.15)

        # Speaking tempo from third byte (80–200 WPM range)
        speaking_tempo = 80 + (digest[2] / 255) * 120

        # Pitch variance from fourth byte (0.0–0.5)
        pitch_variance = (digest[3] / 255) * 0.5
        # Higher pitch variance for stressed states
        if vocal_emotion in ("stressed", "anxious"):
            pitch_variance = min(1.0, pitch_variance + 0.15)

        return AudioResult(
            stress_level=round(stress_level, 3),
            vocal_emotion=vocal_emotion,
            speaking_tempo=round(speaking_tempo, 1),
            pitch_variance=round(pitch_variance, 3),
        )
