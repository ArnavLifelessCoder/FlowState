from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import datetime, timezone

from db.behavior_repository import BehaviorRepository
from models.behavior import BehaviorSnapshot
from models.memory import (
    BehavioralMemoryResponse,
    DailySummary,
    DailySummaryIn,
    ProactiveSuggestion,
    ProfileBuildResponse,
    ProfileDeleteResponse,
    UserBehavioralProfile,
)

logger = logging.getLogger(__name__)


class MemoryService:
    """Long-term behavioral profiling, pattern detection, and proactive suggestions."""

    def __init__(self, repository: BehaviorRepository) -> None:
        self._repository = repository

    # ── Profile Building ─────────────────────────────────────────────

    def build_profile(self, user_id: str, session_ids: list[str]) -> ProfileBuildResponse:
        """Scan all snapshots for given sessions and build/update the user profile."""
        snapshot_rows = self._repository.get_all_snapshots_with_timestamps(session_ids)
        if not snapshot_rows:
            profile = UserBehavioralProfile(
                user_id=user_id,
                total_sessions=len(session_ids),
            )
            self._repository.upsert_behavioral_profile(profile)
            return ProfileBuildResponse(
                user_id=user_id, profile=profile, sessions_analyzed=0,
            )

        snapshots = [row[1] for row in snapshot_rows]
        timestamps_iso = [row[2] for row in snapshot_rows]

        peak_focus_hours = self._detect_peak_focus_hours(snapshots, timestamps_iso)
        stress_triggers = self._detect_stress_triggers(snapshots, timestamps_iso)
        preferred_pace = self._detect_preferred_pace(snapshots)
        avg_cognitive_load = sum(s.cognitive_load for s in snapshots) / len(snapshots)
        distinct_sessions = len(set(row[0] for row in snapshot_rows))

        profile = UserBehavioralProfile(
            user_id=user_id,
            peak_focus_hours=peak_focus_hours,
            stress_triggers=stress_triggers,
            preferred_pace=preferred_pace,
            avg_cognitive_load=round(avg_cognitive_load, 4),
            total_sessions=distinct_sessions,
            updated_at=datetime.now(timezone.utc),
        )
        self._repository.upsert_behavioral_profile(profile)

        return ProfileBuildResponse(
            user_id=user_id, profile=profile, sessions_analyzed=distinct_sessions,
        )

    def get_full_memory(self, user_id: str) -> BehavioralMemoryResponse:
        """Fetch profile, suggestions, and daily trend."""
        profile = self._repository.get_behavioral_profile(user_id)
        daily_trend = self._repository.get_daily_summaries(user_id, days=30)
        suggestions = self.generate_suggestions(user_id, profile, daily_trend)
        return BehavioralMemoryResponse(
            user_id=user_id,
            profile=profile,
            suggestions=suggestions,
            daily_trend=daily_trend,
        )

    def get_suggestions_only(self, user_id: str) -> list[ProactiveSuggestion]:
        profile = self._repository.get_behavioral_profile(user_id)
        daily_trend = self._repository.get_daily_summaries(user_id, days=30)
        return self.generate_suggestions(user_id, profile, daily_trend)

    def delete_profile(self, user_id: str) -> ProfileDeleteResponse:
        deleted = self._repository.delete_behavioral_profile(user_id)
        return ProfileDeleteResponse(user_id=user_id, deleted=deleted)

    # ── Daily Summary Recording ──────────────────────────────────────

    def record_daily_summary(self, payload: DailySummaryIn) -> DailySummary:
        """Aggregate snapshots for the given session into a daily summary."""
        history_records, _ = self._repository.get_behavior_history(
            session_id=payload.session_id, limit=500,
        )

        if not history_records:
            summary = DailySummary(
                user_id=payload.user_id,
                session_id=payload.session_id,
                date=payload.date,
                avg_cognitive_load=0.0,
                avg_frustration=0.0,
                avg_attention=0.0,
                snapshot_count=0,
                peak_hour=None,
                dominant_adaptation="resume_normal",
            )
            self._repository.add_daily_summary(summary)
            return summary

        snapshots = [r.snapshot for r in history_records]
        count = len(snapshots)
        avg_cognitive = sum(s.cognitive_load for s in snapshots) / count
        avg_frustration = sum(s.frustration_score for s in snapshots) / count
        avg_attention = sum(s.attention_level for s in snapshots) / count

        # Determine peak hour from snapshot timestamps
        peak_hour = self._peak_hour_from_snapshots(snapshots)

        # Dominant adaptation action
        adaptation_counts: Counter[str] = Counter(
            s.recommended_adaptation for s in snapshots
        )
        dominant = adaptation_counts.most_common(1)[0][0]

        summary = DailySummary(
            user_id=payload.user_id,
            session_id=payload.session_id,
            date=payload.date,
            avg_cognitive_load=round(avg_cognitive, 4),
            avg_frustration=round(avg_frustration, 4),
            avg_attention=round(avg_attention, 4),
            snapshot_count=count,
            peak_hour=peak_hour,
            dominant_adaptation=dominant,
        )
        self._repository.add_daily_summary(summary)
        return summary

    # ── Pattern Detection ────────────────────────────────────────────

    @staticmethod
    def _detect_peak_focus_hours(
        snapshots: list[BehaviorSnapshot], timestamps_iso: list[str],
    ) -> list[int]:
        """Find hours of day where cognitive load is lowest (best focus)."""
        hour_loads: defaultdict[int, list[float]] = defaultdict(list)
        for snapshot, ts_iso in zip(snapshots, timestamps_iso):
            try:
                ts = datetime.fromisoformat(ts_iso)
                hour_loads[ts.hour].append(snapshot.cognitive_load)
            except (ValueError, AttributeError):
                continue

        if not hour_loads:
            return []

        hour_avg = {
            hour: sum(loads) / len(loads) for hour, loads in hour_loads.items()
        }
        global_avg = sum(hour_avg.values()) / len(hour_avg)
        # Peak focus = hours significantly below average cognitive load
        threshold = global_avg * 0.85
        peak_hours = sorted(h for h, avg in hour_avg.items() if avg <= threshold)
        return peak_hours if peak_hours else [min(hour_avg, key=hour_avg.get)]  # type: ignore[arg-type]

    @staticmethod
    def _detect_stress_triggers(
        snapshots: list[BehaviorSnapshot], timestamps_iso: list[str],
    ) -> dict[str, float]:
        """Identify temporal patterns correlated with high frustration."""
        triggers: dict[str, list[float]] = {
            "morning_sessions": [],
            "afternoon_sessions": [],
            "evening_sessions": [],
            "high_task_switching": [],
            "high_error_rate": [],
        }

        for snapshot, ts_iso in zip(snapshots, timestamps_iso):
            frust = snapshot.frustration_score
            try:
                ts = datetime.fromisoformat(ts_iso)
                hour = ts.hour
            except (ValueError, AttributeError):
                hour = 12  # fallback

            if 5 <= hour < 12:
                triggers["morning_sessions"].append(frust)
            elif 12 <= hour < 18:
                triggers["afternoon_sessions"].append(frust)
            else:
                triggers["evening_sessions"].append(frust)

            if snapshot.task_switches_per_minute > 15:
                triggers["high_task_switching"].append(frust)
            if snapshot.error_rate > 0.15:
                triggers["high_error_rate"].append(frust)

        result: dict[str, float] = {}
        for name, values in triggers.items():
            if values:
                avg_frust = sum(values) / len(values)
                if avg_frust > 0.3:
                    result[name] = round(avg_frust, 4)

        return result

    @staticmethod
    def _detect_preferred_pace(snapshots: list[BehaviorSnapshot]) -> str:
        """Derive preferred pace from dominant adaptation actions."""
        pace_votes = {"slow": 0, "normal": 0, "fast": 0}
        slow_actions = {"reduce_ui_complexity", "pause_notifications", "slow_content_pacing", "enable_focus_mode"}
        fast_actions = {"increase_ui_complexity", "enable_power_features"}

        for s in snapshots:
            action = s.recommended_adaptation
            if action in slow_actions:
                pace_votes["slow"] += 1
            elif action in fast_actions:
                pace_votes["fast"] += 1
            else:
                pace_votes["normal"] += 1

        return max(pace_votes, key=pace_votes.get)  # type: ignore[arg-type]

    @staticmethod
    def _peak_hour_from_snapshots(snapshots: list[BehaviorSnapshot]) -> int | None:
        """Pick the hour with the best attention level from snapshot timestamps."""
        hour_attention: defaultdict[int, list[float]] = defaultdict(list)
        for snapshot in snapshots:
            try:
                ts = snapshot.updated_at
                hour_attention[ts.hour].append(snapshot.attention_level)
            except (AttributeError, TypeError):
                continue
        if not hour_attention:
            return None
        hour_avg = {h: sum(v) / len(v) for h, v in hour_attention.items()}
        return max(hour_avg, key=hour_avg.get)  # type: ignore[arg-type]

    # ── Proactive Suggestions ────────────────────────────────────────

    def generate_suggestions(
        self,
        user_id: str,
        profile: UserBehavioralProfile | None,
        daily_trend: list[DailySummary],
    ) -> list[ProactiveSuggestion]:
        suggestions: list[ProactiveSuggestion] = []

        if not daily_trend:
            return suggestions

        # 1. Streak stress: consecutive days with high frustration
        streak = self._compute_stress_streak(daily_trend)
        if streak >= 2:
            suggestions.append(
                ProactiveSuggestion(
                    type="streak_stress",
                    severity="warning" if streak < 4 else "critical",
                    message=f"You've had elevated stress for {streak} consecutive days. Consider adjusting your workload or taking a break.",
                    data={"consecutive_days": streak},
                )
            )

        # 2. Burnout risk: rising cognitive load trend
        if len(daily_trend) >= 3:
            trend_direction = self._compute_load_trend(daily_trend)
            if trend_direction > 0.05:
                suggestions.append(
                    ProactiveSuggestion(
                        type="burnout_risk",
                        severity="warning",
                        message="Your cognitive load has been increasing over recent sessions. This may indicate approaching burnout.",
                        data={"trend_slope": round(trend_direction, 4)},
                    )
                )

        # 3. Optimal time suggestion
        if profile and profile.peak_focus_hours:
            hours_str = ", ".join(
                f"{h}:00" for h in sorted(profile.peak_focus_hours)
            )
            suggestions.append(
                ProactiveSuggestion(
                    type="optimal_time",
                    severity="info",
                    message=f"Your peak focus hours are typically around {hours_str}. Schedule demanding tasks during these windows.",
                    data={"peak_hours": profile.peak_focus_hours},
                )
            )

        # 4. Stress trigger awareness
        if profile and profile.stress_triggers:
            top_trigger = max(profile.stress_triggers, key=profile.stress_triggers.get)  # type: ignore[arg-type]
            trigger_score = profile.stress_triggers[top_trigger]
            if trigger_score > 0.5:
                friendly_name = top_trigger.replace("_", " ")
                suggestions.append(
                    ProactiveSuggestion(
                        type="stress_trigger",
                        severity="warning" if trigger_score > 0.7 else "info",
                        message=f"'{friendly_name}' is a recurring stress trigger (avg frustration: {trigger_score:.0%}). Consider mitigating strategies.",
                        data={"trigger": top_trigger, "avg_frustration": trigger_score},
                    )
                )

        return suggestions

    @staticmethod
    def _compute_stress_streak(daily_trend: list[DailySummary]) -> int:
        """Count consecutive most-recent days with avg_frustration > 0.5."""
        # daily_trend is ordered DESC by date
        streak = 0
        for summary in daily_trend:
            if summary.avg_frustration > 0.5:
                streak += 1
            else:
                break
        return streak

    @staticmethod
    def _compute_load_trend(daily_trend: list[DailySummary]) -> float:
        """Simple linear regression slope of cognitive load over recent days.

        Positive slope means load is increasing (bad). Returns slope per day.
        daily_trend is DESC, so we reverse for chronological order.
        """
        ordered = list(reversed(daily_trend))
        n = len(ordered)
        if n < 2:
            return 0.0
        x_mean = (n - 1) / 2.0
        y_mean = sum(s.avg_cognitive_load for s in ordered) / n
        numerator = sum(
            (i - x_mean) * (s.avg_cognitive_load - y_mean)
            for i, s in enumerate(ordered)
        )
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        if denominator == 0:
            return 0.0
        return numerator / denominator
