"""Tests for GDPR privacy: data export, deletion, and sensing controls."""

from __future__ import annotations

import os
import sys
import json
import sqlite3

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Disable auth for tests
os.environ["ENABLE_AUTH"] = "false"

from datetime import datetime, timezone
from fastapi.testclient import TestClient

from db.behavior_repository import BehaviorRepository
from models.behavior import BehaviorSnapshot
from models.memory import DailySummary, UserBehavioralProfile
from models.privacy import SensingState, SensingUpdate
from services.memory_service import MemoryService
from services.privacy_service import PrivacyService
from main import app

client = TestClient(app)


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture()
def repo(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    r = BehaviorRepository(db_url)
    r.initialize()
    return r


@pytest.fixture()
def service(repo):
    return PrivacyService(repo)


def _seed_full_user(repo, user_id: str = "user-1", session_id: str = "sess-1"):
    """Populate all tables with data for a user."""
    # Create session
    repo.create_session(session_id, user_id, "web")

    # Behavior snapshot
    snap = BehaviorSnapshot(
        session_id=session_id,
        typing_wpm=40.0, error_rate=0.1, hesitation_index=0.2,
        task_switches_per_minute=5.0, cognitive_load=0.5,
        frustration_score=0.3, attention_level=0.7,
        recommended_adaptation="resume_normal",
        sample_size=10, updated_at=datetime.now(timezone.utc),
    )
    repo.upsert(snap)

    # Profile
    profile = UserBehavioralProfile(
        user_id=user_id, peak_focus_hours=[9, 10],
        stress_triggers={"evening_sessions": 0.6},
        preferred_pace="normal", avg_cognitive_load=0.45, total_sessions=1,
    )
    repo.upsert_behavioral_profile(profile)

    # Daily summary
    summary = DailySummary(
        user_id=user_id, session_id=session_id, date="2026-05-09",
        avg_cognitive_load=0.45, avg_frustration=0.3, avg_attention=0.7,
        snapshot_count=1, dominant_adaptation="resume_normal",
    )
    repo.add_daily_summary(summary)

    # Sensing state
    state = SensingState(session_id=session_id)
    repo.upsert_sensing_state(state)


# ── Unit Tests: Data Export ──────────────────────────────────────────


class TestDataExport:
    def test_export_populated_user(self, repo, service):
        _seed_full_user(repo)
        result = service.export_user_data("user-1")
        assert result.user_id == "user-1"
        assert len(result.sessions) == 1
        assert len(result.behavior_snapshots) >= 1
        assert result.behavioral_profile is not None
        assert len(result.daily_summaries) == 1
        assert len(result.sensing_states) == 1
        assert result.total_records > 0

    def test_export_empty_user(self, repo, service):
        result = service.export_user_data("ghost")
        assert result.total_records == 0
        assert result.sessions == []
        assert result.behavioral_profile is None

    def test_export_multi_session_user(self, repo, service):
        _seed_full_user(repo, "user-multi", "s1")
        _seed_full_user(repo, "user-multi", "s2")
        result = service.export_user_data("user-multi")
        assert len(result.sessions) == 2
        assert len(result.behavior_snapshots) >= 2


# ── Unit Tests: Data Deletion ────────────────────────────────────────


class TestDataDeletion:
    def test_delete_populated_user(self, repo, service):
        _seed_full_user(repo)
        result = service.delete_all_user_data("user-1")
        assert result.deleted is True
        assert result.records_deleted["sessions"] == 1
        assert result.records_deleted["user_behavioral_profiles"] == 1
        assert result.records_deleted["session_daily_summaries"] == 1

        # Verify everything is gone
        assert repo.get_session("sess-1") is None
        assert repo.get_behavioral_profile("user-1") is None
        assert repo.get_daily_summaries("user-1") == []

    def test_delete_empty_user(self, repo, service):
        result = service.delete_all_user_data("ghost")
        assert result.deleted is False

    def test_delete_does_not_affect_others(self, repo, service):
        _seed_full_user(repo, "user-a", "s-a")
        _seed_full_user(repo, "user-b", "s-b")
        service.delete_all_user_data("user-a")

        # user-b still intact
        assert repo.get_session("s-b") is not None
        assert repo.get_behavioral_profile("user-b") is not None


# ── Unit Tests: Sensing State ────────────────────────────────────────


class TestSensingState:
    def test_get_default(self, service):
        state = service.get_sensing_state("new-session")
        assert state.session_id == "new-session"
        assert state.vision_enabled is True
        assert state.all_paused is False

    def test_update_single_modality(self, service):
        update = SensingUpdate(session_id="s1", vision_enabled=False)
        result = service.update_sensing_state(update)
        assert result.vision_enabled is False
        assert result.audio_enabled is True
        assert result.all_paused is False

    def test_pause_all(self, service):
        update = SensingUpdate(session_id="s1", all_paused=True)
        result = service.update_sensing_state(update)
        assert result.all_paused is True
        assert result.vision_enabled is False
        assert result.audio_enabled is False
        assert result.behavior_enabled is False

    def test_auto_detect_all_paused(self, service):
        service.update_sensing_state(SensingUpdate(session_id="s1", vision_enabled=False))
        service.update_sensing_state(SensingUpdate(session_id="s1", audio_enabled=False))
        result = service.update_sensing_state(SensingUpdate(session_id="s1", behavior_enabled=False))
        assert result.all_paused is True

    def test_resume_after_pause(self, service):
        service.update_sensing_state(SensingUpdate(session_id="s1", all_paused=True))
        result = service.update_sensing_state(SensingUpdate(session_id="s1", behavior_enabled=True))
        assert result.behavior_enabled is True
        assert result.all_paused is False

    def test_persistence(self, repo, service):
        service.update_sensing_state(SensingUpdate(session_id="s1", vision_enabled=False))
        stored = repo.get_sensing_state("s1")
        assert stored is not None
        assert stored.vision_enabled is False


# ── Integration Tests (API) ──────────────────────────────────────────


class TestExportAPI:
    def test_export_user(self):
        # Seed data via session + behavior endpoints
        r = client.post("/api/v1/session", json={"user_id": "export-user"})
        session_id = r.json()["session_id"]
        client.post("/api/v1/behavior/event", json={
            "session_id": session_id,
            "event": {"type": "keypress", "timestamp": 1.0, "metadata": {"key": "a"}},
        })

        resp = client.get("/api/v1/privacy/export/export-user")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "export-user"
        assert len(data["sessions"]) >= 1
        assert data["total_records"] >= 1

    def test_export_empty(self):
        resp = client.get("/api/v1/privacy/export/nobody")
        assert resp.status_code == 200
        assert resp.json()["total_records"] == 0


class TestDeleteAPI:
    def test_delete_user(self):
        r = client.post("/api/v1/session", json={"user_id": "delete-user"})
        session_id = r.json()["session_id"]
        client.post("/api/v1/behavior/event", json={
            "session_id": session_id,
            "event": {"type": "keypress", "timestamp": 1.0, "metadata": {"key": "x"}},
        })

        resp = client.delete("/api/v1/privacy/data/delete-user")
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted"] is True

        # Verify data is gone
        export = client.get("/api/v1/privacy/export/delete-user").json()
        assert export["sessions"] == []

    def test_delete_nonexistent(self):
        resp = client.delete("/api/v1/privacy/data/ghost-user")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is False


class TestSensingAPI:
    def test_get_default_state(self):
        resp = client.get("/api/v1/privacy/sensing/new-session-api")
        assert resp.status_code == 200
        data = resp.json()
        assert data["vision_enabled"] is True
        assert data["all_paused"] is False

    def test_update_sensing(self):
        resp = client.put("/api/v1/privacy/sensing", json={
            "session_id": "sense-sess-1", "vision_enabled": False,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["vision_enabled"] is False
        assert data["audio_enabled"] is True

    def test_pause_all(self):
        resp = client.put("/api/v1/privacy/sensing", json={
            "session_id": "sense-sess-2", "all_paused": True,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["all_paused"] is True
        assert data["vision_enabled"] is False

    def test_validation(self):
        resp = client.put("/api/v1/privacy/sensing", json={
            "session_id": "", "vision_enabled": False,
        })
        assert resp.status_code == 422
