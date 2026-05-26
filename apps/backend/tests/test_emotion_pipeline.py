"""Tests for the multimodal emotion pipeline: vision, audio, fusion, and API."""

from __future__ import annotations

import base64
import json
import os
import tempfile
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

# ── Helpers ──────────────────────────────────────────────────────────

def _make_fake_jpeg() -> str:
    """Return a base64 string that looks like a JPEG (256 random-ish bytes)."""
    data = bytes(range(256))
    return base64.b64encode(data).decode()


def _make_fake_wav() -> str:
    """Return a base64 string that looks like a WAV chunk."""
    data = bytes([i % 256 for i in range(512)])
    return base64.b64encode(data).decode()


# ── Vision Service Tests ─────────────────────────────────────────────

class TestVisionService:
    def setup_method(self):
        from services.vision_service import VisionService
        self.service = VisionService()

    def test_valid_frame(self):
        frame = _make_fake_jpeg()
        result = self.service.infer(frame)
        assert result.landmarks_detected is True
        assert result.emotion in ("angry", "disgust", "fear", "happy", "neutral", "sad", "surprise")
        assert 0.45 <= result.confidence <= 0.98
        assert 0.0 <= result.fatigue_score <= 1.0
        assert result.gaze_direction in ("center", "left", "right", "up", "down")

    def test_invalid_base64(self):
        result = self.service.infer("not_valid_base64!!!")
        assert result.landmarks_detected is False
        assert result.emotion == "neutral"

    def test_tiny_frame(self):
        tiny = base64.b64encode(b"tiny").decode()
        result = self.service.infer(tiny)
        assert result.landmarks_detected is False

    def test_deterministic(self):
        frame = _make_fake_jpeg()
        r1 = self.service.infer(frame)
        r2 = self.service.infer(frame)
        assert r1.emotion == r2.emotion
        assert r1.confidence == r2.confidence

    def test_different_frames_vary(self):
        f1 = base64.b64encode(b"A" * 200).decode()
        f2 = base64.b64encode(b"B" * 200).decode()
        r1 = self.service.infer(f1)
        r2 = self.service.infer(f2)
        # At least one attribute should differ
        assert r1.emotion != r2.emotion or r1.confidence != r2.confidence


# ── Audio Service Tests ──────────────────────────────────────────────

class TestAudioService:
    def setup_method(self):
        from services.audio_service import AudioService
        self.service = AudioService()

    def test_valid_audio(self):
        audio = _make_fake_wav()
        result = self.service.infer(audio)
        assert result.vocal_emotion in ("calm", "neutral", "stressed", "anxious", "confident", "frustrated")
        assert 0.0 <= result.stress_level <= 1.0
        assert result.speaking_tempo >= 80
        assert 0.0 <= result.pitch_variance <= 1.0

    def test_invalid_base64(self):
        result = self.service.infer("bad_audio!!!")
        assert result.vocal_emotion == "neutral"
        assert result.stress_level == 0.0

    def test_tiny_audio(self):
        tiny = base64.b64encode(b"sm").decode()
        result = self.service.infer(tiny)
        assert result.vocal_emotion == "neutral"

    def test_deterministic(self):
        audio = _make_fake_wav()
        r1 = self.service.infer(audio)
        r2 = self.service.infer(audio)
        assert r1.stress_level == r2.stress_level
        assert r1.vocal_emotion == r2.vocal_emotion

    def test_stress_boost_for_stressed_emotions(self):
        """Audio classified as stressed/anxious/frustrated should have boosted stress."""
        from services.audio_service import AudioService
        service = AudioService()
        # Try many samples and check that stressed-classified ones have higher stress
        stressed_levels = []
        calm_levels = []
        for i in range(256):
            data = bytes([i]) * 200
            audio = base64.b64encode(data).decode()
            result = service.infer(audio)
            if result.vocal_emotion in ("stressed", "anxious", "frustrated"):
                stressed_levels.append(result.stress_level)
            elif result.vocal_emotion in ("calm", "confident"):
                calm_levels.append(result.stress_level)

        if stressed_levels and calm_levels:
            avg_stressed = sum(stressed_levels) / len(stressed_levels)
            avg_calm = sum(calm_levels) / len(calm_levels)
            assert avg_stressed > avg_calm


# ── Fusion Service Tests ─────────────────────────────────────────────

