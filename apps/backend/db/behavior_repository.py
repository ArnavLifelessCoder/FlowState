from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock

from models.behavior import (
    AdaptationDecisionRecord,
    AdaptationFeedbackIn,
    AdaptationFeedbackRecord,
    BehaviorSnapshotRecord,
    BehaviorSnapshot,
)
from models.assessment import AssessmentResult, InstrumentType
from models.emotion import EmotionState
from models.memory import DailySummary, UserBehavioralProfile
from models.privacy import SensingState
from models.session import SessionRecord
from models.user import UserRecord


class BehaviorRepository:
    def __init__(self, database_url: str) -> None:
        if not database_url.startswith("sqlite:///"):
            raise ValueError("Only sqlite is supported in this baseline implementation.")
        self._db_path = Path(database_url.removeprefix("sqlite:///"))
        self._lock = RLock()
        self._initialized = False

    def initialize(self) -> None:
        with self._lock:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS behavior_sessions (
                        session_id TEXT PRIMARY KEY,
                        metrics_json TEXT NOT NULL,
                        sample_size INTEGER NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS behavior_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        metrics_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS adaptation_feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        action TEXT NOT NULL,
                        reward REAL NOT NULL,
                        decision_state_key TEXT,
                        task_completion_delta REAL NOT NULL,
                        emotional_stability_delta REAL NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                columns = conn.execute("PRAGMA table_info(adaptation_feedback)").fetchall()
                column_names = {str(col[1]) for col in columns}
                if "decision_state_key" not in column_names:
                    conn.execute("ALTER TABLE adaptation_feedback ADD COLUMN decision_state_key TEXT")
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS adaptation_q_values (
                        session_id TEXT NOT NULL,
                        state_key TEXT NOT NULL,
                        action TEXT NOT NULL,
                        q_value REAL NOT NULL,
                        updated_at TEXT NOT NULL,
                        PRIMARY KEY (session_id, state_key, action)
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS adaptation_decisions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        state_key TEXT NOT NULL,
                        action TEXT NOT NULL,
                        exploration INTEGER NOT NULL,
                        q_values_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS user_behavioral_profiles (
                        user_id TEXT PRIMARY KEY,
                        peak_focus_hours TEXT NOT NULL,
                        stress_triggers TEXT NOT NULL,
                        preferred_pace TEXT NOT NULL,
                        avg_cognitive_load REAL NOT NULL,
                        total_sessions INTEGER NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS session_daily_summaries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        date TEXT NOT NULL,
                        avg_cognitive_load REAL NOT NULL,
                        avg_frustration REAL NOT NULL,
                        avg_attention REAL NOT NULL,
                        snapshot_count INTEGER NOT NULL,
                        peak_hour INTEGER,
                        dominant_adaptation TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        UNIQUE(user_id, session_id, date)
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        started_at TEXT NOT NULL,
                        ended_at TEXT,
                        platform TEXT NOT NULL DEFAULT 'web'
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sensing_states (
                        session_id TEXT PRIMARY KEY,
                        vision_enabled INTEGER NOT NULL DEFAULT 1,
                        audio_enabled INTEGER NOT NULL DEFAULT 1,
                        behavior_enabled INTEGER NOT NULL DEFAULT 1,
                        all_paused INTEGER NOT NULL DEFAULT 0,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS users (
                        user_id TEXT PRIMARY KEY,
                        username TEXT NOT NULL UNIQUE,
                        password_hash TEXT NOT NULL,
                        display_name TEXT NOT NULL DEFAULT '',
                        created_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS emotion_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        state_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS assessments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        user_id TEXT NOT NULL,
                        instrument_type TEXT NOT NULL,
                        result_json TEXT NOT NULL,
                        normalized_score REAL NOT NULL,
                        completed_at TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_migrations (
                        version INTEGER PRIMARY KEY,
                        applied_at TEXT NOT NULL
                    )
                    """
                )
                conn.commit()
            self._initialized = True

    def upsert(self, snapshot: BehaviorSnapshot) -> None:
        self._ensure_ready()
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO behavior_sessions(session_id, metrics_json, sample_size, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        metrics_json=excluded.metrics_json,
                        sample_size=excluded.sample_size,
                        updated_at=excluded.updated_at
                    """,
                    (
                        snapshot.session_id,
                        json.dumps(snapshot.model_dump(mode="json")),
                        snapshot.sample_size,
                        snapshot.updated_at.isoformat(),
                    ),
                )
                conn.execute(
                    """
                    INSERT INTO behavior_snapshots(session_id, metrics_json, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (
                        snapshot.session_id,
                        json.dumps(snapshot.model_dump(mode="json")),
                        snapshot.updated_at.isoformat(),
                    ),
                )
                conn.commit()

    def get(self, session_id: str) -> BehaviorSnapshot | None:
        self._ensure_ready()
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                row = conn.execute(
                    "SELECT metrics_json FROM behavior_sessions WHERE session_id = ?",
                    (session_id,),
                ).fetchone()
        if row is None:
            return None
        data = json.loads(row[0])
        return BehaviorSnapshot.model_validate(data)

    def ping(self) -> bool:
        try:
            self._ensure_ready()
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("SELECT 1").fetchone()
            return True
        except Exception:
            return False

    def add_feedback(self, payload: AdaptationFeedbackIn) -> AdaptationFeedbackRecord:
        self._ensure_ready()
        created_at = datetime.now(timezone.utc)
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO adaptation_feedback(
                        session_id, action, reward, decision_state_key, task_completion_delta, emotional_stability_delta, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload.session_id,
                        payload.action,
                        payload.reward,
                        payload.decision_state_key,
                        payload.task_completion_delta,
                        payload.emotional_stability_delta,
                        created_at.isoformat(),
                    ),
                )
                conn.commit()
                feedback_id = int(cursor.lastrowid)
        return AdaptationFeedbackRecord(
            id=feedback_id,
            session_id=payload.session_id,
            action=payload.action,
            reward=payload.reward,
            task_completion_delta=payload.task_completion_delta,
            emotional_stability_delta=payload.emotional_stability_delta,
            created_at=created_at,
        )

    def get_feedback(
        self, session_id: str, limit: int = 50, before_id: int | None = None
    ) -> list[AdaptationFeedbackRecord]:
        self._ensure_ready()
        safe_limit = max(1, min(limit, 200))
        query = """
            SELECT id, session_id, action, reward, task_completion_delta, emotional_stability_delta, created_at
            FROM adaptation_feedback
            WHERE session_id = ?
        """
        params: list[object] = [session_id]
        if before_id is not None:
            query += " AND id < ?"
            params.append(before_id)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(safe_limit)
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                rows = conn.execute(query, tuple(params)).fetchall()
        result: list[AdaptationFeedbackRecord] = []
        for row in rows:
            result.append(
                AdaptationFeedbackRecord(
                    id=int(row[0]),
                    session_id=str(row[1]),
                    action=str(row[2]),
                    reward=float(row[3]),
                    task_completion_delta=float(row[4]),
                    emotional_stability_delta=float(row[5]),
                    created_at=datetime.fromisoformat(str(row[6])),
                )
            )
        return result

    def _ensure_ready(self) -> None:
        if not self._initialized:
            self.initialize()

    def get_q_values(self, session_id: str, state_key: str, actions: list[str]) -> dict[str, float]:
        self._ensure_ready()
        result = {action: 0.0 for action in actions}
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                rows = conn.execute(
                    """
                    SELECT action, q_value
                    FROM adaptation_q_values
                    WHERE session_id = ? AND state_key = ?
                    """,
                    (session_id, state_key),
                ).fetchall()
        for row in rows:
            action = str(row[0])
            if action in result:
                result[action] = float(row[1])
        return result

    def upsert_q_value(self, session_id: str, state_key: str, action: str, q_value: float) -> None:
        self._ensure_ready()
        updated_at = datetime.now(timezone.utc).isoformat()
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO adaptation_q_values(session_id, state_key, action, q_value, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(session_id, state_key, action) DO UPDATE SET
                        q_value = excluded.q_value,
                        updated_at = excluded.updated_at
                    """,
                    (session_id, state_key, action, q_value, updated_at),
                )
                conn.commit()

    def add_decision(
        self,
        session_id: str,
        state_key: str,
        action: str,
        exploration: bool,
        q_values: dict[str, float],
    ) -> AdaptationDecisionRecord:
        self._ensure_ready()
        created_at = datetime.now(timezone.utc)
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO adaptation_decisions(
                        session_id, state_key, action, exploration, q_values_json, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        state_key,
                        action,
                        1 if exploration else 0,
                        json.dumps(q_values),
                        created_at.isoformat(),
                    ),
                )
                conn.commit()
                decision_id = int(cursor.lastrowid)
        return AdaptationDecisionRecord(
            id=decision_id,
            session_id=session_id,
            state_key=state_key,
            action=action,
            exploration=exploration,
            q_values=q_values,
            created_at=created_at,
        )

    def get_decisions(
        self, session_id: str, limit: int = 100, before_id: int | None = None
    ) -> list[AdaptationDecisionRecord]:
        self._ensure_ready()
        safe_limit = max(1, min(limit, 500))
        query = """
            SELECT id, session_id, state_key, action, exploration, q_values_json, created_at
            FROM adaptation_decisions
            WHERE session_id = ?
        """
        params: list[object] = [session_id]
        if before_id is not None:
            query += " AND id < ?"
            params.append(before_id)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(safe_limit)
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                rows = conn.execute(query, tuple(params)).fetchall()
        return [
            AdaptationDecisionRecord(
                id=int(row[0]),
                session_id=str(row[1]),
                state_key=str(row[2]),
                action=str(row[3]),
                exploration=bool(row[4]),
                q_values=json.loads(str(row[5])),
                created_at=datetime.fromisoformat(str(row[6])),
            )
            for row in rows
        ]

    def get_behavior_history(
        self, session_id: str, limit: int = 100, before_id: int | None = None
    ) -> tuple[list[BehaviorSnapshotRecord], bool]:
        self._ensure_ready()
        safe_limit = max(1, min(limit, 500))
        query = """
            SELECT id, metrics_json
            FROM behavior_snapshots
            WHERE session_id = ?
        """
        params: list[object] = [session_id]
        if before_id is not None:
            query += " AND id < ?"
            params.append(before_id)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(safe_limit + 1)
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                rows = conn.execute(query, tuple(params)).fetchall()
        has_more = len(rows) > safe_limit
        rows = rows[:safe_limit]
        records = [
            BehaviorSnapshotRecord(
                id=int(row[0]),
                session_id=session_id,
                snapshot=BehaviorSnapshot.model_validate(json.loads(str(row[1]))),
            )
            for row in rows
        ]
        return records, has_more

    # ── Behavioral Memory ────────────────────────────────────────────

    def upsert_behavioral_profile(self, profile: UserBehavioralProfile) -> None:
        self._ensure_ready()
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO user_behavioral_profiles(
                        user_id, peak_focus_hours, stress_triggers, preferred_pace,
                        avg_cognitive_load, total_sessions, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        peak_focus_hours = excluded.peak_focus_hours,
                        stress_triggers = excluded.stress_triggers,
                        preferred_pace = excluded.preferred_pace,
                        avg_cognitive_load = excluded.avg_cognitive_load,
                        total_sessions = excluded.total_sessions,
                        updated_at = excluded.updated_at
                    """,
                    (
                        profile.user_id,
                        json.dumps(profile.peak_focus_hours),
                        json.dumps(profile.stress_triggers),
                        profile.preferred_pace,
                        profile.avg_cognitive_load,
                        profile.total_sessions,
                        profile.updated_at.isoformat(),
                    ),
                )
                conn.commit()

    def get_behavioral_profile(self, user_id: str) -> UserBehavioralProfile | None:
        self._ensure_ready()
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                row = conn.execute(
                    """
                    SELECT user_id, peak_focus_hours, stress_triggers, preferred_pace,
                           avg_cognitive_load, total_sessions, updated_at
                    FROM user_behavioral_profiles
                    WHERE user_id = ?
                    """,
                    (user_id,),
                ).fetchone()
        if row is None:
            return None
        return UserBehavioralProfile(
            user_id=str(row[0]),
            peak_focus_hours=json.loads(str(row[1])),
            stress_triggers=json.loads(str(row[2])),
            preferred_pace=str(row[3]),
            avg_cognitive_load=float(row[4]),
            total_sessions=int(row[5]),
            updated_at=datetime.fromisoformat(str(row[6])),
        )

    def delete_behavioral_profile(self, user_id: str) -> bool:
        self._ensure_ready()
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM user_behavioral_profiles WHERE user_id = ?", (user_id,)
                )
                conn.execute(
                    "DELETE FROM session_daily_summaries WHERE user_id = ?", (user_id,)
                )
                conn.commit()
                return cursor.rowcount > 0

    def add_daily_summary(self, summary: DailySummary) -> None:
        self._ensure_ready()
        created_at = datetime.now(timezone.utc).isoformat()
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO session_daily_summaries(
                        user_id, session_id, date, avg_cognitive_load, avg_frustration,
                        avg_attention, snapshot_count, peak_hour, dominant_adaptation, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, session_id, date) DO UPDATE SET
                        avg_cognitive_load = excluded.avg_cognitive_load,
                        avg_frustration = excluded.avg_frustration,
                        avg_attention = excluded.avg_attention,
                        snapshot_count = excluded.snapshot_count,
                        peak_hour = excluded.peak_hour,
                        dominant_adaptation = excluded.dominant_adaptation,
                        created_at = excluded.created_at
                    """,
                    (
                        summary.user_id,
                        summary.session_id,
                        summary.date,
                        summary.avg_cognitive_load,
                        summary.avg_frustration,
                        summary.avg_attention,
                        summary.snapshot_count,
                        summary.peak_hour,
                        summary.dominant_adaptation,
                        created_at,
                    ),
                )
                conn.commit()

    def get_daily_summaries(self, user_id: str, days: int = 30) -> list[DailySummary]:
        self._ensure_ready()
        safe_days = max(1, min(days, 365))
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                rows = conn.execute(
                    """
                    SELECT user_id, session_id, date, avg_cognitive_load, avg_frustration,
                           avg_attention, snapshot_count, peak_hour, dominant_adaptation
                    FROM session_daily_summaries
                    WHERE user_id = ?
                    ORDER BY date DESC
                    LIMIT ?
                    """,
                    (user_id, safe_days),
                ).fetchall()
        return [
            DailySummary(
                user_id=str(row[0]),
                session_id=str(row[1]),
                date=str(row[2]),
                avg_cognitive_load=float(row[3]),
                avg_frustration=float(row[4]),
                avg_attention=float(row[5]),
                snapshot_count=int(row[6]),
                peak_hour=int(row[7]) if row[7] is not None else None,
                dominant_adaptation=str(row[8]),
            )
            for row in rows
        ]

    def get_all_snapshots_with_timestamps(
        self, session_ids: list[str],
    ) -> list[tuple[str, BehaviorSnapshot, str]]:
        """Return (session_id, snapshot, created_at_iso) for given sessions."""
        self._ensure_ready()
        if not session_ids:
            return []
        placeholders = ",".join("?" for _ in session_ids)
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                rows = conn.execute(
                    f"""
                    SELECT session_id, metrics_json, created_at
                    FROM behavior_snapshots
                    WHERE session_id IN ({placeholders})
                    ORDER BY created_at ASC
                    """,
                    tuple(session_ids),
                ).fetchall()
        results: list[tuple[str, BehaviorSnapshot, str]] = []
        for row in rows:
            snapshot = BehaviorSnapshot.model_validate(json.loads(str(row[1])))
            results.append((str(row[0]), snapshot, str(row[2])))
        return results

    def get_distinct_session_ids(self) -> list[str]:
        """Return all distinct session_ids that have snapshots."""
        self._ensure_ready()
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                rows = conn.execute(
                    "SELECT DISTINCT session_id FROM behavior_snapshots"
                ).fetchall()
        return [str(row[0]) for row in rows]

    # ── Session Management ────────────────────────────────────────────

    def create_session(
        self, session_id: str, user_id: str, platform: str = "web",
    ) -> SessionRecord:
        self._ensure_ready()
        started_at = datetime.now(timezone.utc)
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO sessions(session_id, user_id, started_at, platform)
                    VALUES (?, ?, ?, ?)
                    """,
                    (session_id, user_id, started_at.isoformat(), platform),
                )
                conn.commit()
        return SessionRecord(
            session_id=session_id,
            user_id=user_id,
            started_at=started_at,
            ended_at=None,
            platform=platform,
            is_active=True,
        )

    def end_session(self, session_id: str) -> SessionRecord | None:
        self._ensure_ready()
        ended_at = datetime.now(timezone.utc)
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.execute(
                    "UPDATE sessions SET ended_at = ? WHERE session_id = ? AND ended_at IS NULL",
                    (ended_at.isoformat(), session_id),
                )
                conn.commit()
                if cursor.rowcount == 0:
                    return None
        return self.get_session(session_id)

    def get_session(self, session_id: str) -> SessionRecord | None:
        self._ensure_ready()
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                row = conn.execute(
                    "SELECT session_id, user_id, started_at, ended_at, platform FROM sessions WHERE session_id = ?",
                    (session_id,),
                ).fetchone()
        if row is None:
            return None
        ended_at = datetime.fromisoformat(str(row[3])) if row[3] else None
        return SessionRecord(
            session_id=str(row[0]),
            user_id=str(row[1]),
            started_at=datetime.fromisoformat(str(row[2])),
            ended_at=ended_at,
            platform=str(row[4]),
            is_active=ended_at is None,
        )

    def list_sessions(
        self, user_id: str, limit: int = 50, active_only: bool = False,
    ) -> list[SessionRecord]:
        self._ensure_ready()
        safe_limit = max(1, min(limit, 200))
        query = "SELECT session_id, user_id, started_at, ended_at, platform FROM sessions WHERE user_id = ?"
        params: list[object] = [user_id]
        if active_only:
            query += " AND ended_at IS NULL"
        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(safe_limit)
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                rows = conn.execute(query, tuple(params)).fetchall()
        results: list[SessionRecord] = []
        for row in rows:
            ended_at = datetime.fromisoformat(str(row[3])) if row[3] else None
            results.append(
                SessionRecord(
                    session_id=str(row[0]),
                    user_id=str(row[1]),
                    started_at=datetime.fromisoformat(str(row[2])),
                    ended_at=ended_at,
                    platform=str(row[4]),
                    is_active=ended_at is None,
                )
            )
        return results

    def get_session_ids_for_user(self, user_id: str) -> list[str]:
        """Return all session_ids belonging to a user."""
        self._ensure_ready()
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                rows = conn.execute(
                    "SELECT session_id FROM sessions WHERE user_id = ? ORDER BY started_at DESC",
                    (user_id,),
                ).fetchall()
        return [str(row[0]) for row in rows]

    def get_snapshots_for_session(
        self, session_id: str, limit: int = 200,
    ) -> list[BehaviorSnapshot]:
        """Return historical snapshots for a session."""
        self._ensure_ready()
        safe_limit = max(1, min(limit, 1000))
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                rows = conn.execute(
                    "SELECT metrics_json FROM behavior_snapshots WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
                    (session_id, safe_limit),
                ).fetchall()
        results: list[BehaviorSnapshot] = []
        for row in rows:
            try:
                data = json.loads(str(row[0]))
                results.append(BehaviorSnapshot.model_validate(data))
            except Exception:
                continue
        return results

    # ── Privacy / GDPR ───────────────────────────────────────────────

    def delete_all_user_data(self, user_id: str) -> dict[str, int]:
        """Cascade-delete ALL data for a user across all tables. Returns count per table."""
        self._ensure_ready()
        session_ids = self.get_session_ids_for_user(user_id)
        counts: dict[str, int] = {}
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                if session_ids:
                    ph = ",".join("?" for _ in session_ids)
                    for table in [
                        "behavior_snapshots", "behavior_sessions",
                        "adaptation_feedback", "adaptation_q_values",
                        "adaptation_decisions", "sensing_states",
                        "emotion_snapshots", "assessments",
                    ]:
                        cursor = conn.execute(
                            f"DELETE FROM {table} WHERE session_id IN ({ph})",
                            tuple(session_ids),
                        )
                        counts[table] = cursor.rowcount

                # Tables keyed by user_id
                cursor = conn.execute(
                    "DELETE FROM user_behavioral_profiles WHERE user_id = ?", (user_id,)
                )
                counts["user_behavioral_profiles"] = cursor.rowcount
                cursor = conn.execute(
                    "DELETE FROM session_daily_summaries WHERE user_id = ?", (user_id,)
                )
                counts["session_daily_summaries"] = cursor.rowcount
                cursor = conn.execute(
                    "DELETE FROM sessions WHERE user_id = ?", (user_id,)
                )
                counts["sessions"] = cursor.rowcount
                conn.commit()
        return counts

    def export_all_user_data(self, user_id: str) -> dict:
        """Export ALL data for a user as a plain dict."""
        self._ensure_ready()
        session_ids = self.get_session_ids_for_user(user_id)
        data: dict = {
            "sessions": [],
            "behavior_snapshots": [],
            "adaptation_decisions": [],
            "adaptation_feedback": [],
            "behavioral_profile": None,
            "daily_summaries": [],
            "sensing_states": [],
        }
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                # Sessions
                for row in conn.execute(
                    "SELECT session_id, user_id, started_at, ended_at, platform FROM sessions WHERE user_id = ?",
                    (user_id,),
                ).fetchall():
                    data["sessions"].append({
                        "session_id": row[0], "user_id": row[1],
                        "started_at": row[2], "ended_at": row[3], "platform": row[4],
                    })

                if session_ids:
                    ph = ",".join("?" for _ in session_ids)
                    # Behavior snapshots
                    for row in conn.execute(
                        f"SELECT id, session_id, metrics_json, created_at FROM behavior_snapshots WHERE session_id IN ({ph})",
                        tuple(session_ids),
                    ).fetchall():
                        data["behavior_snapshots"].append({
                            "id": row[0], "session_id": row[1],
                            "metrics": json.loads(str(row[2])), "created_at": row[3],
                        })

                    # Adaptation decisions
                    for row in conn.execute(
                        f"SELECT id, session_id, state_key, action, exploration, q_values_json, created_at FROM adaptation_decisions WHERE session_id IN ({ph})",
                        tuple(session_ids),
                    ).fetchall():
                        data["adaptation_decisions"].append({
                            "id": row[0], "session_id": row[1], "state_key": row[2],
                            "action": row[3], "exploration": bool(row[4]),
                            "q_values": json.loads(str(row[5])), "created_at": row[6],
                        })

                    # Adaptation feedback
                    for row in conn.execute(
                        f"SELECT id, session_id, action, reward, task_completion_delta, emotional_stability_delta, created_at FROM adaptation_feedback WHERE session_id IN ({ph})",
                        tuple(session_ids),
                    ).fetchall():
                        data["adaptation_feedback"].append({
                            "id": row[0], "session_id": row[1], "action": row[2],
                            "reward": row[3], "task_completion_delta": row[4],
                            "emotional_stability_delta": row[5], "created_at": row[6],
                        })

                    # Sensing states
                    for row in conn.execute(
                        f"SELECT session_id, vision_enabled, audio_enabled, behavior_enabled, all_paused, updated_at FROM sensing_states WHERE session_id IN ({ph})",
                        tuple(session_ids),
                    ).fetchall():
                        data["sensing_states"].append({
                            "session_id": row[0], "vision_enabled": bool(row[1]),
                            "audio_enabled": bool(row[2]), "behavior_enabled": bool(row[3]),
                            "all_paused": bool(row[4]), "updated_at": row[5],
                        })

                # Profile
                profile = self.get_behavioral_profile(user_id)
                if profile:
                    data["behavioral_profile"] = profile.model_dump(mode="json")

                # Daily summaries
                for s in self.get_daily_summaries(user_id, days=365):
                    data["daily_summaries"].append(s.model_dump(mode="json"))

        return data

    def upsert_sensing_state(self, state: SensingState) -> None:
        self._ensure_ready()
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO sensing_states(session_id, vision_enabled, audio_enabled, behavior_enabled, all_paused, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        vision_enabled = excluded.vision_enabled,
                        audio_enabled = excluded.audio_enabled,
                        behavior_enabled = excluded.behavior_enabled,
                        all_paused = excluded.all_paused,
                        updated_at = excluded.updated_at
                    """,
                    (
                        state.session_id,
                        1 if state.vision_enabled else 0,
                        1 if state.audio_enabled else 0,
                        1 if state.behavior_enabled else 0,
                        1 if state.all_paused else 0,
                        state.updated_at.isoformat(),
                    ),
                )
                conn.commit()

    def get_sensing_state(self, session_id: str) -> SensingState | None:
        self._ensure_ready()
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                row = conn.execute(
                    "SELECT session_id, vision_enabled, audio_enabled, behavior_enabled, all_paused, updated_at FROM sensing_states WHERE session_id = ?",
                    (session_id,),
                ).fetchone()
        if row is None:
            return None
        return SensingState(
            session_id=str(row[0]),
            vision_enabled=bool(row[1]),
            audio_enabled=bool(row[2]),
            behavior_enabled=bool(row[3]),
            all_paused=bool(row[4]),
            updated_at=datetime.fromisoformat(str(row[5])),
        )

    # ── Users / Auth ─────────────────────────────────────────────────────

    def create_user(
        self, user_id: str, username: str, password_hash: str, display_name: str,
    ) -> UserRecord:
        self._ensure_ready()
        now = datetime.now(timezone.utc)
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    "INSERT INTO users(user_id, username, password_hash, display_name, created_at) VALUES (?, ?, ?, ?, ?)",
                    (user_id, username, password_hash, display_name, now.isoformat()),
                )
                conn.commit()
        return UserRecord(
            user_id=user_id, username=username,
            display_name=display_name, created_at=now,
        )

    def get_user_by_username(self, username: str) -> UserRecord | None:
        self._ensure_ready()
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                row = conn.execute(
                    "SELECT user_id, username, display_name, created_at FROM users WHERE username = ?",
                    (username,),
                ).fetchone()
        if row is None:
            return None
        return UserRecord(
            user_id=str(row[0]), username=str(row[1]),
            display_name=str(row[2]), created_at=datetime.fromisoformat(str(row[3])),
        )

    def get_user_by_id(self, user_id: str) -> UserRecord | None:
        self._ensure_ready()
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                row = conn.execute(
                    "SELECT user_id, username, display_name, created_at FROM users WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
        if row is None:
            return None
        return UserRecord(
            user_id=str(row[0]), username=str(row[1]),
            display_name=str(row[2]), created_at=datetime.fromisoformat(str(row[3])),
        )

    def get_password_hash(self, user_id: str) -> str | None:
        self._ensure_ready()
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                row = conn.execute(
                    "SELECT password_hash FROM users WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
        return str(row[0]) if row else None

    # ── Emotion Snapshots (Multimodal) ────────────────────────────────────

    def save_emotion_state(self, state: EmotionState) -> None:
        """Persist a fused multimodal emotion state."""
        self._ensure_ready()
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO emotion_snapshots(session_id, state_json, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (
                        state.session_id,
                        json.dumps(state.model_dump(mode="json")),
                        state.timestamp.isoformat(),
                    ),
                )
                conn.commit()

    def get_emotion_state(self, session_id: str) -> EmotionState | None:
        """Get the latest emotion state for a session."""
        self._ensure_ready()
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                row = conn.execute(
                    "SELECT state_json FROM emotion_snapshots WHERE session_id = ? ORDER BY id DESC LIMIT 1",
                    (session_id,),
                ).fetchone()
        if row is None:
            return None
        return EmotionState.model_validate(json.loads(str(row[0])))

    def get_emotion_history(
        self, session_id: str, limit: int = 50, before_id: int | None = None,
    ) -> tuple[list[EmotionState], bool]:
        """Return emotion history with pagination."""
        self._ensure_ready()
        safe_limit = max(1, min(limit, 500))
        query = "SELECT id, state_json FROM emotion_snapshots WHERE session_id = ?"
        params: list[object] = [session_id]
        if before_id is not None:
            query += " AND id < ?"
            params.append(before_id)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(safe_limit + 1)
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                rows = conn.execute(query, tuple(params)).fetchall()
        has_more = len(rows) > safe_limit
        rows = rows[:safe_limit]
        results: list[EmotionState] = []
        for row in rows:
            try:
                results.append(EmotionState.model_validate(json.loads(str(row[1]))))
            except Exception:
                continue
        return results, has_more

    def get_emotion_snapshot_count(self, session_id: str) -> int:
        """Count emotion snapshots for a session."""
        self._ensure_ready()
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                row = conn.execute(
                    "SELECT COUNT(*) FROM emotion_snapshots WHERE session_id = ?",
                    (session_id,),
                ).fetchone()
        return int(row[0]) if row else 0

    # ── Assessments (Psychometric) ────────────────────────────────────────

    def save_assessment(self, result: AssessmentResult) -> None:
        """Persist a scored assessment result."""
        self._ensure_ready()
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO assessments(session_id, user_id, instrument_type, result_json, normalized_score, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result.session_id,
                        result.user_id,
                        result.instrument_type.value,
                        json.dumps(result.model_dump(mode="json")),
                        result.normalized_score,
                        result.completed_at.isoformat(),
                    ),
                )
                conn.commit()

    def get_assessments(
        self,
        user_id: str,
        instrument_type: InstrumentType | None = None,
        limit: int = 50,
    ) -> list[AssessmentResult]:
        """Get assessment history for a user, optionally filtered by instrument."""
        self._ensure_ready()
        safe_limit = max(1, min(limit, 500))
        if instrument_type:
            query = "SELECT result_json FROM assessments WHERE user_id = ? AND instrument_type = ? ORDER BY id DESC LIMIT ?"
            params: tuple = (user_id, instrument_type.value, safe_limit)
        else:
            query = "SELECT result_json FROM assessments WHERE user_id = ? ORDER BY id DESC LIMIT ?"
            params = (user_id, safe_limit)

        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                rows = conn.execute(query, params).fetchall()

        results: list[AssessmentResult] = []
        for row in rows:
            try:
                results.append(AssessmentResult.model_validate(json.loads(str(row[0]))))
            except Exception:
                continue
        return results

    def get_assessment_count(self, user_id: str) -> int:
        """Count all assessments for a user."""
        self._ensure_ready()
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                row = conn.execute(
                    "SELECT COUNT(*) FROM assessments WHERE user_id = ?",
                    (user_id,),
                ).fetchone()
        return int(row[0]) if row else 0

    # ── Schema Migrations ────────────────────────────────────────────────

    def get_schema_version(self) -> int:
        """Return the current schema version (0 if never migrated)."""
        self._ensure_ready()
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                row = conn.execute(
                    "SELECT MAX(version) FROM schema_migrations",
                ).fetchone()
        return int(row[0]) if row and row[0] is not None else 0

    def record_migration(self, version: int) -> None:
        """Record that a migration version has been applied."""
        self._ensure_ready()
        now = datetime.now(timezone.utc)
        with self._lock:
            with sqlite3.connect(self._db_path) as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (version, now.isoformat()),
                )
                conn.commit()
