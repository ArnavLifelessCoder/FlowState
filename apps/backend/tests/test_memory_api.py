"""Integration tests for the Memory API endpoints."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Disable auth for tests
os.environ["ENABLE_AUTH"] = "false"

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _ingest_events(session_id: str, count: int = 5):
    """Ingest behavior events to create snapshot data."""
    for i in range(count):
        resp = client.post(
            "/api/v1/behavior/event",
            json={
                "session_id": session_id,
                "event": {
                    "type": "keypress",
                    "timestamp": 1000.0 + i * 0.5,
                    "metadata": {"key": "a"},
                },
            },
        )
        assert resp.status_code == 200


class TestMemoryProfileEndpoint:
    def test_get_empty_profile(self):
        resp = client.get("/api/v1/memory/profile/user-test-1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "user-test-1"
        assert data["profile"] is None
        assert data["suggestions"] == []
        assert data["daily_trend"] == []


class TestMemoryBuildEndpoint:
    def test_build_with_no_data(self):
        resp = client.post(
            "/api/v1/memory/profile/user-test-2/build",
            json=["nonexistent-session"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == "user-test-2"
        assert data["sessions_analyzed"] == 0

    def test_build_with_data(self):
        _ingest_events("build-sess-1", count=10)
        resp = client.post(
            "/api/v1/memory/profile/user-build-1/build",
            json=["build-sess-1"],
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sessions_analyzed"] == 1
        assert data["profile"]["avg_cognitive_load"] > 0


class TestMemorySummaryEndpoint:
    def test_record_summary(self):
        _ingest_events("summary-sess-1", count=5)
        resp = client.post(
            "/api/v1/memory/summary",
            json={
                "user_id": "user-summary-1",
                "session_id": "summary-sess-1",
                "date": "2026-05-09",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["snapshot_count"] >= 1
        assert data["user_id"] == "user-summary-1"

    def test_record_summary_empty_session(self):
        resp = client.post(
            "/api/v1/memory/summary",
            json={
                "user_id": "user-summary-2",
                "session_id": "ghost-session",
                "date": "2026-05-09",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["snapshot_count"] == 0


class TestMemorySuggestionsEndpoint:
    def test_get_suggestions_empty(self):
        resp = client.get("/api/v1/memory/suggestions/user-suggestions-1")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


class TestMemoryDeleteEndpoint:
    def test_delete_nonexistent(self):
        resp = client.delete("/api/v1/memory/profile/user-del-1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["deleted"] is False

    def test_delete_existing(self):
        # Build a profile first
        _ingest_events("del-sess-1", count=3)
        client.post(
            "/api/v1/memory/profile/user-del-2/build",
            json=["del-sess-1"],
        )
        # Verify it exists
        resp = client.get("/api/v1/memory/profile/user-del-2")
        assert resp.json()["profile"] is not None

        # Delete
        resp = client.delete("/api/v1/memory/profile/user-del-2")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

        # Verify deletion
        resp = client.get("/api/v1/memory/profile/user-del-2")
        assert resp.json()["profile"] is None


class TestMemoryValidation:
    def test_invalid_date_format(self):
        resp = client.post(
            "/api/v1/memory/summary",
            json={
                "user_id": "user-val-1",
                "session_id": "val-sess-1",
                "date": "not-a-date",
            },
        )
        assert resp.status_code == 422
