"""Signal-driven vocal-stress features.

Replaces the legacy hash stub with real digital-signal-processing features
computed from PCM audio. Vocal stress is a well-studied area; even without a
trained speech-emotion model, a few classic features are genuinely informative:

* **RMS energy** (loudness) — stressed/agitated speech is typically louder;
* **zero-crossing rate** (ZCR) — a proxy for spectral "harshness"/noisiness and
  rough voice quality, which rises under stress;
* **energy-envelope variability** — erratic, choppy loudness tracks agitation,
  while steady energy tracks calm/confident speech;
* **onset rate** — a coarse speaking-tempo estimate (fast speech ↔ arousal).

These map to a vocal stress level and emotion label with documented, monotone
rules. The frontend now sends 16-bit PCM WAV (not opaque webm), so these
features reflect the actual microphone signal.
"""

from __future__ import annotations

import io
import wave
from dataclasses import dataclass

import numpy as np

from models.emotion import AudioResult


@dataclass
class AudioFeatures:
    rms: float               # loudness, 0..1
    zcr: float               # zero-crossing rate, 0..1
    envelope_var: float      # normalized energy-envelope variability, 0..1
    onset_rate: float        # onsets per second
    voiced: bool             # enough energy to be real speech/voice
    sample_rate: int


def decode_wav(raw: bytes) -> tuple[np.ndarray, int] | None:
    """Decode 8/16/32-bit PCM WAV bytes to float samples in [-1, 1] (mono).

    Returns ``None`` if the bytes are not a parseable PCM WAV container (e.g.
    a compressed webm/opus blob), so callers can fall back gracefully.
    """
    try:
        with wave.open(io.BytesIO(raw), "rb") as wav:
            n_channels = wav.getnchannels()
            sampwidth = wav.getsampwidth()
            framerate = wav.getframerate()
            frames = wav.readframes(wav.getnframes())
    except (wave.Error, EOFError, OSError):
        return None

    if not frames:
        return None

    dtype_map = {1: np.uint8, 2: np.int16, 4: np.int32}
    dtype = dtype_map.get(sampwidth)
    if dtype is None:
        return None

    data = np.frombuffer(frames, dtype=dtype).astype(np.float64)
    if sampwidth == 1:  # 8-bit PCM is unsigned, centered at 128
        data = (data - 128.0) / 128.0
    elif sampwidth == 2:
        data = data / 32768.0
    else:
        data = data / 2147483648.0

    if n_channels > 1:
        data = data.reshape(-1, n_channels).mean(axis=1)

    return data, framerate


def extract_features(samples: np.ndarray, sample_rate: int) -> AudioFeatures:
    """Compute DSP features from mono float samples in [-1, 1]."""
    if samples.size == 0:
        return AudioFeatures(0.0, 0.0, 0.0, 0.0, False, sample_rate)

    rms_raw = float(np.sqrt(np.mean(samples ** 2)))
    # Normalize loudness: typical conversational speech ~0.05–0.3 RMS.
    rms = float(np.clip(rms_raw / 0.3, 0.0, 1.0))

    # Zero-crossing rate (fraction of adjacent samples that change sign).
    signs = np.signbit(samples)
    zcr_raw = float(np.mean(signs[1:] != signs[:-1])) if samples.size > 1 else 0.0
    zcr = float(np.clip(zcr_raw / 0.5, 0.0, 1.0))

    # Short-frame energy envelope (~20 ms frames).
    frame = max(1, int(sample_rate * 0.02))
    n_frames = samples.size // frame
    if n_frames >= 2:
        trimmed = samples[: n_frames * frame].reshape(n_frames, frame)
        energy = np.sqrt(np.mean(trimmed ** 2, axis=1))
        mean_e = float(energy.mean())
        envelope_var = float(np.clip(energy.std() / (mean_e + 1e-6), 0.0, 1.0)) if mean_e > 1e-6 else 0.0
        # Onsets: frames whose energy jumps notably above the running mean.
        threshold = mean_e * 1.5
        onsets = int(np.sum((energy[1:] > threshold) & (energy[:-1] <= threshold)))
        duration_s = samples.size / float(sample_rate)
        onset_rate = onsets / duration_s if duration_s > 0 else 0.0
    else:
        envelope_var = 0.0
        onset_rate = 0.0

    voiced = rms_raw > 0.01
    return AudioFeatures(rms, zcr, envelope_var, onset_rate, voiced, sample_rate)


# Vocal emotion decision regions over (stress, energy steadiness).
def _classify_emotion(stress: float, rms: float, envelope_var: float) -> str:
    if not rms:
        return "neutral"
    if stress >= 0.65:
        # Loud + erratic reads as frustrated; loud + steady-ish as stressed.
        return "frustrated" if envelope_var > 0.5 else "stressed"
    if stress >= 0.45:
        return "anxious" if envelope_var > 0.5 else "neutral"
    if rms >= 0.45 and envelope_var < 0.45:
        return "confident"
    return "calm"


def classify(features: AudioFeatures, duration_ms: int = 2000) -> AudioResult:
    """Derive an AudioResult from real DSP features."""
    if not features.voiced:
        return AudioResult(stress_level=0.0, vocal_emotion="neutral", speaking_tempo=0.0, pitch_variance=0.0)

    # Stress = loud + harsh + erratic. Weights chosen so each axis matters.
    stress = 0.45 * features.rms + 0.30 * features.zcr + 0.25 * features.envelope_var
    stress = float(np.clip(stress, 0.0, 1.0))

    # Speaking tempo proxy: onsets ≈ syllable bursts → rough words-per-minute.
    speaking_tempo = float(np.clip(features.onset_rate * 45.0, 0.0, 300.0))

    # Pitch-variance proxy from ZCR and envelope variability.
    pitch_variance = float(np.clip(0.6 * features.zcr + 0.4 * features.envelope_var, 0.0, 1.0))

    emotion = _classify_emotion(stress, features.rms, features.envelope_var)
    return AudioResult(
        stress_level=round(stress, 3),
        vocal_emotion=emotion,
        speaking_tempo=round(speaking_tempo, 1),
        pitch_variance=round(pitch_variance, 3),
    )