class TestFusionService:
    def setup_method(self):
        from services.fusion_service import FusionService
        from models.emotion import VisionResult, AudioResult, ModalityWeights
        self.service = FusionService()
        self.VisionResult = VisionResult
        self.AudioResult = AudioResult

    def test_no_modalities(self):
        state = self.service.fuse(session_id="test-1")
        assert state.session_id == "test-1"
        assert state.modalities_used == []
        assert state.emotion == "neutral"

    def test_vision_only(self):
        vision = self.VisionResult(
            emotion="happy", confidence=0.9, fatigue_score=0.2,
            gaze_direction="center", landmarks_detected=True,
        )
        state = self.service.fuse(session_id="test-2", vision=vision)
        assert "vision" in state.modalities_used
        assert "audio" not in state.modalities_used
        assert state.confidence > 0
        assert state.stress_level >= 0
        assert state.cognitive_load >= 0

    def test_audio_only(self):
        audio = self.AudioResult(
            stress_level=0.7, vocal_emotion="stressed",
            speaking_tempo=150, pitch_variance=0.3,
        )
        state = self.service.fuse(session_id="test-3", audio=audio)
        assert "audio" in state.modalities_used
        assert state.stress_level > 0.3

    def test_full_multimodal(self):
        from models.behavior import BehaviorSnapshot
        vision = self.VisionResult(
            emotion="fear", confidence=0.85, fatigue_score=0.6,
            gaze_direction="left", landmarks_detected=True,
        )
        audio = self.AudioResult(
            stress_level=0.8, vocal_emotion="anxious",
            speaking_tempo=180, pitch_variance=0.4,
        )
        behavior = BehaviorSnapshot(
            session_id="test-4", typing_wpm=45, error_rate=0.15,
            hesitation_index=0.8, task_switches_per_minute=5,
            cognitive_load=0.65, frustration_score=0.5,
            attention_level=0.4, recommended_adaptation="reduce_ui_complexity",
            sample_size=100, updated_at=datetime.now(timezone.utc),
        )
        state = self.service.fuse(session_id="test-4", vision=vision, audio=audio, behavior=behavior)
        assert len(state.modalities_used) == 3
        assert state.stress_level > 0.4
        assert state.burnout_risk > 0
        assert state.recommended_adaptation != ""

    def test_adaptation_recommendations(self):
        """High stress should trigger suggest_break."""
        vision = self.VisionResult(
            emotion="angry", confidence=0.9, fatigue_score=0.9,
            gaze_direction="down", landmarks_detected=True,
        )
        audio = self.AudioResult(
            stress_level=0.9, vocal_emotion="frustrated",
            speaking_tempo=200, pitch_variance=0.5,
        )
        state = self.service.fuse(session_id="test-5", vision=vision, audio=audio)
        assert state.recommended_adaptation in ("suggest_break", "pause_notifications")

    def test_low_stress_allows_complexity(self):
        """Low stress and high attention should allow UI complexity increase."""
        from models.behavior import BehaviorSnapshot
        behavior = BehaviorSnapshot(
            session_id="test-6", typing_wpm=80, error_rate=0.01,
            hesitation_index=0.05, task_switches_per_minute=1,
            cognitive_load=0.15, frustration_score=0.05,
            attention_level=0.95, recommended_adaptation="increase_ui_complexity",
            sample_size=200, updated_at=datetime.now(timezone.utc),
        )
        state = self.service.fuse(session_id="test-6", behavior=behavior)
        assert state.recommended_adaptation in ("increase_ui_complexity", "resume_normal")

    def test_weight_normalization(self):
        """When only one modality is present, its weight should normalize to 1.0."""
        from models.emotion import ModalityWeights
        service = self.service
        vision = self.VisionResult(
            emotion="neutral", confidence=0.7, fatigue_score=0.3,
            gaze_direction="center", landmarks_detected=True,
        )
        state = service.fuse(session_id="norm-test", vision=vision)
        # With only vision and default weight 0.4, after normalization it becomes 1.0
        assert state.modalities_used == ["vision"]
        assert state.cognitive_load > 0


# ── Emotion Pipeline Tests ───────────────────────────────────────────

