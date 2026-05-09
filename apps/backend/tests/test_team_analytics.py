"""Tests for enterprise team analytics: unit + integration."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["ENABLE_AUTH"] = "false"

from datetime import datetime, timezone
from fastapi.testclient import TestClient

from db.behavior_repository import BehaviorRepository
from models.behavior import BehaviorSnapshot
from models.memory import UserBehavioralProfile
from models.team import TeamCreateRequest
from services.team_analytics_service import TeamAnalyticsService
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
    return TeamAnalyticsService(repo)


def _seed_user(repo, user_id: str, session_id: str, load: float = 0.5, frust: float = 0.3, att: float = 0.7):
    """Create a session and snapshot for a user."""
    repo.create_session(session_id, user_id, "web")
    snap = BehaviorSnapshot(
        session_id=session_id,
        typing_wpm=45.0, error_rate=0.1, hesitation_index=0.1,
        task_switches_per_minute=5.0,
        cognitive_load=load, frustration_score=frust, attention_level=att,
        recommended_adaptation="resume_normal",
        sample_size=10, updated_at=datetime.now(timezone.utc),
    )
    repo.upsert(snap)


def _seed_profile(repo, user_id: str, peak_hours=None, triggers=None):
    profile = UserBehavioralProfile(
        user_id=user_id,
        peak_focus_hours=peak_hours or [9, 10],
        stress_triggers=triggers or {"evening_sessions": 0.65},
        preferred_pace="normal",
        avg_cognitive_load=0.5,
        total_sessions=1,
    )
    repo.upsert_behavioral_profile(profile)


# ── Unit Tests: Team CRUD ────────────────────────────────────────────


class TestTeamCRUD:
    def test_create_team(self, repo, service):
        _seed_user(repo, "u1", "s1")
        _seed_user(repo, "u2", "s2")
        result = service.create_team(TeamCreateRequest(team_id="team-1", user_ids=["u1", "u2"]))
        assert result.team_id == "team-1"
        assert result.member_count == 2

    def test_list_teams(self, repo, service):
        _seed_user(repo, "u1", "s1")
        service.create_team(TeamCreateRequest(team_id="t1", user_ids=["u1"]))
        service.create_team(TeamCreateRequest(team_id="t2", user_ids=["u1"]))
        result = service.list_teams()
        assert result.total == 2
        assert "t1" in result.teams

    def test_delete_team(self, repo, service):
        _seed_user(repo, "u1", "s1")
        service.create_team(TeamCreateRequest(team_id="t1", user_ids=["u1"]))
        assert service.delete_team("t1") is True
        assert service.delete_team("t1") is False

    def test_deduplicates_user_ids(self, repo, service):
        _seed_user(repo, "u1", "s1")
        result = service.create_team(TeamCreateRequest(team_id="t1", user_ids=["u1", "u1", "u1"]))
        assert result.member_count == 1


# ── Unit Tests: Analytics ────────────────────────────────────────────


class TestTeamAnalytics:
    def test_aggregate_metrics(self, repo, service):
        _seed_user(repo, "u1", "s1", load=0.4, frust=0.2, att=0.8)
        _seed_user(repo, "u2", "s2", load=0.6, frust=0.4, att=0.6)
        service.create_team(TeamCreateRequest(team_id="t1", user_ids=["u1", "u2"]))

        result = service.get_analytics("t1")
        assert result.aggregate.member_count == 2
        assert result.aggregate.total_sessions == 2
        assert 0.4 <= result.aggregate.avg_cognitive_load <= 0.6
        assert len(result.members) == 2

    def test_anonymized_ids(self, repo, service):
        _seed_user(repo, "u1", "s1")
        service.create_team(TeamCreateRequest(team_id="t1", user_ids=["u1"]))
        result = service.get_analytics("t1")
        member = result.members[0]
        assert member.anonymous_id != "u1"
        assert len(member.anonymous_id) == 12

    def test_burnout_risk_detection(self, repo, service):
        _seed_user(repo, "u1", "s1", load=0.7, frust=0.6, att=0.3)
        _seed_user(repo, "u2", "s2", load=0.3, frust=0.2, att=0.8)
        service.create_team(TeamCreateRequest(team_id="t1", user_ids=["u1", "u2"]))

        result = service.get_analytics("t1")
        assert result.aggregate.burnout_risk_count == 1

    def test_stress_hotspots(self, repo, service):
        _seed_user(repo, "u1", "s1")
        _seed_profile(repo, "u1", triggers={"evening_sessions": 0.7, "high_task_switching": 0.8})
        _seed_user(repo, "u2", "s2")
        _seed_profile(repo, "u2", triggers={"evening_sessions": 0.65})
        service.create_team(TeamCreateRequest(team_id="t1", user_ids=["u1", "u2"]))

        result = service.get_analytics("t1")
        assert "evening_sessions" in result.aggregate.stress_hotspots
        assert "high_task_switching" in result.aggregate.stress_hotspots

    def test_empty_team(self, service):
        result = service.get_analytics("nonexistent")
        assert result.aggregate.member_count == 0

    def test_peak_hours_from_profile(self, repo, service):
        _seed_user(repo, "u1", "s1")
        _seed_profile(repo, "u1", peak_hours=[9, 10, 14])
        service.create_team(TeamCreateRequest(team_id="t1", user_ids=["u1"]))

        result = service.get_analytics("t1")
        assert result.members[0].peak_focus_hours == [9, 10, 14]


# ── Integration Tests (API) ──────────────────────────────────────────


def _api_seed_user(user_id: str):
    """Create a session and ingest events via the API."""
    r = client.post("/api/v1/session", json={"user_id": user_id})
    session_id = r.json()["session_id"]
    for i in range(3):
        client.post("/api/v1/behavior/event", json={
            "session_id": session_id,
            "event": {"type": "keypress", "timestamp": 1.0 + i * 0.5, "metadata": {"key": "a"}},
        })
    return session_id


class TestTeamCreateAPI:
    def test_create_team(self):
        _api_seed_user("team-api-u1")
        _api_seed_user("team-api-u2")
        resp = client.post("/api/v1/teams", json={
            "team_id": "api-team-1",
            "user_ids": ["team-api-u1", "team-api-u2"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["team_id"] == "api-team-1"
        assert data["member_count"] == 2

    def test_create_validation(self):
        resp = client.post("/api/v1/teams", json={
            "team_id": "",
            "user_ids": ["u1"],
        })
        assert resp.status_code == 422


class TestTeamListAPI:
    def test_list_teams(self):
        resp = client.get("/api/v1/teams")
        assert resp.status_code == 200
        assert "teams" in resp.json()


class TestTeamAnalyticsAPI:
    def test_get_analytics(self):
        _api_seed_user("team-api-u3")
        client.post("/api/v1/teams", json={
            "team_id": "api-team-analytics",
            "user_ids": ["team-api-u3"],
        })
        resp = client.get("/api/v1/teams/api-team-analytics")
        assert resp.status_code == 200
        data = resp.json()
        assert data["aggregate"]["member_count"] == 1
        assert len(data["members"]) == 1
        assert data["members"][0]["anonymous_id"] != "team-api-u3"

    def test_get_nonexistent(self):
        resp = client.get("/api/v1/teams/ghost-team")
        assert resp.status_code == 404


class TestTeamDeleteAPI:
    def test_delete_team(self):
        client.post("/api/v1/teams", json={
            "team_id": "api-team-del",
            "user_ids": ["some-user"],
        })
        resp = client.delete("/api/v1/teams/api-team-del")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    def test_delete_nonexistent(self):
        resp = client.delete("/api/v1/teams/ghost-team")
        assert resp.status_code == 404
