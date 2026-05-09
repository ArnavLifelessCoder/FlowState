from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from threading import RLock

from models.behavior import BehaviorSnapshot
from models.notification import (
    GateDecision,
    GatingPolicy,
    NotificationGateResult,
    NotificationPriority,
    NotificationQueueResponse,
    NotificationRequest,
    NotificationStats,
    QueuedNotification,
)
from services.behavior_session_service import BehaviorSessionService

logger = logging.getLogger(__name__)


class NotificationGatingService:
    """Evaluates notifications against cognitive state and gates delivery.

    Decisions:
      - DELIVER: user is in a good state, send immediately.
      - QUEUE: user is moderately loaded, hold for later.
      - SUPPRESS: user is highly stressed/loaded, drop the notification.
      - CRITICAL notifications always bypass the gate (configurable).
    """

    def __init__(
        self,
        behavior_sessions: BehaviorSessionService,
        policy: GatingPolicy | None = None,
    ) -> None:
        self._behavior_sessions = behavior_sessions
        self._policy = policy or GatingPolicy()
        self._lock = RLock()
        # In-memory queue per session (production would use DB/Redis)
        self._queues: dict[str, list[QueuedNotification]] = defaultdict(list)
        self._stats: dict[str, dict[str, int]] = defaultdict(
            lambda: {"total_evaluated": 0, "delivered": 0, "queued": 0, "suppressed": 0}
        )
        self._next_id = 1

    def evaluate(self, request: NotificationRequest) -> NotificationGateResult:
        """Evaluate a notification against current cognitive state."""
        snapshot = self._behavior_sessions.current(request.session_id)
        decision, reason = self._gate(request, snapshot)

        with self._lock:
            self._stats[request.session_id]["total_evaluated"] += 1
            stats_key = {"deliver": "delivered", "queue": "queued", "suppress": "suppressed"}[decision.value]
            self._stats[request.session_id][stats_key] += 1

            if decision == GateDecision.QUEUE:
                queued = QueuedNotification(
                    id=self._next_id,
                    notification=request,
                    reason=reason,
                    queued_at=datetime.now(timezone.utc),
                )
                self._next_id += 1
                self._queues[request.session_id].append(queued)

        logger.info(
            "notification_gated session_id=%s decision=%s priority=%s reason=%s",
            request.session_id, decision.value, request.priority.value, reason,
        )

        return NotificationGateResult(
            notification=request,
            decision=decision,
            reason=reason,
            cognitive_load=snapshot.cognitive_load,
            frustration_score=snapshot.frustration_score,
            attention_level=snapshot.attention_level,
        )

    def _gate(
        self, request: NotificationRequest, snapshot: BehaviorSnapshot,
    ) -> tuple[GateDecision, str]:
        """Core gating logic."""
        p = self._policy

        # Critical notifications always pass through (if configured)
        if request.priority == NotificationPriority.CRITICAL and p.always_deliver_critical:
            return GateDecision.DELIVER, "critical priority bypasses gate"

        # SUPPRESS: very high cognitive load or frustration
        if snapshot.cognitive_load >= p.suppress_cognitive_load:
            return GateDecision.SUPPRESS, f"cognitive load {snapshot.cognitive_load:.2f} >= {p.suppress_cognitive_load:.2f}"

        if snapshot.frustration_score >= p.suppress_frustration:
            return GateDecision.SUPPRESS, f"frustration {snapshot.frustration_score:.2f} >= {p.suppress_frustration:.2f}"

        # QUEUE: moderate cognitive load while attention is high (deep focus)
        if snapshot.cognitive_load >= p.queue_cognitive_load and snapshot.attention_level >= p.queue_attention:
            return GateDecision.QUEUE, f"deep focus detected (load={snapshot.cognitive_load:.2f}, attention={snapshot.attention_level:.2f})"

        # HIGH priority gets delivered even at moderate load
        if request.priority == NotificationPriority.HIGH:
            return GateDecision.DELIVER, "high priority notification"

        # QUEUE: moderate cognitive load for normal/low priority
        if snapshot.cognitive_load >= p.queue_cognitive_load:
            if request.priority == NotificationPriority.LOW:
                return GateDecision.QUEUE, f"low priority deferred at moderate load ({snapshot.cognitive_load:.2f})"

        # Default: deliver
        return GateDecision.DELIVER, "cognitive state permits delivery"

    def get_queued(self, session_id: str, pending_only: bool = True) -> NotificationQueueResponse:
        """Get queued notifications for a session."""
        with self._lock:
            items = self._queues.get(session_id, [])
            if pending_only:
                items = [q for q in items if not q.delivered]
        return NotificationQueueResponse(
            session_id=session_id, queued=items, total=len(items),
        )

    def flush_queue(self, session_id: str) -> list[QueuedNotification]:
        """Mark all pending queued notifications as delivered and return them."""
        now = datetime.now(timezone.utc)
        flushed: list[QueuedNotification] = []
        with self._lock:
            for item in self._queues.get(session_id, []):
                if not item.delivered:
                    item.delivered = True
                    item.delivered_at = now
                    flushed.append(item)
            self._stats[session_id]["delivered"] += len(flushed)
        logger.info("notification_queue_flushed session_id=%s count=%d", session_id, len(flushed))
        return flushed

    def get_stats(self, session_id: str) -> NotificationStats:
        """Get notification gating statistics for a session."""
        with self._lock:
            s = self._stats[session_id]
        return NotificationStats(
            session_id=session_id,
            total_evaluated=s["total_evaluated"],
            delivered=s["delivered"],
            queued=s["queued"],
            suppressed=s["suppressed"],
        )

    def update_policy(self, policy: GatingPolicy) -> GatingPolicy:
        """Update the gating policy thresholds."""
        self._policy = policy
        logger.info("notification_policy_updated suppress_load=%.2f suppress_frust=%.2f", policy.suppress_cognitive_load, policy.suppress_frustration)
        return self._policy

    def get_policy(self) -> GatingPolicy:
        return self._policy
