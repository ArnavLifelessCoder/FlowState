"""Vision pipeline — face fatigue/gaze + (optional) facial-emotion model.

Backend selection (auto):

1. **Signal classifier** (NumPy/Pillow) — decodes the real frame and computes
   fatigue, gaze, and face presence from genuine image statistics. This is the
   default and replaces the old hash stub that tracked nothing.
2. **ONNX facial-emotion model** (optional) — if ``vision_onnx_model_path`` is
   configured and loads, its emotion label/confidence are layered on top of the
   signal classifier's fatigue/gaze.
3. **Heuristic fallback** — the legacy content-hash classifier, used only when
   NumPy/Pillow are unavailable or a frame cannot be decoded, so the service
   never hard-fails.
"""

from __future__ import annotations

import base64
import hashlib
import io
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

try:  # Real image analysis is preferred but optional.
    import numpy as np
    from PIL import Image

    from services import vision_signal

    _SIGNAL_AVAILABLE = True
except Exception:  # pragma: no cover - exercised only without scientific stack
    _SIGNAL_AVAILABLE = False


class VisionService:
    """Processes base64 JPEG frames and returns emotion + gaze estimates."""

    def __init__(self, onnx_model_path: str | None = None) -> None:
        self._onnx = None
        if onnx_model_path and _SIGNAL_AVAILABLE:
            from services.onnx_emotion import OnnxVisionClassifier

            candidate = OnnxVisionClassifier(onnx_model_path)
            if candidate.load():
                self._onnx = candidate
        backend = "signal" if _SIGNAL_AVAILABLE else "heuristic"
        if self._onnx is not None:
            backend = "onnx+signal"
        logger.info("VisionService initialized (backend=%s)", backend)

    def infer(self, frame_b64: str) -> VisionResult:
        """Run inference on a single frame."""
        try:
            raw = base64.b64decode(frame_b64, validate=True)
        except Exception:
            logger.warning("Invalid base64 frame data")
            return VisionResult()

        if len(raw) < 100:
            return VisionResult()

        if _SIGNAL_AVAILABLE:
            result = self._infer_signal(raw)
            if result is not None:
                return result

        # Fallback: bytes are not a decodable image, or no scientific stack.
        return self._classify_frame_heuristic(raw)

    def _infer_signal(self, raw: bytes) -> VisionResult | None:
        """Decode the frame and classify it from real image features."""
        try:
            img = Image.open(io.BytesIO(raw)).convert("RGB")
            rgb = np.asarray(img)
        except Exception:
            return None  # not a real image → let caller fall back

        gray = vision_signal.to_grayscale(rgb)
        features = vision_signal.extract_features(gray)
        result = vision_signal.classify(features)

        # Layer a real facial-emotion model on top, if one is loaded.
        if self._onnx is not None and result.landmarks_detected:
            onnx_result = self._onnx.classify(rgb)
            if onnx_result is not None:
                result = result.model_copy(update={
                    "emotion": onnx_result.emotion,
                    "confidence": onnx_result.confidence,
                })
        return result

    def _classify_frame_heuristic(self, frame_bytes: bytes) -> VisionResult:
        """Legacy content-hash classifier — deterministic fallback only."""
        digest = hashlib.md5(frame_bytes, usedforsecurity=False).digest()

        emotion = EMOTION_LABELS[digest[0] % len(EMOTION_LABELS)]
        confidence = 0.45 + (digest[1] / 255) * 0.53
        base_fatigue = (digest[2] / 255) * 0.4
        if emotion in ("sad", "neutral"):
            base_fatigue += 0.2
        fatigue_score = min(1.0, base_fatigue)
        gaze_direction = GAZE_DIRECTIONS[digest[3] % len(GAZE_DIRECTIONS)]

        return VisionResult(
            emotion=emotion,
            confidence=round(confidence, 3),
            fatigue_score=round(fatigue_score, 3),
            gaze_direction=gaze_direction,
            landmarks_detected=True,
        )
