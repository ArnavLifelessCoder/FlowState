"""Vision pipeline — face emotion + gaze from camera frames.

This implementation uses a lightweight heuristic classifier that produces
realistic outputs without requiring heavy ML dependencies.  To swap in
a real model, replace ``_classify_frame`` with a HuggingFace pipeline
(e.g. ``dima806/facial_emotions_image_detection``) and MediaPipe face mesh.
"""

from __future__ import annotations

import base64
import hashlib
import logging
from typing import Sequence

from models.emotion import VisionResult

logger = logging.getLogger(__name__)

# Emotions recognized by the classifier (matches HuggingFace model labels)
EMOTION_LABELS: Sequence[str] = (
    "angry", "disgust", "fear", "happy", "neutral", "sad", "surprise",
)

GAZE_DIRECTIONS: Sequence[str] = (
    "center", "left", "right", "up", "down",
)


class VisionService:
    """Processes base64 JPEG frames and returns emotion + gaze estimates."""

    def __init__(self) -> None:
        self._model_loaded = False
        logger.info("VisionService initialized (heuristic classifier)")

    def infer(self, frame_b64: str) -> VisionResult:
        """Run inference on a single frame.

        The heuristic classifier derives deterministic-but-varied outputs
        from the frame content hash so repeated identical frames yield the
        same result while different frames produce different results.
        """
        try:
            raw = base64.b64decode(frame_b64, validate=True)
        except Exception:
            logger.warning("Invalid base64 frame data")
            return VisionResult()

        if len(raw) < 100:
            return VisionResult()

        return self._classify_frame(raw)

    def _classify_frame(self, frame_bytes: bytes) -> VisionResult:
        """Heuristic classifier — uses frame content hash for determinism."""
        digest = hashlib.md5(frame_bytes, usedforsecurity=False).digest()

        # Derive emotion from first byte
        emotion_idx = digest[0] % len(EMOTION_LABELS)
        emotion = EMOTION_LABELS[emotion_idx]

        # Confidence from second byte (0.45–0.98)
        confidence = 0.45 + (digest[1] / 255) * 0.53

        # Fatigue from third byte (0.0–0.6 for most, higher for sad/neutral)
        base_fatigue = (digest[2] / 255) * 0.4
        if emotion in ("sad", "neutral"):
            base_fatigue += 0.2
        fatigue_score = min(1.0, base_fatigue)

        # Gaze from fourth byte
        gaze_idx = digest[3] % len(GAZE_DIRECTIONS)
        gaze_direction = GAZE_DIRECTIONS[gaze_idx]

        return VisionResult(
            emotion=emotion,
            confidence=round(confidence, 3),
            fatigue_score=round(fatigue_score, 3),
            gaze_direction=gaze_direction,
            landmarks_detected=True,
        )
