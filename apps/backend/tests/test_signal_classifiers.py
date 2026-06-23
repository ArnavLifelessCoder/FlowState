"""Accuracy + volatility tests for the real signal-driven classifiers.

These verify that the vision/audio pipelines actually respond to image and
audio *content* (the whole point of replacing the hash stub) and that the
end-to-end smoothed emotion stream is not volatile.
"""

from __future__ import annotations

import base64
import io
import os
import sys
import wave

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services import audio_signal, vision_signal
from services.audio_service import AudioService
from services.vision_service import VisionService


# ── image helpers ────────────────────────────────────────────────────

def _jpeg_b64(arr: np.ndarray) -> str:
    img = Image.fromarray(arr.astype(np.uint8), mode="RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return base64.b64encode(buf.getvalue()).decode()


def _sharp_bright_frame() -> np.ndarray:
    # High-contrast checkerboard → high sharpness, mid/high brightness.
    base = np.indices((120, 120)).sum(axis=0) % 2
    img = np.where(base[..., None] == 0, 210, 90).repeat(3, axis=2)
    return img


def _dark_blurry_frame() -> np.ndarray:
    # Dim, smooth gradient → real structure (contrast) but very low local
    # sharpness (a linear ramp has ~zero Laplacian) and low brightness.
    ramp = np.linspace(10, 120, 120).astype(np.uint8)
    img = np.repeat(ramp[None, :], 120, axis=0)
    return np.repeat(img[..., None], 3, axis=2)


def _blank_frame() -> np.ndarray:
    return np.full((120, 120, 3), 128, dtype=np.uint8)


def _blob_frame(cx_fraction: float) -> np.ndarray:
    img = np.full((120, 120, 3), 20, dtype=np.uint8)
    cx = int(cx_fraction * 120)
    x0, x1 = max(0, cx - 20), min(120, cx + 20)
    img[40:80, x0:x1] = 230
    return img


# ── audio helpers ────────────────────────────────────────────────────

def _wav_b64(samples: np.ndarray, sample_rate: int = 16000) -> str:
    pcm = np.clip(samples, -1, 1)
    pcm16 = (pcm * 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm16.tobytes())
    return base64.b64encode(buf.getvalue()).decode()


def _tone(freq: float, amp: float, sr: int = 16000, dur: float = 1.0) -> np.ndarray:
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    return amp * np.sin(2 * np.pi * freq * t)


def _noise(amp: float, sr: int = 16000, dur: float = 1.0) -> np.ndarray:
    rng = np.random.default_rng(42)
    return amp * rng.uniform(-1, 1, int(sr * dur))


# ── Vision feature accuracy ──────────────────────────────────────────

class TestVisionFeatures:
    def test_sharp_frame_more_sharpness_than_blurry(self):
        sharp = vision_signal.extract_features(vision_signal.to_grayscale(_sharp_bright_frame()))
        blurry = vision_signal.extract_features(vision_signal.to_grayscale(_dark_blurry_frame()))
        assert sharp.sharpness > blurry.sharpness

    def test_blank_frame_not_face_like(self):
        feats = vision_signal.extract_features(vision_signal.to_grayscale(_blank_frame()))
        assert feats.face_like is False

    def test_gaze_tracks_bright_region(self):
        left = vision_signal.classify(
            vision_signal.extract_features(vision_signal.to_grayscale(_blob_frame(0.15)))
        )
        right = vision_signal.classify(
            vision_signal.extract_features(vision_signal.to_grayscale(_blob_frame(0.85)))
        )
        assert left.gaze_direction == "left"
        assert right.gaze_direction == "right"

    def test_dark_blurry_more_fatigued_than_sharp_bright(self):
        sharp = vision_signal.classify(
            vision_signal.extract_features(vision_signal.to_grayscale(_sharp_bright_frame()))
        )
        blurry = vision_signal.classify(
            vision_signal.extract_features(vision_signal.to_grayscale(_dark_blurry_frame()))
        )
        assert blurry.fatigue_score > sharp.fatigue_score


# ── Vision service (decode + classify, real JPEGs) ───────────────────

class TestVisionServiceSignal:
    def setup_method(self):
        self.service = VisionService()

    def test_real_jpeg_uses_signal_path(self):
        result = self.service.infer(_jpeg_b64(_sharp_bright_frame()))
        assert result.landmarks_detected is True
        assert 0.0 <= result.fatigue_score <= 1.0
        assert result.gaze_direction in ("center", "left", "right", "up", "down")

    def test_deterministic(self):
        frame = _jpeg_b64(_sharp_bright_frame())
        assert self.service.infer(frame).fatigue_score == self.service.infer(frame).fatigue_score

    def test_content_drives_output(self):
        sharp = self.service.infer(_jpeg_b64(_sharp_bright_frame()))
        blurry = self.service.infer(_jpeg_b64(_dark_blurry_frame()))
        assert blurry.fatigue_score > sharp.fatigue_score

    def test_invalid_bytes_fall_back_gracefully(self):
        # Non-image bytes must not crash — heuristic fallback kicks in.
        result = self.service.infer(base64.b64encode(bytes(range(256))).decode())
        assert result.landmarks_detected is True
        assert result.emotion in (
            "angry", "disgust", "fear", "happy", "neutral", "sad", "surprise",
        )


# ── Audio DSP accuracy ───────────────────────────────────────────────

class TestAudioFeatures:
    def test_silence_not_voiced(self):
        feats = audio_signal.extract_features(np.zeros(16000), 16000)
        assert feats.voiced is False

    def test_loud_has_higher_rms(self):
        quiet = audio_signal.extract_features(_tone(200, 0.05), 16000)
        loud = audio_signal.extract_features(_tone(200, 0.5), 16000)
        assert loud.rms > quiet.rms

    def test_noise_has_higher_zcr_than_tone(self):
        tone = audio_signal.extract_features(_tone(150, 0.4), 16000)
        noise = audio_signal.extract_features(_noise(0.4), 16000)
        assert noise.zcr > tone.zcr

    def test_decode_rejects_non_wav(self):
        assert audio_signal.decode_wav(bytes(range(256))) is None


class TestAudioServiceSignal:
    def setup_method(self):
        self.service = AudioService()

    def test_silence_zero_stress(self):
        result = self.service.infer(_wav_b64(np.zeros(16000)))
        assert result.stress_level == 0.0
        assert result.vocal_emotion == "neutral"

    def test_loud_harsh_more_stress_than_quiet_calm(self):
        calm = self.service.infer(_wav_b64(_tone(180, 0.06)))
        harsh = self.service.infer(_wav_b64(_noise(0.7)))
        assert harsh.stress_level > calm.stress_level

    def test_loud_harsh_classified_stressed(self):
        result = self.service.infer(_wav_b64(_noise(0.85)))
        assert result.vocal_emotion in ("stressed", "anxious", "frustrated")

    def test_quiet_tone_classified_calm(self):
        result = self.service.infer(_wav_b64(_tone(180, 0.05)))
        assert result.vocal_emotion in ("calm", "neutral")

    def test_webm_bytes_fall_back(self):
        # Compressed (non-WAV) bytes → heuristic fallback, no crash.
        result = self.service.infer(base64.b64encode(b"\x1aE\xdf\xa3" + bytes(300)).decode())
        assert result.vocal_emotion in (
            "calm", "neutral", "stressed", "anxious", "confident", "frustrated",
        )


# ── End-to-end volatility ────────────────────────────────────────────

class TestPipelineVolatility:
    def _pipeline(self, tmp_path):
        from db.behavior_repository import BehaviorRepository
        from services.behavior_session_service import BehaviorSessionService
        from services.emotion_pipeline import EmotionPipeline
        from services.fusion_service import FusionService

        repo = BehaviorRepository(f"sqlite:///{tmp_path / 'vol.db'}")
        repo.initialize()
        return EmotionPipeline(
            repository=repo,
            vision_service=VisionService(),
            audio_service=AudioService(),
            fusion_service=FusionService(),
            behavior_sessions=BehaviorSessionService(repository=repo),
        )

    def test_smoothed_stream_is_not_volatile(self, tmp_path):
        """A noisy frame stream must yield a bounded, low-jitter stress signal."""
        pipeline = self._pipeline(tmp_path)
        rng = np.random.default_rng(7)

        stresses = []
        labels = []
        for _ in range(40):
            # Each frame is a slightly different noisy image (real-world jitter).
            frame = (rng.uniform(0, 255, (120, 120, 3))).astype(np.uint8)
            state = pipeline.infer_frame("vol-sess", _jpeg_b64(frame))
            stresses.append(state.stress_level)
            labels.append(state.emotion)

        # Frame-to-frame stress change stays small after smoothing.
        deltas = [abs(stresses[i] - stresses[i - 1]) for i in range(1, len(stresses))]
        assert max(deltas) < 0.2, f"stress too jumpy: max delta {max(deltas)}"

        # The label should not flip on most frames (hysteresis at work).
        switches = sum(1 for i in range(1, len(labels)) if labels[i] != labels[i - 1])
        assert switches <= len(labels) // 4, f"label too volatile: {switches} switches"

    def test_stability_reported(self, tmp_path):
        pipeline = self._pipeline(tmp_path)
        last = None
        for _ in range(15):
            last = pipeline.infer_frame("stab-sess", _jpeg_b64(_sharp_bright_frame()))
        # A steady input should converge to a high stability score.
        assert last is not None
        assert last.stability >= 0.8
        assert last.trend in ("rising", "falling", "steady")
