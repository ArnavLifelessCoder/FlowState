"""Unit tests for the MemoryService."""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timezone, timedelta

import pytest

# Ensure the backend package is importable.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db.behavior_repository import BehaviorRepository
from models.behavior import BehaviorSnapshot
from models.memory import DailySummary, DailySummaryIn, UserBehavioralProfile
from services.memory_service import MemoryService


@pytest.fixture()
def repo(tmp_path):
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    r = BehaviorRepository(db_url)
    r.initialize()
    return r


@pytest.fixture()
def service(repo):
    return MemoryService(repo)


def _make_snapshot(
    session_id: str = "sess-1",
    cognitive_load: float = 0.5,
    frustration: float = 0.3,
    attention: float = 0.7,
    adaptation: str = "resume_normal",
    ts: datetime | None = None,
    error_rate: float = 0.05,
    task_switches: float = 5.0,
) -> BehaviorSnapshot:
    return BehaviorSnapshot(
        session_id=session_id,
        typing_wpm=45.0,
        error_rate=error_rate,
        hesitation_index=0.1,
        task_switches_per_minute=task_switches,
        cognitive_load=cognitive_load,
        frustration_score=frustration,
        attention_level=attention,
        recommended_adaptation=adaptation,
        sample_size=100,
        updated_at=ts or datetime.now(timezone.utc),
    )


def _seed_snapshots(repo, snapshots: list[BehaviorSnapshot], timestamps: list[str] | None = None):
    """Insert snapshots directly into the DB for testing."""
    import json, sqlite3
    for i, snap in enumerate(snapshots):
        ts = timestamps[i] if timestamps else snap.updated_at.isoformat()
        with sqlite3.connect(repo._db_path) as conn:
            conn.execute(
                "INSERT INTO behavior_snapshots(session_id, metrics_json, created_at) VALUES (?, ?, ?)",
                (snap.session_id, json.dumps(snap.model_dump(mode="json")), ts),
            )
            conn.execute(
                """INSERT INTO behavior_sessions(session_id, metrics_json, sample_size, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(session_id) DO UPDATE SET
                       metrics_json=excluded.metrics_json,
                       sample_size=excluded.sample_size,
                       updated_at=excluded.updated_at""",
                (snap.session_id, json.dumps(snap.model_dump(mode="json")), snap.sample_size, ts),
            )
            conn.commit()


# ── Profile Building ─────────────────────────────────────────────────


class TestBuildProfile:
    def test_empty_sessions(self, service):
        result = service.build_profile("user-1", ["nonexistent"])
        assert result.user_id == "user-1"
        assert result.sessions_analyzed == 0
        assert result.profile.total_sessions == 1

    def test_single_session(self, repo, service):
        snaps = [
            _make_snapshot("s1", cognitive_load=0.3, frustration=0.2, attention=0.8),
            _make_snapshot("s1", cognitive_load=0.4, frustration=0.3, attention=0.7),
        ]
        _seed_snapshots(repo, snaps)
        result = service.build_profile("user-1", ["s1"])
        assert result.sessions_analyzed == 1
        assert result.profile.avg_cognitive_load == pytest.approx(0.35, abs=0.01)

    def test_multiple_sessions(self, repo, service):
        snaps = [
            _make_snapshot("s1", cognitive_load=0.3),
            _make_snapshot("s2", cognitive_load=0.5),
        ]
        _seed_snapshots(repo, snaps)
        result = service.build_profile("user-1", ["s1", "s2"])
        assert result.sessions_analyzed == 2
        assert result.profile.avg_cognitive_load == pytest.approx(0.4, abs=0.01)

    def test_profile_persisted(self, repo, service):
        snaps = [_make_snapshot("s1")]
        _seed_snapshots(repo, snaps)
        service.build_profile("user-1", ["s1"])
        stored = repo.get_behavioral_profile("user-1")
        assert stored is not None
        assert stored.user_id == "user-1"


# ── Peak Focus Hours ─────────────────────────────────────────────────


class TestPeakFocusHours:
    def test_detects_low_load_hours(self, repo, service):
        now = datetime.now(timezone.utc)
        snaps = []
        timestamps = []
        # Morning: low cognitive load
        for i in range(5):
            ts = now.replace(hour=9, minute=i * 10, second=0, microsecond=0)
            snaps.append(_make_snapshot("s1", cognitive_load=0.2, ts=ts))
            timestamps.append(ts.isoformat())
        # Afternoon: high cognitive load
        for i in range(5):
            ts = now.replace(hour=15, minute=i * 10, second=0, microsecond=0)
            snaps.append(_make_snapshot("s1", cognitive_load=0.8, ts=ts))
            timestamps.append(ts.isoformat())
        _seed_snapshots(repo, snaps, timestamps)
        result = service.build_profile("user-1", ["s1"])
        assert 9 in result.profile.peak_focus_hours
        assert 15 not in result.profile.peak_focus_hours


