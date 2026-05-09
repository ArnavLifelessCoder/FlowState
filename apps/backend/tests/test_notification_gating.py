"""Tests for notification gating: unit + integration."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Disable auth for tests
os.environ["ENABLE_AUTH"] = "false"

from datetime import datetime, timezone
from fastapi.testclient import TestClient

from db.behavior_repository import BehaviorRepository
from models.behavior import BehaviorSnapshot
from models.notification import GateDecision, GatingPolicy, NotificationPriority, NotificationRequest
from services.behavior_session_service import BehaviorSessionService
from services.notification_gating_service import NotificationGatingService
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
def bss(repo):
    return BehaviorSessionService(repository=repo, window_size=100)


@pytest.fixture()
def service(bss):
    return NotificationGatingService(behavior_sessions=bss)


def _make_request(
    session_id: str = "s1",
    priority: str = "normal",
    title: str = "Test Notification",
) -> NotificationRequest:
    return NotificationRequest(
        session_id=session_id,
        title=title,
        priority=NotificationPriority(priority),
    )


def _seed_snapshot(bss, session_id: str, cognitive_load: float, frustration: float, attention: float):
    """Seed a behavior snapshot to simulate cognitive state."""
    snap = BehaviorSnapshot(
        session_id=session_id,
        typing_wpm=45.0, error_rate=0.1, hesitation_index=0.1,
        task_switches_per_minute=5.0,
        cognitive_load=cognitive_load,
        frustration_score=frustration,
        attention_level=attention,
        recommended_adaptation="resume_normal",
        sample_size=10, updated_at=datetime.now(timezone.utc),
    )
    bss._repository.upsert(snap)
    return snap


# ── Unit Tests: Gate Decisions ───────────────────────────────────────


class TestGateDecisions:
    def test_deliver_when_calm(self, bss, service):
        _seed_snapshot(bss, "s1", cognitive_load=0.3, frustration=0.2, attention=0.5)
        result = service.evaluate(_make_request("s1"))
        assert result.decision == GateDecision.DELIVER
        assert "permits delivery" in result.reason

    def test_suppress_high_cognitive_load(self, bss, service):
        _seed_snapshot(bss, "s1", cognitive_load=0.8, frustration=0.3, attention=0.5)
        result = service.evaluate(_make_request("s1"))
        assert result.decision == GateDecision.SUPPRESS
        assert "cognitive load" in result.reason

    def test_suppress_high_frustration(self, bss, service):
        _seed_snapshot(bss, "s1", cognitive_load=0.3, frustration=0.75, attention=0.5)
        result = service.evaluate(_make_request("s1"))
        assert result.decision == GateDecision.SUPPRESS
        assert "frustration" in result.reason

    def test_queue_deep_focus(self, bss, service):
        _seed_snapshot(bss, "s1", cognitive_load=0.6, frustration=0.2, attention=0.85)
        result = service.evaluate(_make_request("s1"))
        assert result.decision == GateDecision.QUEUE
        assert "deep focus" in result.reason

    def test_queue_low_priority_moderate_load(self, bss, service):
        _seed_snapshot(bss, "s1", cognitive_load=0.6, frustration=0.2, attention=0.5)
        result = service.evaluate(_make_request("s1", priority="low"))
        assert result.decision == GateDecision.QUEUE

    def test_deliver_high_priority_moderate_load(self, bss, service):
        _seed_snapshot(bss, "s1", cognitive_load=0.6, frustration=0.2, attention=0.5)
        result = service.evaluate(_make_request("s1", priority="high"))
        assert result.decision == GateDecision.DELIVER
        assert "high priority" in result.reason

    def test_critical_bypasses_gate(self, bss, service):
        _seed_snapshot(bss, "s1", cognitive_load=0.9, frustration=0.9, attention=0.1)
        result = service.evaluate(_make_request("s1", priority="critical"))
        assert result.decision == GateDecision.DELIVER
        assert "critical" in result.reason

    def test_critical_bypass_configurable(self, bss):
        policy = GatingPolicy(always_deliver_critical=False)
        svc = NotificationGatingService(behavior_sessions=bss, policy=policy)
        _seed_snapshot(bss, "s1", cognitive_load=0.9, frustration=0.3, attention=0.5)
        result = svc.evaluate(_make_request("s1", priority="critical"))
        assert result.decision == GateDecision.SUPPRESS


# ── Unit Tests: Queue Management ─────────────────────────────────────


class TestQueueManagement:
    def test_queued_notifications_stored(self, bss, service):
        _seed_snapshot(bss, "s1", cognitive_load=0.6, frustration=0.2, attention=0.85)
        service.evaluate(_make_request("s1"))
        queue = service.get_queued("s1")
        assert queue.total == 1
        assert queue.queued[0].notification.title == "Test Notification"

    def test_flush_marks_delivered(self, bss, service):
        _seed_snapshot(bss, "s1", cognitive_load=0.6, frustration=0.2, attention=0.85)
        service.evaluate(_make_request("s1", title="N1"))
        service.evaluate(_make_request("s1", title="N2"))
        flushed = service.flush_queue("s1")
        assert len(flushed) == 2
        assert all(f.delivered for f in flushed)
        assert all(f.delivered_at is not None for f in flushed)

        # Queue should be empty now
        queue = service.get_queued("s1", pending_only=True)
        assert queue.total == 0

    def test_flush_empty_queue(self, service):
        flushed = service.flush_queue("empty-session")
        assert flushed == []

    def test_pending_only_filter(self, bss, service):
        _seed_snapshot(bss, "s1", cognitive_load=0.6, frustration=0.2, attention=0.85)
        service.evaluate(_make_request("s1", title="N1"))
        service.flush_queue("s1")
        service.evaluate(_make_request("s1", title="N2"))

        all_items = service.get_queued("s1", pending_only=False)
        pending = service.get_queued("s1", pending_only=True)
        assert all_items.total == 2
        assert pending.total == 1


# ── Unit Tests: Stats ────────────────────────────────────────────────


class TestNotificationStats:
    def test_stats_tracking(self, bss, service):
        _seed_snapshot(bss, "s1", cognitive_load=0.3, frustration=0.2, attention=0.5)
        service.evaluate(_make_request("s1"))  # deliver

        _seed_snapshot(bss, "s1", cognitive_load=0.6, frustration=0.2, attention=0.85)
        service.evaluate(_make_request("s1"))  # queue

        _seed_snapshot(bss, "s1", cognitive_load=0.8, frustration=0.3, attention=0.5)
        service.evaluate(_make_request("s1"))  # suppress

        stats = service.get_stats("s1")
        assert stats.total_evaluated == 3
        assert stats.delivered == 1
        assert stats.queued == 1
        assert stats.suppressed == 1

    def test_stats_empty_session(self, service):
        stats = service.get_stats("nonexistent")
        assert stats.total_evaluated == 0


# ── Unit Tests: Policy ───────────────────────────────────────────────


class TestGatingPolicy:
    def test_custom_thresholds(self, bss):
        policy = GatingPolicy(suppress_cognitive_load=0.5, suppress_frustration=0.4)
        svc = NotificationGatingService(behavior_sessions=bss, policy=policy)
        _seed_snapshot(bss, "s1", cognitive_load=0.55, frustration=0.2, attention=0.5)
        result = svc.evaluate(_make_request("s1"))
        assert result.decision == GateDecision.SUPPRESS

    def test_update_policy(self, service):
        new_policy = GatingPolicy(suppress_cognitive_load=0.9, suppress_frustration=0.9)
        updated = service.update_policy(new_policy)
        assert updated.suppress_cognitive_load == 0.9

    def test_get_policy(self, service):
        policy = service.get_policy()
        assert policy.suppress_cognitive_load == 0.75  # default


# ── Integration Tests (API) ──────────────────────────────────────────


def _ingest_for_state(session_id: str, count: int = 5):
    """Ingest events to create a session with a snapshot."""
    for i in range(count):
        client.post("/api/v1/behavior/event", json={
            "session_id": session_id,
            "event": {"type": "keypress", "timestamp": 1.0 + i * 0.5, "metadata": {"key": "a"}},
        })


class TestEvaluateAPI:
    def test_evaluate_notification(self):
        _ingest_for_state("notif-sess-1")
        resp = client.post("/api/v1/notifications/evaluate", json={
            "session_id": "notif-sess-1",
            "title": "New message",
            "priority": "normal",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["decision"] in ["deliver", "queue", "suppress"]
        assert "cognitive_load" in data

    def test_evaluate_critical(self):
        _ingest_for_state("notif-sess-2")
        resp = client.post("/api/v1/notifications/evaluate", json={
            "session_id": "notif-sess-2",
            "title": "Server down!",
            "priority": "critical",
        })
        assert resp.status_code == 200
        assert resp.json()["decision"] == "deliver"

    def test_evaluate_validation(self):
        resp = client.post("/api/v1/notifications/evaluate", json={
            "session_id": "",
            "title": "Bad",
        })
        assert resp.status_code == 422


class TestQueueAPI:
    def test_get_queue(self):
        resp = client.get("/api/v1/notifications/queue/some-session")
        assert resp.status_code == 200
        assert resp.json()["total"] >= 0

    def test_flush_queue(self):
        resp = client.post("/api/v1/notifications/queue/some-session/flush")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestStatsAPI:
    def test_get_stats(self):
        resp = client.get("/api/v1/notifications/stats/some-session")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_evaluated" in data
        assert "delivered" in data


class TestPolicyAPI:
    def test_get_policy(self):
        resp = client.get("/api/v1/notifications/policy")
        assert resp.status_code == 200
        data = resp.json()
        assert "suppress_cognitive_load" in data

    def test_update_policy(self):
        resp = client.put("/api/v1/notifications/policy", json={
            "suppress_cognitive_load": 0.85,
            "suppress_frustration": 0.80,
        })
        assert resp.status_code == 200
        assert resp.json()["suppress_cognitive_load"] == 0.85