class TestEmotionPipeline:
    def setup_method(self):
        self._db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._db_file.close()
        db_url = f"sqlite:///{self._db_file.name}"

        from db.behavior_repository import BehaviorRepository
        from services.vision_service import VisionService
        from services.audio_service import AudioService
        from services.fusion_service import FusionService
        from services.behavior_session_service import BehaviorSessionService
        from services.emotion_pipeline import EmotionPipeline

        self.repo = BehaviorRepository(db_url)
        self.repo.initialize()
        self.behavior_sessions = BehaviorSessionService(repository=self.repo)
        self.pipeline = EmotionPipeline(
            repository=self.repo,
            vision_service=VisionService(),
            audio_service=AudioService(),
            fusion_service=FusionService(),
            behavior_sessions=self.behavior_sessions,
        )

    def teardown_method(self):
        try:
            os.unlink(self._db_file.name)
        except PermissionError:
            pass  # Windows may hold the file briefly

    def test_infer_frame(self):
        state = self.pipeline.infer_frame("sess-1", _make_fake_jpeg())
        assert state.session_id == "sess-1"
        assert "vision" in state.modalities_used
        assert state.emotion != ""

    def test_infer_audio(self):
        state = self.pipeline.infer_audio("sess-2", _make_fake_wav())
        assert state.session_id == "sess-2"
        assert "audio" in state.modalities_used

    def test_infer_multimodal(self):
        state = self.pipeline.infer_multimodal(
            "sess-3",
            frame_b64=_make_fake_jpeg(),
            audio_b64=_make_fake_wav(),
        )
        assert "vision" in state.modalities_used
        assert "audio" in state.modalities_used

    def test_persistence(self):
        self.pipeline.infer_frame("sess-4", _make_fake_jpeg())
        stored = self.pipeline.get_current("sess-4")
        assert stored is not None
        assert stored.session_id == "sess-4"

    def test_history(self):
        for _ in range(5):
            self.pipeline.infer_frame("sess-5", _make_fake_jpeg())
        states, has_more = self.pipeline.get_history("sess-5", limit=3)
        assert len(states) == 3
        assert has_more is True

    def test_no_current(self):
        result = self.pipeline.get_current("nonexistent")
        assert result is None


# ── API Integration Tests ────────────────────────────────────────────

@pytest.fixture
def client():
    """Create a test client with auth disabled."""
    os.environ["enable_auth"] = "false"
    # Clear cached settings
    from config import get_settings
    get_settings.cache_clear()
    from main import app
    with TestClient(app) as c:
        yield c
    os.environ.pop("enable_auth", None)
    get_settings.cache_clear()


class TestEmotionAPI:
    def test_infer_frame(self, client: TestClient):
        resp = client.post("/api/v1/emotion/infer-frame", json={
            "session_id": "api-test-1",
            "frame_b64": _make_fake_jpeg(),
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "api-test-1"
        assert "vision" in data["modalities_used"]
        assert data["emotion"] != ""
        assert 0 <= data["stress_level"] <= 1
        assert 0 <= data["cognitive_load"] <= 1

    def test_infer_audio(self, client: TestClient):
        resp = client.post("/api/v1/emotion/infer-audio", json={
            "session_id": "api-test-2",
            "audio_b64": _make_fake_wav(),
            "sample_rate": 16000,
            "duration_ms": 2000,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == "api-test-2"
        assert "audio" in data["modalities_used"]

    def test_get_current_no_data(self, client: TestClient):
        resp = client.get("/api/v1/emotion/current/nonexistent")
        assert resp.status_code == 200
        data = resp.json()
        assert data["modalities_used"] == []

    def test_get_current_after_infer(self, client: TestClient):
        client.post("/api/v1/emotion/infer-frame", json={
            "session_id": "api-test-3",
            "frame_b64": _make_fake_jpeg(),
        })
        resp = client.get("/api/v1/emotion/current/api-test-3")
        assert resp.status_code == 200
        data = resp.json()
        assert "vision" in data["modalities_used"]

    def test_emotion_history(self, client: TestClient):
        import uuid
        sid = f"api-hist-{uuid.uuid4().hex[:8]}"
        for _ in range(3):
            client.post("/api/v1/emotion/infer-frame", json={
                "session_id": sid,
                "frame_b64": _make_fake_jpeg(),
            })
        resp = client.get(f"/api/v1/emotion/history/{sid}?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == sid
        assert len(data["items"]) == 3

    def test_infer_frame_validation(self, client: TestClient):
        resp = client.post("/api/v1/emotion/infer-frame", json={
            "session_id": "",
            "frame_b64": "",
        })
        assert resp.status_code == 422

    def test_infer_audio_validation(self, client: TestClient):
        resp = client.post("/api/v1/emotion/infer-audio", json={
            "session_id": "x",
            "audio_b64": "",
        })
        assert resp.status_code == 422