# ── Stress Triggers ──────────────────────────────────────────────────


class TestStressTriggers:
    def test_detects_evening_stress(self, repo, service):
        now = datetime.now(timezone.utc)
        snaps = []
        timestamps = []
        # Evening: high frustration
        for i in range(5):
            ts = now.replace(hour=21, minute=i * 10, second=0, microsecond=0)
            snaps.append(_make_snapshot("s1", frustration=0.8, ts=ts))
            timestamps.append(ts.isoformat())
        # Morning: low frustration
        for i in range(5):
            ts = now.replace(hour=9, minute=i * 10, second=0, microsecond=0)
            snaps.append(_make_snapshot("s1", frustration=0.1, ts=ts))
            timestamps.append(ts.isoformat())
        _seed_snapshots(repo, snaps, timestamps)
        result = service.build_profile("user-1", ["s1"])
        assert "evening_sessions" in result.profile.stress_triggers
        assert result.profile.stress_triggers["evening_sessions"] > 0.5

    def test_detects_high_task_switching(self, repo, service):
        now = datetime.now(timezone.utc)
        snaps = [
            _make_snapshot("s1", frustration=0.7, task_switches=25.0, ts=now),
            _make_snapshot("s1", frustration=0.6, task_switches=20.0, ts=now),
        ]
        _seed_snapshots(repo, snaps, [now.isoformat()] * 2)
        result = service.build_profile("user-1", ["s1"])
        assert "high_task_switching" in result.profile.stress_triggers

    def test_detects_high_error_rate(self, repo, service):
        now = datetime.now(timezone.utc)
        snaps = [
            _make_snapshot("s1", frustration=0.6, error_rate=0.3, ts=now),
            _make_snapshot("s1", frustration=0.5, error_rate=0.25, ts=now),
        ]
        _seed_snapshots(repo, snaps, [now.isoformat()] * 2)
        result = service.build_profile("user-1", ["s1"])
        assert "high_error_rate" in result.profile.stress_triggers


# ── Preferred Pace ───────────────────────────────────────────────────


class TestPreferredPace:
    def test_slow_pace(self, repo, service):
        snaps = [
            _make_snapshot("s1", adaptation="reduce_ui_complexity"),
            _make_snapshot("s1", adaptation="pause_notifications"),
            _make_snapshot("s1", adaptation="resume_normal"),
        ]
        _seed_snapshots(repo, snaps)
        result = service.build_profile("user-1", ["s1"])
        assert result.profile.preferred_pace == "slow"

    def test_fast_pace(self, repo, service):
        snaps = [
            _make_snapshot("s1", adaptation="increase_ui_complexity"),
            _make_snapshot("s1", adaptation="enable_power_features"),
            _make_snapshot("s1", adaptation="resume_normal"),
        ]
        _seed_snapshots(repo, snaps)
        result = service.build_profile("user-1", ["s1"])
        assert result.profile.preferred_pace == "fast"


# ── Daily Summary ────────────────────────────────────────────────────


class TestDailySummary:
    def test_record_and_retrieve(self, repo, service):
        snaps = [
            _make_snapshot("s1", cognitive_load=0.4, frustration=0.2, attention=0.8),
            _make_snapshot("s1", cognitive_load=0.6, frustration=0.4, attention=0.6),
        ]
        _seed_snapshots(repo, snaps)
        payload = DailySummaryIn(user_id="user-1", session_id="s1", date="2026-05-09")
        summary = service.record_daily_summary(payload)
        assert summary.snapshot_count == 2
        assert summary.avg_cognitive_load == pytest.approx(0.5, abs=0.01)

        stored = repo.get_daily_summaries("user-1", days=7)
        assert len(stored) == 1
        assert stored[0].date == "2026-05-09"

    def test_empty_session(self, service):
        payload = DailySummaryIn(user_id="user-1", session_id="empty", date="2026-05-09")
        summary = service.record_daily_summary(payload)
        assert summary.snapshot_count == 0


# ── Proactive Suggestions ───────────────────────────────────────────


