"""Tests for JWT auth: unit + integration."""

from __future__ import annotations

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["ENABLE_AUTH"] = "false"

from fastapi.testclient import TestClient

from db.behavior_repository import BehaviorRepository
from models.user import UserRegister
from services.auth_service import AuthService
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
    return AuthService(repo)


# ── Unit Tests: Registration ────────────────────────────────────────


class TestRegistration:
    def test_register_user(self, service):
        record = service.register(UserRegister(username="alice", password="securepass123"))
        assert record.username == "alice"
        assert len(record.user_id) > 0

    def test_register_with_display_name(self, service):
        record = service.register(UserRegister(
            username="bob", password="securepass123", display_name="Bob Smith",
        ))
        assert record.display_name == "Bob Smith"

    def test_duplicate_username(self, service):
        service.register(UserRegister(username="alice", password="pass12345"))
        with pytest.raises(ValueError, match="already taken"):
            service.register(UserRegister(username="alice", password="otherpass123"))


# ── Unit Tests: Login ────────────────────────────────────────────────


class TestLogin:
    def test_successful_login(self, service):
        service.register(UserRegister(username="alice", password="securepass123"))
        result = service.login("alice", "securepass123")
        assert result is not None
        assert result.access_token
        assert result.refresh_token
        assert result.token_type == "bearer"
        assert result.expires_in > 0

    def test_wrong_password(self, service):
        service.register(UserRegister(username="alice", password="securepass123"))
        result = service.login("alice", "wrongpass")
        assert result is None

    def test_nonexistent_user(self, service):
        result = service.login("ghost", "pass12345")
        assert result is None


# ── Unit Tests: Token Verification ───────────────────────────────────


class TestTokenVerification:
    def test_verify_valid_access_token(self, service):
        service.register(UserRegister(username="alice", password="securepass123"))
        tokens = service.login("alice", "securepass123")
        user_id = service.verify_access_token(tokens.access_token)
        assert user_id is not None

    def test_verify_refresh_token_rejected(self, service):
        service.register(UserRegister(username="alice", password="securepass123"))
        tokens = service.login("alice", "securepass123")
        user_id = service.verify_access_token(tokens.refresh_token)
        assert user_id is None

    def test_verify_invalid_token(self, service):
        assert service.verify_access_token("garbage.token.here") is None


# ── Unit Tests: Refresh ──────────────────────────────────────────────


class TestRefresh:
    def test_refresh_success(self, service):
        service.register(UserRegister(username="alice", password="securepass123"))
        tokens = service.login("alice", "securepass123")
        new_tokens = service.refresh(tokens.refresh_token)
        assert new_tokens is not None
        assert new_tokens.access_token
        assert new_tokens.refresh_token
        assert new_tokens.expires_in > 0
        # Verify new access token is valid
        user_id = service.verify_access_token(new_tokens.access_token)
        assert user_id is not None

    def test_refresh_with_access_token_fails(self, service):
        service.register(UserRegister(username="alice", password="securepass123"))
        tokens = service.login("alice", "securepass123")
        assert service.refresh(tokens.access_token) is None

    def test_refresh_invalid_token(self, service):
        assert service.refresh("not.a.token") is None


# ── Unit Tests: User Info ────────────────────────────────────────────


class TestUserInfo:
    def test_get_user_info(self, service):
        record = service.register(UserRegister(username="alice", password="securepass123"))
        info = service.get_user_info(record.user_id)
        assert info is not None
        assert info.username == "alice"

    def test_nonexistent_user(self, service):
        assert service.get_user_info("ghost-id") is None


# ── Unit Tests: Password Hashing ─────────────────────────────────────


class TestPasswordSecurity:
    def test_password_not_stored_plain(self, repo, service):
        record = service.register(UserRegister(username="alice", password="securepass123"))
        stored_hash = repo.get_password_hash(record.user_id)
        assert stored_hash != "securepass123"
        assert stored_hash.startswith("$2b$")  # bcrypt hash


# ── Unit Tests: Schema Migration ─────────────────────────────────────


class TestSchemaMigration:
    def test_initial_version(self, repo):
        assert repo.get_schema_version() == 0

    def test_record_migration(self, repo):
        repo.record_migration(1)
        assert repo.get_schema_version() == 1
        repo.record_migration(2)
        assert repo.get_schema_version() == 2

    def test_idempotent_migration(self, repo):
        repo.record_migration(1)
        repo.record_migration(1)  # Should not error
        assert repo.get_schema_version() == 1


# ── Integration Tests (API) ──────────────────────────────────────────


class TestRegisterAPI:
    def test_register(self):
        import uuid
        username = f"api-user-{uuid.uuid4().hex[:8]}"
        resp = client.post("/api/v1/auth/register", json={
            "username": username,
            "password": "securepass123",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == username
        assert "user_id" in data

    def test_duplicate(self):
        import uuid
        username = f"api-dup-{uuid.uuid4().hex[:8]}"
        client.post("/api/v1/auth/register", json={
            "username": username, "password": "securepass123",
        })
        resp = client.post("/api/v1/auth/register", json={
            "username": username, "password": "other12345",
        })
        assert resp.status_code == 409

    def test_validation(self):
        resp = client.post("/api/v1/auth/register", json={
            "username": "ab", "password": "short",
        })
        assert resp.status_code == 422


class TestLoginAPI:
    def test_login_success(self):
        import uuid
        username = f"api-login-{uuid.uuid4().hex[:8]}"
        client.post("/api/v1/auth/register", json={
            "username": username, "password": "securepass123",
        })
        resp = client.post("/api/v1/auth/login", json={
            "username": username, "password": "securepass123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self):
        import uuid
        username = f"api-wrong-{uuid.uuid4().hex[:8]}"
        client.post("/api/v1/auth/register", json={
            "username": username, "password": "securepass123",
        })
        resp = client.post("/api/v1/auth/login", json={
            "username": username, "password": "wrongpass123",
        })
        assert resp.status_code == 401


class TestRefreshAPI:
    def test_refresh_success(self):
        import uuid
        username = f"api-ref-{uuid.uuid4().hex[:8]}"
        client.post("/api/v1/auth/register", json={
            "username": username, "password": "securepass123",
        })
        login = client.post("/api/v1/auth/login", json={
            "username": username, "password": "securepass123",
        }).json()
        resp = client.post("/api/v1/auth/refresh", json={
            "refresh_token": login["refresh_token"],
        })
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_refresh_invalid(self):
        resp = client.post("/api/v1/auth/refresh", json={
            "refresh_token": "not.a.token",
        })
        assert resp.status_code == 401


class TestMeAPI:
    def test_get_me(self):
        import uuid
        username = f"api-me-{uuid.uuid4().hex[:8]}"
        client.post("/api/v1/auth/register", json={
            "username": username, "password": "securepass123",
        })
        login = client.post("/api/v1/auth/login", json={
            "username": username, "password": "securepass123",
        }).json()
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {login['access_token']}"},
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == username

    def test_no_auth(self):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_invalid_token(self):
        resp = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401
