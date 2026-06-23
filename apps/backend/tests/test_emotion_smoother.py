"""Tests for EmotionSmoother — temporal stabilization of the mood stream."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from models.emotion import EmotionState
from services.emotion_smoother import EmotionSmoother


def _state(session_id="s1", emotion="neutral", stress=0.0, load=0.0, attention=0.0,
           burnout=0.0, confidence=0.5, modalities=("vision",)):
    return EmotionState(
        session_id=session_id,
        emotion=emotion,
        confidence=confidence,
        stress_level=stress,
        cognitive_load=load,
        attention_level=attention,
        burnout_risk=burnout,
        modalities_used=list(modalities),
    )


class TestConstruction:
    def test_rejects_bad_alpha(self):
        with pytest.raises(ValueError):
            EmotionSmoother(alpha=0.0)
        with pytest.raises(ValueError):
            EmotionSmoother(alpha=1.5)

    def test_rejects_bad_switch_after(self):
        with pytest.raises(ValueError):
            EmotionSmoother(switch_after=0)


class TestContinuousSmoothing:
    def test_first_sample_passthrough(self):
        sm = EmotionSmoother(alpha=0.4)
        out = sm.smooth(_state(stress=0.8))
        assert out.smoothed is True
        assert out.stress_level == pytest.approx(0.8, abs=1e-4)

    def test_ema_damps_spikes(self):
        sm = EmotionSmoother(alpha=0.4)
        sm.smooth(_state(stress=0.1))
        out = sm.smooth(_state(stress=0.9))
        # Smoothed value should sit between the two, not jump to 0.9.
        assert 0.1 < out.stress_level < 0.9
        assert out.stress_level == pytest.approx(0.4 * 0.9 + 0.6 * 0.1, abs=1e-4)

    def test_converges_to_steady_input(self):
        sm = EmotionSmoother(alpha=0.5)
        out = None
        for _ in range(30):
            out = sm.smooth(_state(stress=0.7))
        assert out.stress_level == pytest.approx(0.7, abs=1e-2)

    def test_values_stay_bounded(self):
        sm = EmotionSmoother()
        out = sm.smooth(_state(stress=1.0, load=1.0, attention=1.0, burnout=1.0, confidence=1.0))
        for f in ("stress_level", "cognitive_load", "attention_level", "burnout_risk", "confidence"):
            assert 0.0 <= getattr(out, f) <= 1.0


class TestLabelHysteresis:
    def test_label_holds_against_single_flip(self):
        sm = EmotionSmoother(switch_after=3, confidence_override=0.99)
        sm.smooth(_state(emotion="calm", confidence=0.5))
        sm.smooth(_state(emotion="calm", confidence=0.5))
        # One off frame should not change the displayed label.
        out = sm.smooth(_state(emotion="angry", confidence=0.5))
        assert out.emotion == "calm"

    def test_label_switches_after_persistence(self):
        sm = EmotionSmoother(switch_after=3, confidence_override=0.99)
        sm.smooth(_state(emotion="calm", confidence=0.5))
        for _ in range(3):
            out = sm.smooth(_state(emotion="angry", confidence=0.5))
        assert out.emotion == "angry"

    def test_high_confidence_overrides_immediately(self):
        sm = EmotionSmoother(switch_after=5, confidence_override=0.85)
        sm.smooth(_state(emotion="calm", confidence=0.5))
        out = sm.smooth(_state(emotion="angry", confidence=0.95))
        assert out.emotion == "angry"

    def test_interrupted_candidate_resets_streak(self):
        sm = EmotionSmoother(switch_after=3, confidence_override=0.99)
        sm.smooth(_state(emotion="calm", confidence=0.5))
        sm.smooth(_state(emotion="angry", confidence=0.5))
        sm.smooth(_state(emotion="sad", confidence=0.5))  # breaks the angry streak
        out = sm.smooth(_state(emotion="angry", confidence=0.5))
        assert out.emotion == "calm"


class TestTrend:
    def test_rising_stress(self):
        sm = EmotionSmoother(alpha=1.0, trend_epsilon=0.04)
        sm.smooth(_state(stress=0.2))
        out = sm.smooth(_state(stress=0.6))
        assert out.trend == "rising"

    def test_falling_stress(self):
        sm = EmotionSmoother(alpha=1.0, trend_epsilon=0.04)
        sm.smooth(_state(stress=0.6))
        out = sm.smooth(_state(stress=0.2))
        assert out.trend == "falling"

    def test_steady_stress(self):
        sm = EmotionSmoother(alpha=1.0, trend_epsilon=0.04)
        sm.smooth(_state(stress=0.5))
        out = sm.smooth(_state(stress=0.51))
        assert out.trend == "steady"


class TestStability:
    def test_steady_signal_is_stable(self):
        sm = EmotionSmoother()
        out = None
        for _ in range(10):
            out = sm.smooth(_state(stress=0.5))
        assert out.stability > 0.9

    def test_noisy_signal_is_unstable(self):
        sm = EmotionSmoother()
        out = None
        for i in range(10):
            out = sm.smooth(_state(stress=0.0 if i % 2 == 0 else 1.0))
        assert out.stability < 0.6


class TestSessionIsolation:
    def test_sessions_do_not_cross_contaminate(self):
        sm = EmotionSmoother(alpha=0.5)
        sm.smooth(_state(session_id="a", stress=0.9))
        out_b = sm.smooth(_state(session_id="b", stress=0.1))
        # Session b's first sample must not inherit a's average.
        assert out_b.stress_level == pytest.approx(0.1, abs=1e-4)

    def test_reset_clears_state(self):
        sm = EmotionSmoother(alpha=0.5)
        sm.smooth(_state(session_id="a", stress=0.9))
        sm.reset("a")
        out = sm.smooth(_state(session_id="a", stress=0.1))
        assert out.stress_level == pytest.approx(0.1, abs=1e-4)


class TestEmptyModalities:
    def test_no_modalities_passthrough(self):
        sm = EmotionSmoother()
        out = sm.smooth(_state(modalities=()))
        assert out.smoothed is True
        assert out.trend == "steady"

    def test_empty_state_does_not_pollute_average(self):
        sm = EmotionSmoother(alpha=0.5)
        sm.smooth(_state(session_id="a", stress=0.8))
        sm.smooth(_state(session_id="a", stress=0.0, modalities=()))  # ignored
        out = sm.smooth(_state(session_id="a", stress=0.8))
        # Average should reflect only the two 0.8 samples, not the empty one.
        assert out.stress_level == pytest.approx(0.8, abs=1e-4)


class TestLRUEviction:
    def test_evicts_oldest_sessions(self):
        sm = EmotionSmoother(max_sessions=3)
        for i in range(5):
            sm.smooth(_state(session_id=f"s{i}", stress=0.5))
        # Only the 3 most recent sessions are retained.
        assert len(sm._sessions) == 3
        assert "s0" not in sm._sessions
        assert "s4" in sm._sessions