class TestProactiveSuggestions:
    def test_streak_stress(self, repo, service):
        for i in range(4):
            date_str = f"2026-05-{6 + i:02d}"
            summary = DailySummary(
                user_id="user-1",
                session_id=f"s{i}",
                date=date_str,
                avg_cognitive_load=0.5,
                avg_frustration=0.7,
                avg_attention=0.4,
                snapshot_count=10,
                dominant_adaptation="pause_notifications",
            )
            repo.add_daily_summary(summary)

        suggestions = service.get_suggestions_only("user-1")
        types = [s.type for s in suggestions]
        assert "streak_stress" in types
        streak_suggestion = next(s for s in suggestions if s.type == "streak_stress")
        assert streak_suggestion.data["consecutive_days"] == 4
        assert streak_suggestion.severity == "critical"

    def test_burnout_risk(self, repo, service):
        # Increasing cognitive load over 5 days
        for i in range(5):
            date_str = f"2026-05-{5 + i:02d}"
            summary = DailySummary(
                user_id="user-1",
                session_id=f"s{i}",
                date=date_str,
                avg_cognitive_load=0.3 + i * 0.1,
                avg_frustration=0.3,
                avg_attention=0.7,
                snapshot_count=10,
                dominant_adaptation="resume_normal",
            )
            repo.add_daily_summary(summary)

        suggestions = service.get_suggestions_only("user-1")
        types = [s.type for s in suggestions]
        assert "burnout_risk" in types

    def test_optimal_time_suggestion(self, repo, service):
        profile = UserBehavioralProfile(
            user_id="user-1",
            peak_focus_hours=[9, 10, 11],
            stress_triggers={},
            preferred_pace="normal",
            avg_cognitive_load=0.4,
            total_sessions=5,
        )
        repo.upsert_behavioral_profile(profile)
        # Need at least one daily summary for suggestions to run
        summary = DailySummary(
            user_id="user-1", session_id="s1", date="2026-05-09",
            avg_cognitive_load=0.4, avg_frustration=0.3, avg_attention=0.7,
            snapshot_count=10, dominant_adaptation="resume_normal",
        )
        repo.add_daily_summary(summary)

        suggestions = service.get_suggestions_only("user-1")
        types = [s.type for s in suggestions]
        assert "optimal_time" in types

    def test_stress_trigger_suggestion(self, repo, service):
        profile = UserBehavioralProfile(
            user_id="user-1",
            peak_focus_hours=[],
            stress_triggers={"evening_sessions": 0.75},
            preferred_pace="normal",
            avg_cognitive_load=0.5,
            total_sessions=3,
        )
        repo.upsert_behavioral_profile(profile)
        summary = DailySummary(
            user_id="user-1", session_id="s1", date="2026-05-09",
            avg_cognitive_load=0.5, avg_frustration=0.4, avg_attention=0.6,
            snapshot_count=10, dominant_adaptation="resume_normal",
        )
        repo.add_daily_summary(summary)

        suggestions = service.get_suggestions_only("user-1")
        types = [s.type for s in suggestions]
        assert "stress_trigger" in types

    def test_no_suggestions_when_empty(self, service):
        suggestions = service.get_suggestions_only("user-empty")
        assert suggestions == []


# ── Profile Deletion ─────────────────────────────────────────────────


class TestProfileDeletion:
    def test_delete_existing(self, repo, service):
        profile = UserBehavioralProfile(
            user_id="user-1", peak_focus_hours=[9],
            stress_triggers={}, preferred_pace="normal",
            avg_cognitive_load=0.4, total_sessions=1,
        )
        repo.upsert_behavioral_profile(profile)
        result = service.delete_profile("user-1")
        assert result.deleted is True
        assert repo.get_behavioral_profile("user-1") is None

    def test_delete_nonexistent(self, service):
        result = service.delete_profile("ghost")
        assert result.deleted is False


# ── Full Memory Response ─────────────────────────────────────────────


class TestFullMemory:
    def test_returns_complete_response(self, repo, service):
        profile = UserBehavioralProfile(
            user_id="user-1", peak_focus_hours=[10, 14],
            stress_triggers={"evening_sessions": 0.6},
            preferred_pace="slow", avg_cognitive_load=0.45, total_sessions=3,
        )
        repo.upsert_behavioral_profile(profile)
        summary = DailySummary(
            user_id="user-1", session_id="s1", date="2026-05-09",
            avg_cognitive_load=0.45, avg_frustration=0.3, avg_attention=0.7,
            snapshot_count=20, dominant_adaptation="reduce_ui_complexity",
        )
        repo.add_daily_summary(summary)

        response = service.get_full_memory("user-1")
        assert response.user_id == "user-1"
        assert response.profile is not None
        assert len(response.daily_trend) == 1
        assert isinstance(response.suggestions, list)
