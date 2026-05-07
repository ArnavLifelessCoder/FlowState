from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from statistics import pvariance
from threading import RLock

from models.session import BehaviorEvent, BehaviorEventType


@dataclass
class BehaviorFeatures:
    typing_wpm: float
    error_rate: float
    hesitation_index: float
    task_switches_per_minute: float


class BehaviorService:
    """Derives lightweight cognitive features from recent behavior events."""

    def __init__(self, window_size: int = 500) -> None:
        self._events: deque[BehaviorEvent] = deque(maxlen=window_size)
        self._lock = RLock()

    def ingest(self, event: BehaviorEvent) -> BehaviorFeatures:
        with self._lock:
            self._events.append(event)
            return self.compute_features()

    def event_count(self) -> int:
        with self._lock:
            return len(self._events)

    def compute_features(self) -> BehaviorFeatures:
        keypresses = [e for e in self._events if e.type == BehaviorEventType.KEYPRESS]
        focus_changes = [e for e in self._events if e.type == BehaviorEventType.FOCUS_CHANGE]

        typing_wpm = self._compute_typing_wpm(keypresses)
        error_rate = self._compute_error_rate(keypresses)
        hesitation_index = self._compute_hesitation_index(keypresses)
        task_switches = self._compute_task_switches_per_minute(focus_changes)

        return BehaviorFeatures(
            typing_wpm=typing_wpm,
            error_rate=error_rate,
            hesitation_index=hesitation_index,
            task_switches_per_minute=task_switches,
        )

    @staticmethod
    def _compute_typing_wpm(keypresses: list[BehaviorEvent]) -> float:
        if len(keypresses) < 2:
            return 0.0

        span_seconds = max(keypresses[-1].timestamp - keypresses[0].timestamp, 1.0)
        words_typed = len(keypresses) / 5.0
        return round((words_typed / span_seconds) * 60.0, 2)

    @staticmethod
    def _compute_error_rate(keypresses: list[BehaviorEvent]) -> float:
        if not keypresses:
            return 0.0

        backspaces = sum(
            1
            for e in keypresses
            if e.metadata.get("is_backspace") is True or e.metadata.get("key") == "Backspace"
        )
        return round(backspaces / len(keypresses), 4)

    @staticmethod
    def _compute_hesitation_index(keypresses: list[BehaviorEvent]) -> float:
        if len(keypresses) < 3:
            return 0.0

        deltas = [
            keypresses[idx].timestamp - keypresses[idx - 1].timestamp
            for idx in range(1, len(keypresses))
        ]
        if len(deltas) < 2:
            return 0.0

        return round(pvariance(deltas), 4)

    def _compute_task_switches_per_minute(self, focus_changes: list[BehaviorEvent]) -> float:
        if len(focus_changes) < 1:
            return 0.0

        first_ts = self._events[0].timestamp if self._events else 0.0
        last_ts = self._events[-1].timestamp if self._events else first_ts
        span_minutes = max((last_ts - first_ts) / 60.0, 1 / 60.0)
        return round(len(focus_changes) / span_minutes, 2)

    def snapshot(self) -> dict[str, float]:
        with self._lock:
            features = self.compute_features()
            # A minimal heuristic proxy until model inference is plugged in.
            cognitive_load = min(
                1.0,
                max(
                    0.0,
                    0.25 * (features.typing_wpm / 60.0)
                    + 0.45 * features.error_rate
                    + 0.20 * min(features.hesitation_index / 3.0, 1.0)
                    + 0.10 * min(features.task_switches_per_minute / 30.0, 1.0),
                ),
            )
            frustration_score = min(1.0, 0.55 * features.error_rate + 0.45 * cognitive_load)
            attention_level = max(0.0, 1.0 - (0.6 * cognitive_load + 0.4 * features.error_rate))
            recommended_adaptation = self._recommended_adaptation(
                cognitive_load=cognitive_load,
                frustration_score=frustration_score,
                attention_level=attention_level,
            )

            return {
                "typing_wpm": features.typing_wpm,
                "error_rate": features.error_rate,
                "hesitation_index": features.hesitation_index,
                "task_switches_per_minute": features.task_switches_per_minute,
                "cognitive_load": round(cognitive_load, 4),
                "frustration_score": round(frustration_score, 4),
                "attention_level": round(attention_level, 4),
                "recommended_adaptation": recommended_adaptation,
                "sample_size": float(len(self._events)),
            }

    @staticmethod
    def _recommended_adaptation(
        cognitive_load: float, frustration_score: float, attention_level: float
    ) -> str:
        if frustration_score >= 0.7:
            return "pause_notifications"
        if cognitive_load >= 0.65:
            return "reduce_ui_complexity"
        if attention_level < 0.35:
            return "enable_focus_mode"
        if attention_level > 0.8 and cognitive_load < 0.35:
            return "increase_ui_complexity"
        return "resume_normal"

