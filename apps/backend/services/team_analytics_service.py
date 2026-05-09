from __future__ import annotations

import hashlib
import logging
from collections import defaultdict
from datetime import datetime, timezone
from threading import RLock

from db.behavior_repository import BehaviorRepository
from models.team import (
    TeamAggregate,
    TeamAnalyticsResponse,
    TeamCreateRequest,
    TeamListResponse,
    TeamMember,
)

logger = logging.getLogger(__name__)

BURNOUT_COGNITIVE_THRESHOLD = 0.65
BURNOUT_FRUSTRATION_THRESHOLD = 0.55
STRESS_HOTSPOT_THRESHOLD = 0.60


class TeamAnalyticsService:
    """Aggregate, anonymized team analytics across users."""

    def __init__(self, repository: BehaviorRepository) -> None:
        self._repository = repository
        self._lock = RLock()
        # In-memory team registry (production would use DB)
        self._teams: dict[str, list[str]] = {}

    def create_team(self, request: TeamCreateRequest) -> TeamAggregate:
        with self._lock:
            self._teams[request.team_id] = list(set(request.user_ids))
        return self.get_analytics(request.team_id).aggregate

    def delete_team(self, team_id: str) -> bool:
        with self._lock:
            return self._teams.pop(team_id, None) is not None

    def list_teams(self) -> TeamListResponse:
        with self._lock:
            team_ids = list(self._teams.keys())
        return TeamListResponse(teams=team_ids, total=len(team_ids))

    def get_analytics(self, team_id: str) -> TeamAnalyticsResponse:
        with self._lock:
            user_ids = self._teams.get(team_id, [])

        if not user_ids:
            return TeamAnalyticsResponse(
                aggregate=TeamAggregate(
                    team_id=team_id, member_count=0,
                    avg_cognitive_load=0, avg_frustration=0, avg_attention=0,
                    total_sessions=0, total_snapshots=0,
                ),
                members=[],
            )

        members: list[TeamMember] = []
        all_loads: list[float] = []
        all_frustrations: list[float] = []
        all_attentions: list[float] = []
        total_sessions = 0
        total_snapshots = 0
        hour_counts: dict[int, int] = defaultdict(int)
        burnout_risk_count = 0
        stress_hotspots: set[str] = set()

        for user_id in user_ids:
            # Anonymize user_id with one-way hash
            anon_id = hashlib.sha256(f"flowstate:{user_id}".encode()).hexdigest()[:12]

            # Get user's session data
            session_ids = self._repository.get_session_ids_for_user(user_id)
            sessions = self._repository.list_sessions(user_id)
            session_count = len(sessions)
            total_sessions += session_count

            # Get snapshots across all sessions
            user_loads: list[float] = []
            user_frustrations: list[float] = []
            user_attentions: list[float] = []
            user_snapshot_count = 0

            for sid in session_ids:
                snapshots = self._repository.get_snapshots_for_session(sid, limit=200)
                for snap in snapshots:
                    user_loads.append(snap.cognitive_load)
                    user_frustrations.append(snap.frustration_score)
                    user_attentions.append(snap.attention_level)
                    user_snapshot_count += 1
                    # Track peak hours
                    hour_counts[snap.updated_at.hour] += 1

            total_snapshots += user_snapshot_count

            avg_load = sum(user_loads) / len(user_loads) if user_loads else 0
            avg_frust = sum(user_frustrations) / len(user_frustrations) if user_frustrations else 0
            avg_att = sum(user_attentions) / len(user_attentions) if user_attentions else 0

            all_loads.extend(user_loads)
            all_frustrations.extend(user_frustrations)
            all_attentions.extend(user_attentions)

            # Detect burnout risk
            if avg_load >= BURNOUT_COGNITIVE_THRESHOLD and avg_frust >= BURNOUT_FRUSTRATION_THRESHOLD:
                burnout_risk_count += 1

            # Detect stress hotspots from behavioral profile
            profile = self._repository.get_behavioral_profile(user_id)
            peak_hours: list[int] = []
            if profile:
                peak_hours = profile.peak_focus_hours
                for trigger, score in profile.stress_triggers.items():
                    if score >= STRESS_HOTSPOT_THRESHOLD:
                        stress_hotspots.add(trigger)

            members.append(TeamMember(
                anonymous_id=anon_id,
                avg_cognitive_load=round(avg_load, 3),
                avg_frustration=round(avg_frust, 3),
                avg_attention=round(avg_att, 3),
                total_sessions=session_count,
                total_snapshots=user_snapshot_count,
                peak_focus_hours=peak_hours,
            ))

        # Team-level aggregates
        team_avg_load = sum(all_loads) / len(all_loads) if all_loads else 0
        team_avg_frust = sum(all_frustrations) / len(all_frustrations) if all_frustrations else 0
        team_avg_att = sum(all_attentions) / len(all_attentions) if all_attentions else 0

        # Top 3 peak hours across team
        sorted_hours = sorted(hour_counts.items(), key=lambda x: x[1], reverse=True)
        team_peak = [h for h, _ in sorted_hours[:3]]

        aggregate = TeamAggregate(
            team_id=team_id,
            member_count=len(user_ids),
            avg_cognitive_load=round(team_avg_load, 3),
            avg_frustration=round(team_avg_frust, 3),
            avg_attention=round(team_avg_att, 3),
            total_sessions=total_sessions,
            total_snapshots=total_snapshots,
            stress_hotspots=sorted(stress_hotspots),
            team_peak_hours=team_peak,
            burnout_risk_count=burnout_risk_count,
        )

        logger.info(
            "team_analytics_computed team_id=%s members=%d sessions=%d snapshots=%d burnout_risk=%d",
            team_id, len(user_ids), total_sessions, total_snapshots, burnout_risk_count,
        )

        return TeamAnalyticsResponse(aggregate=aggregate, members=members)
