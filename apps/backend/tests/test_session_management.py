"""Tests for session management: unit + integration."""

from __future__ import annotations

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Disable auth for tests
os.environ["ENABLE_AUTH"] = "false"

from fastapi.testclient import TestClient

from db.behavior_repository import BehaviorRepository
from models.memory import DailySummaryIn
from models.session import SessionCreate
from services.memory_service import MemoryService
from services.session_management_service import SessionManagementService
from main import app

client = TestClient(app)


# ── Unit Tests ───────────────────────────────────────────────────────


@pytest.fixture()
def repo(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    r = BehaviorRepository(db_url)
    r.initialize()
    return r


@pytest.fixture()
def mem_service(repo):
    return MemoryService(repo)


@pytest.fixture()
def service(repo, mem_service):
    return SessionManagementService(repository=repo, memory_service=mem_service)


class TestSessionCreateUnit:
    def test_creates_session(self, service):
        payload = SessionCreate(user_id="user-1", platform="web")
        record = service.create_session(payload)
        assert record.user_id == "user-1"
        assert record.platform == "web"
        assert record.is_active is True
        assert record.ended_at is None
        assert len(record.session_id) > 0

    def test_unique_session_ids(self, service):
        payload = SessionCreate(user_id="user-1")
        r1 = service.create_session(payload)
        r2 = service.create_session(payload)
        assert r1.session_id != r2.session_id


class TestSessionEndUnit:
    def test_end_active_session(self, service):
        payload = SessionCreate(user_id="user-1")
        created = service.create_session(payload)
        result = service.end_session(created.session_id)
        assert result is not None
        assert result.session_id == created.session_id
        assert result.duration_seconds >= 0
        assert result.daily_summary_generated is True

    def test_end_nonexistent_session(self, service):
        result = service.end_session("ghost-session")
        assert result is None

    def test_end_already_ended_session(self, service):
        payload = SessionCreate(user_id="user-1")
        created = service.create_session(payload)
        service.end_session(created.session_id)
        result = service.end_session(created.session_id)
        assert result is None


class TestSessionGetUnit:
    def test_get_existing(self, service):
        payload = SessionCreate(user_id="user-1")
        created = service.create_session(payload)
        found = service.get_session(created.session_id)
        assert found is not None
        assert found.session_id == created.session_id

    def test_get_nonexistent(self, service):
        assert service.get_session("nope") is None


class TestSessionListUnit:
    def test_list_by_user(self, service):
        for _ in range(3):
            service.create_session(SessionCreate(user_id="user-list"))
        service.create_session(SessionCreate(user_id="other-user"))

        result = service.list_sessions("user-list")
        assert result.total == 3
        assert all(s.user_id == "user-list" for s in result.sessions)

    def test_list_active_only(self, service):
        s1 = service.create_session(SessionCreate(user_id="user-active"))
        s2 = service.create_session(SessionCreate(user_id="user-active"))
        service.end_session(s1.session_id)

        result = service.list_sessions("user-active", active_only=True)
        assert result.total == 1
        assert result.sessions[0].session_id == s2.session_id

    def test_list_empty(self, service):
        result = service.list_sessions("nobody")
        assert result.total == 0


class TestSessionIdsForUser:
    def test_returns_user_sessions(self, repo, service):
        service.create_session(SessionCreate(user_id="u1"))
        service.create_session(SessionCreate(user_id="u1"))
        service.create_session(SessionCreate(user_id="u2"))

        ids = repo.get_session_ids_for_user("u1")
        assert len(ids) == 2

        ids2 = repo.get_session_ids_for_user("u2")
        assert len(ids2) == 1


class TestAutoSummaryOnEnd:
    def test_daily_summary_generated(self, repo, service, mem_service):
        """Ending a session should auto-generate a daily summary."""
        # Create and ingest some behavior data
        import json, sqlite3
        from models.behavior import BehaviorSnapshot
        from datetime import datetime, timezone

        created = service.create_session(SessionCreate(user_id="user-summary"))
        snap = BehaviorSnapshot(
            session_id=created.session_id,
            typing_wpm=40.0, error_rate=0.1, hesitation_index=0.2,
            task_switches_per_minute=5.0, cognitive_load=0.5,
            frustration_score=0.3, attention_level=0.7,
            recommended_adaptation="resume_normal",
            sample_size=10, updated_at=datetime.now(timezone.utc),
        )
        repo.upsert(snap)

        result = service.end_session(created.session_id)
        assert result is not None
        assert result.daily_summary_generated is True

        summaries = repo.get_daily_summaries("user-summary", days=7)
        assert len(summaries) == 1


# ── Integration Tests (API) ──────────────────────────────────────────


class TestSessionCreateAPI:
    def test_create_session(self):
        resp = client.post(
            "/api/v1/session",
            json={"user_id": "api-user-1", "platform": "web"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "api-user-1"
        assert data["is_active"] is True

    def test_create_session_validation(self):
        resp = client.post(
            "/api/v1/session",
            json={"user_id": "", "platform": "web"},
        )
        assert resp.status_code == 422


class TestSessionGetAPI:
    def test_get_existing(self):
        create_resp = client.post(
            "/api/v1/session",
            json={"user_id": "api-user-get"},
        )
        session_id = create_resp.json()["session_id"]

        resp = client.get(f"/api/v1/session/{session_id}")
        assert resp.status_code == 200
        assert resp.json()["session_id"] == session_id

    def test_get_nonexistent(self):
        resp = client.get("/api/v1/session/doesnt-exist")
        assert resp.status_code == 404


class TestSessionEndAPI:
    def test_end_session(self):
        create_resp = client.post(
            "/api/v1/session",
            json={"user_id": "api-user-end"},
        )
        session_id = create_resp.json()["session_id"]

        resp = client.post(f"/api/v1/session/{session_id}/end")
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == session_id
        assert data["duration_seconds"] >= 0

    def test_end_nonexistent(self):
        resp = client.post("/api/v1/session/ghost/end")
        assert resp.status_code == 404


class TestSessionListAPI:
    def test_list_user_sessions(self):
        for _ in range(2):
            client.post(
                "/api/v1/session",
                json={"user_id": "api-user-list"},
            )

        resp = client.get("/api/v1/session/user/api-user-list")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 2

    def test_list_active_only(self):
        import uuid
        uid = f"api-active-{uuid.uuid4().hex[:8]}"
        r1 = client.post(
            "/api/v1/session",
            json={"user_id": uid},
        )
        r2 = client.post(
            "/api/v1/session",
            json={"user_id": uid},
        )
        # End one
        client.post(f"/api/v1/session/{r1.json()['session_id']}/end")

        resp = client.get(
            f"/api/v1/session/user/{uid}",
            params={"active_only": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["sessions"][0]["session_id"] == r2.json()["session_id"]


class TestHealthEndpoint:
    def test_health(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
