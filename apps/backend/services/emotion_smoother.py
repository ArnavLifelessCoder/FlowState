"""Temporal smoothing for the multimodal emotion stream.

The per-frame fusion output is noisy: vision/audio inference runs many times a
second and any single frame can swing the instantaneous estimate. Presenting
that raw stream to the user produces a "mood indicator" that flickers between
unrelated emotions several times a second, which reads as random and erodes
trust in the signal.

``EmotionSmoother`` turns that noisy stream into a stable one using two
standard techniques:

* **Exponential moving average (EMA)** on the continuous metrics
  (stress, cognitive load, attention, burnout risk, confidence). EMA is the
  same low-pass filter used for signal smoothing — it weights recent samples
  more heavily while damping single-frame spikes.
* **Hysteresis** on the discrete emotion label. The displayed label only
  changes once a *different* label has shown up consistently (or with very
  high confidence). This stops the label from ping-ponging on every frame.

It also derives a short-term ``trend`` (is stress rising or falling?) and a
``stability`` score (how settled the signal currently is), both of which the
frontend can surface to make the indicator feel intentional rather than jumpy.

State is held per session with simple LRU eviction so long-running servers do
not accumulate unbounded state.
"""

from __future__ import annotations

import logging
from collections import OrderedDict
from dataclasses import dataclass, field

from models.emotion import EmotionState

logger = logging.getLogger(__name__)

# Continuous fields that get EMA-smoothed.
_SMOOTHED_FIELDS = ("stress_level", "cognitive_load", "attention_level", "burnout_risk", "confidence")


@dataclass
class _SessionState:
    """Accumulated smoothing state for a single session."""

    values: dict[str, float] = field(default_factory=dict)
    label: str = "neutral"
    candidate: str | None = None
    candidate_streak: int = 0
    jitter: float = 0.0
    prev_stress: float | None = None
    seen: int = 0


class EmotionSmoother:
    """Stabilizes a per-session stream of fused ``EmotionState`` objects.

    Parameters
    ----------
    alpha:
        EMA weight for new samples (0 < alpha <= 1). Higher = more responsive,
        lower = smoother. 0.4 keeps the signal lively while removing flicker.
    switch_after:
        Number of consecutive frames a new label must persist before it
        replaces the displayed label (hysteresis depth).
    confidence_override:
        A new label is accepted immediately if its confidence is at least this
        high, so genuinely strong signals are not delayed.
    trend_epsilon:
        Minimum change in smoothed stress to count as rising/falling rather
        than steady.
    max_sessions:
        Upper bound on tracked sessions before least-recently-used eviction.
    """

    def __init__(
        self,
        alpha: float = 0.4,
        switch_after: int = 3,
        confidence_override: float = 0.85,
        trend_epsilon: float = 0.04,
        max_sessions: int = 2048,
    ) -> None:
        if not 0.0 < alpha <= 1.0:
            raise ValueError("alpha must be in (0, 1]")
        if switch_after < 1:
            raise ValueError("switch_after must be >= 1")
        self._alpha = alpha
        self._switch_after = switch_after
        self._confidence_override = confidence_override
        self._trend_epsilon = trend_epsilon
        self._max_sessions = max_sessions
        self._sessions: "OrderedDict[str, _SessionState]" = OrderedDict()

    def reset(self, session_id: str) -> None:
        """Drop accumulated state for a session (e.g. when it ends)."""
        self._sessions.pop(session_id, None)

    def smooth(self, state: EmotionState) -> EmotionState:
        """Return a temporally stabilized copy of ``state``.

        The first observation for a session is returned essentially unchanged
        (there is nothing to average against yet) but flagged as smoothed so
        downstream consumers can treat the field set uniformly.
        """
        # A state with no active modalities carries no signal — pass it through
        # untouched and do not let it perturb the accumulated average.
        if not state.modalities_used:
            return state.model_copy(update={"smoothed": True, "stability": 1.0, "trend": "steady"})

        sess = self._sessions.get(state.session_id)
        if sess is None:
            sess = _SessionState()
            self._sessions[state.session_id] = sess
        self._sessions.move_to_end(state.session_id)
        self._evict_if_needed()

        smoothed_values = self._update_values(sess, state)
        label = self._update_label(sess, state)
        trend = self._update_trend(sess, smoothed_values["stress_level"])
        stability = self._update_stability(sess, state)
        sess.seen += 1

        return state.model_copy(
            update={
                **smoothed_values,
                "emotion": label,
                "trend": trend,
                "stability": round(stability, 3),
                "smoothed": True,
            }
        )

    # ── internals ────────────────────────────────────────────────────

    def _update_values(self, sess: _SessionState, state: EmotionState) -> dict[str, float]:
        out: dict[str, float] = {}
        for name in _SMOOTHED_FIELDS:
            new = float(getattr(state, name))
            prev = sess.values.get(name)
            blended = new if prev is None else self._alpha * new + (1.0 - self._alpha) * prev
            blended = max(0.0, min(1.0, blended))
            sess.values[name] = blended
            out[name] = round(blended, 4)
        return out

    def _update_label(self, sess: _SessionState, state: EmotionState) -> str:
        incoming = state.emotion
        if sess.seen == 0:
            sess.label = incoming
            sess.candidate = None
            sess.candidate_streak = 0
            return sess.label

        if incoming == sess.label:
            sess.candidate = None
            sess.candidate_streak = 0
            return sess.label

        # Strong evidence skips the waiting period.
        if state.confidence >= self._confidence_override:
            sess.label = incoming
            sess.candidate = None
            sess.candidate_streak = 0
            return sess.label

        if incoming == sess.candidate:
            sess.candidate_streak += 1
        else:
            sess.candidate = incoming
            sess.candidate_streak = 1

        if sess.candidate_streak >= self._switch_after:
            sess.label = incoming
            sess.candidate = None
            sess.candidate_streak = 0

        return sess.label

    def _update_trend(self, sess: _SessionState, smoothed_stress: float) -> str:
        prev = sess.prev_stress
        sess.prev_stress = smoothed_stress
        if prev is None:
            return "steady"
        delta = smoothed_stress - prev
        if delta > self._trend_epsilon:
            return "rising"
        if delta < -self._trend_epsilon:
            return "falling"
        return "steady"

    def _update_stability(self, sess: _SessionState, state: EmotionState) -> float:
        """Track how much the *raw* signal is moving frame to frame.

        Low movement → high stability. We EMA the absolute change in raw stress
        so a single spike does not collapse the score permanently.
        """
        prev = sess.values.get("_raw_stress")
        raw = float(state.stress_level)
        sess.values["_raw_stress"] = raw
        if prev is None:
            return 1.0
        change = abs(raw - prev)
        sess.jitter = self._alpha * change + (1.0 - self._alpha) * sess.jitter
        # Scale: ~0.33 of full-range jitter per frame drives stability to 0.
        return max(0.0, min(1.0, 1.0 - sess.jitter * 3.0))

    def _evict_if_needed(self) -> None:
        while len(self._sessions) > self._max_sessions:
            evicted, _ = self._sessions.popitem(last=False)
            logger.debug("EmotionSmoother evicted session state: %s", evicted)
