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

