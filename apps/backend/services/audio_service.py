"""Audio pipeline — vocal stress + emotion from audio chunks.

Backend selection (auto):

1. **Signal classifier** (NumPy DSP) — decodes PCM WAV and computes vocal stress
   from real loudness (RMS), harshness (zero-crossing rate), energy-envelope
   variability, and onset rate. This is the default and replaces the old hash
   stub. The frontend now sends 16-bit PCM WAV so these features are meaningful.
2. **Heuristic fallback** — the legacy content-hash classifier, used only when
   NumPy is unavailable or the chunk is not parseable PCM WAV (e.g. a compressed
   webm/opus blob), so the service never hard-fails.
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

try:  # Real DSP is preferred but optional.
    import numpy as np  # noqa: F401  (used by audio_signal)

    from services import audio_signal

    _SIGNAL_AVAILABLE = True
except Exception:  # pragma: no cover - exercised only without scientific stack
    _SIGNAL_AVAILABLE = False


class AudioService:
    """Processes base64 WAV chunks and returns vocal stress + emotion estimates."""

    def __init__(self) -> None:
        logger.info(
            "AudioService initialized (backend=%s)",
            "signal" if _SIGNAL_AVAILABLE else "heuristic",
        )

    def infer(self, audio_b64: str, sample_rate: int = 16000, duration_ms: int = 2000) -> AudioResult:
        """Run inference on a single audio chunk."""
        try:
            raw = base64.b64decode(audio_b64, validate=True)
        except Exception:
            logger.warning("Invalid base64 audio data")
            return AudioResult()

        if len(raw) < 100:
            return AudioResult()

        if _SIGNAL_AVAILABLE:
            decoded = audio_signal.decode_wav(raw)
            if decoded is not None:
                samples, sr = decoded
                features = audio_signal.extract_features(samples, sr)
                return audio_signal.classify(features, duration_ms)

        # Fallback: not parseable PCM WAV, or no scientific stack.
        return self._classify_chunk_heuristic(raw)

    def _classify_chunk_heuristic(self, audio_bytes: bytes) -> AudioResult:
        """Legacy content-hash classifier — deterministic fallback only."""
        digest = hashlib.md5(audio_bytes, usedforsecurity=False).digest()

        vocal_emotion = VOCAL_EMOTIONS[digest[0] % len(VOCAL_EMOTIONS)]
        stress_level = 0.1 + (digest[1] / 255) * 0.75
        if vocal_emotion in ("stressed", "anxious", "frustrated"):
            stress_level = min(1.0, stress_level + 0.15)
        speaking_tempo = 80 + (digest[2] / 255) * 120
        pitch_variance = (digest[3] / 255) * 0.5
        if vocal_emotion in ("stressed", "anxious"):
            pitch_variance = min(1.0, pitch_variance + 0.15)

        return AudioResult(
            stress_level=round(stress_level, 3),
            vocal_emotion=vocal_emotion,
            speaking_tempo=round(speaking_tempo, 1),
            pitch_variance=round(pitch_variance, 3),
        )
