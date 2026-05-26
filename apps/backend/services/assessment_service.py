"""Assessment service — scores psychometric instruments and calibrates sensing.

This service:
1. Validates and scores user responses against instrument definitions
2. Generates per-subscale and overall scores with clinical interpretations
3. Tracks assessment history for trend analysis
4. Calibrates real-time sensor estimates against self-report ground truth
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from db.behavior_repository import BehaviorRepository
from models.assessment import (
    AssessmentResult,
    AssessmentSubmission,
    AssessmentTrend,
    INSTRUMENT_CATALOG,
    InstrumentType,
    SubscaleScore,
    TrendPoint,
    WellbeingSnapshot,
)

logger = logging.getLogger(__name__)


# ── Interpretation thresholds ─────────────────────────────────────

_NASA_TLX_INTERP = [
    (0.3, "Low workload — you're well within capacity", "Consider taking on more challenging tasks"),
    (0.55, "Moderate workload — healthy engagement level", "Maintain current pace"),
    (0.75, "High workload — approaching cognitive ceiling", "Consider breaking tasks into smaller chunks"),
    (1.0, "Very high workload — risk of errors and fatigue", "Take a break and reassess priorities"),
]

_PSS4_INTERP = [
    (0.3, "Low stress — feeling in control", "Keep up current habits"),
    (0.55, "Moderate stress — some pressure present", "Consider stress management techniques"),
    (0.75, "High stress — significant pressure detected", "Prioritize rest and delegation"),
    (1.0, "Very high stress — overwhelm likely", "Immediate decompression recommended"),
]

_FLOW_INTERP = [
    (0.3, "Low flow — difficulty concentrating", "Try removing distractions and starting with easier tasks"),
    (0.55, "Moderate flow — some engagement present", "Lean into current activity without task-switching"),
    (0.75, "High flow — strong absorption in work", "Protect this state — minimize interruptions"),
    (1.0, "Peak flow — fully immersed and productive", "Outstanding — let it ride"),
]

_BURNOUT_INTERP = [
    (0.3, "Low burnout risk — healthy engagement", "Continue with regular check-ins"),
    (0.55, "Moderate burnout signs — early warning", "Ensure adequate recovery time between intense periods"),
    (0.75, "High burnout risk — multiple warning signs", "Consider workload reduction and dedicated rest days"),
    (1.0, "Critical burnout indicators — intervention needed", "Strongly recommend professional support and immediate workload changes"),
]

_MOOD_INTERP = [
    (0.3, "Positive mood state — low stress, good energy", "Great baseline for deep work"),
    (0.55, "Neutral mood — functional but not optimal", "Check in again in an hour"),
    (0.75, "Low mood — stress or fatigue present", "Consider a short break or change of activity"),
    (1.0, "Very low mood — significant distress signals", "Take care of yourself first"),
]

_INTERP_MAP = {
    InstrumentType.NASA_TLX: _NASA_TLX_INTERP,
    InstrumentType.PSS4: _PSS4_INTERP,
    InstrumentType.FLOW_SHORT: _FLOW_INTERP,
    InstrumentType.BURNOUT_MICRO: _BURNOUT_INTERP,
    InstrumentType.MOOD_CHECK: _MOOD_INTERP,
}


class AssessmentService:
    """Scores psychometric assessments and manages longitudinal tracking."""

    def __init__(self, repository: BehaviorRepository) -> None:
        self._repository = repository

    def get_instrument(self, instrument_type: InstrumentType):
        """Return the full instrument definition for rendering in the frontend."""
        return INSTRUMENT_CATALOG.get(instrument_type)

    def list_instruments(self):
        """Return all available instruments."""
        return list(INSTRUMENT_CATALOG.values())

    def score(self, submission: AssessmentSubmission) -> AssessmentResult:
        """Validate and score a completed assessment."""
        instrument = INSTRUMENT_CATALOG.get(submission.instrument_type)
        if instrument is None:
            raise ValueError(f"Unknown instrument: {submission.instrument_type}")

        # Validate all required questions are answered
        question_map = {q.id: q for q in instrument.questions}
        for qid in question_map:
            if qid not in submission.responses:
                raise ValueError(f"Missing response for question: {qid}")

        # Validate response ranges
        for qid, value in submission.responses.items():
            if qid not in question_map:
                continue
            q = question_map[qid]
            if value < q.min_value or value > q.max_value:
                raise ValueError(f"Response for {qid} out of range [{q.min_value}, {q.max_value}]: {value}")

        # Score subscales
        subscale_scores = self._score_subscales(instrument, submission.responses)

        # Overall score
        overall, normalized = self._compute_overall(instrument, subscale_scores)

        # Interpretation
        interp, recommendation = self._interpret(instrument.instrument_type, normalized)

        result = AssessmentResult(
            session_id=submission.session_id,
            user_id=submission.user_id,
            instrument_type=submission.instrument_type,
            instrument_name=instrument.name,
            subscale_scores=subscale_scores,
            overall_score=round(overall, 2),
            normalized_score=round(normalized, 4),
            interpretation=interp,
            recommendation=recommendation,
            completed_at=datetime.now(timezone.utc),
        )

        # Persist
        self._repository.save_assessment(result)
        logger.info(
            "Assessment scored: user=%s instrument=%s score=%.2f severity=%s",
            submission.user_id, submission.instrument_type.value, normalized, result.severity,
        )
        return result

    def get_history(
        self,
        user_id: str,
        instrument_type: InstrumentType | None = None,
        limit: int = 50,
    ) -> list[AssessmentResult]:
        """Get assessment history for a user, optionally filtered by instrument."""
        return self._repository.get_assessments(user_id, instrument_type, limit)

    def get_trend(self, user_id: str, instrument_type: InstrumentType) -> AssessmentTrend:
        """Compute trend for a specific instrument over time."""
        results = self._repository.get_assessments(user_id, instrument_type, limit=100)

        points = [
            TrendPoint(
                instrument_type=r.instrument_type,
                score=r.overall_score,
                normalized=r.normalized_score,
                completed_at=r.completed_at,
            )
            for r in results
        ]

        if len(points) < 2:
            direction = "stable"
        else:
            recent = sum(p.normalized for p in points[:3]) / min(3, len(points))
            older = sum(p.normalized for p in points[-3:]) / min(3, len(points))
            diff = recent - older

            # For instruments where high = bad (NASA-TLX, PSS4, Burnout), decreasing is improving
            # For Flow and Mood, increasing is improving
            high_is_bad = instrument_type in (InstrumentType.NASA_TLX, InstrumentType.PSS4, InstrumentType.BURNOUT_MICRO)

            if abs(diff) < 0.05:
                direction = "stable"
            elif (high_is_bad and diff < 0) or (not high_is_bad and diff > 0):
                direction = "improving"
            else:
                direction = "worsening"

        avg = sum(p.normalized for p in points) / len(points) if points else 0.0
        latest = points[0].normalized if points else 0.0

        return AssessmentTrend(
            user_id=user_id,
            instrument_type=instrument_type,
            points=points,
            direction=direction,
            average=round(avg, 4),
            latest=round(latest, 4),
        )

    def compute_wellbeing(self, user_id: str, session_id: str | None = None) -> WellbeingSnapshot:
        """Create a composite wellbeing snapshot combining sensors + self-report.

        This is the key calibration function — it shows the delta between
        what the sensors estimate and what the user actually reports.
        """
        # Get latest sensor data
        sensor_stress = None
        sensor_load = None
        sensor_attention = None

        if session_id:
            emotion = self._repository.get_emotion_state(session_id)
            if emotion:
                sensor_stress = emotion.stress_level
                sensor_load = emotion.cognitive_load
                sensor_attention = emotion.attention_level

        # Get latest self-reports
        stress_reports = self._repository.get_assessments(user_id, InstrumentType.PSS4, limit=1)
        mood_reports = self._repository.get_assessments(user_id, InstrumentType.MOOD_CHECK, limit=1)
        flow_reports = self._repository.get_assessments(user_id, InstrumentType.FLOW_SHORT, limit=1)
        burnout_reports = self._repository.get_assessments(user_id, InstrumentType.BURNOUT_MICRO, limit=1)

        self_stress = stress_reports[0].normalized_score if stress_reports else None
        self_energy = None
        self_flow = flow_reports[0].normalized_score if flow_reports else None
        self_burnout = burnout_reports[0].normalized_score if burnout_reports else None

        if mood_reports:
            # Extract energy subscale from mood check
            for sub in mood_reports[0].subscale_scores:
                if sub.name == "energy":
                    self_energy = sub.normalized
                    break

        # Calibration delta: sensor stress vs self-reported stress
        calibration_delta = None
        if sensor_stress is not None and self_stress is not None:
            calibration_delta = round(sensor_stress - self_stress, 4)

        # Composite wellbeing (lower = better)
        signals = []
        if sensor_stress is not None:
            signals.append(1.0 - sensor_stress)
        if self_stress is not None:
            signals.append(1.0 - self_stress)
        if self_energy is not None:
            signals.append(self_energy)  # high energy = good
        if self_flow is not None:
            signals.append(self_flow)  # high flow = good
        if self_burnout is not None:
            signals.append(1.0 - self_burnout)  # low burnout = good
        if sensor_attention is not None:
            signals.append(sensor_attention)

        composite = sum(signals) / len(signals) if signals else 0.5

        return WellbeingSnapshot(
            user_id=user_id,
            timestamp=datetime.now(timezone.utc),
            sensor_stress=sensor_stress,
            sensor_cognitive_load=sensor_load,
            sensor_attention=sensor_attention,
            self_report_stress=self_stress,
            self_report_energy=self_energy,
            self_report_flow=self_flow,
            self_report_burnout=self_burnout,
            calibration_delta=calibration_delta,
            composite_wellbeing=round(min(1.0, max(0.0, composite)), 4),
        )

    # ── Internal scoring methods ──────────────────────────────────

    def _score_subscales(self, instrument, responses: dict[str, int]) -> list[SubscaleScore]:
        """Group questions by subscale and compute per-subscale scores."""
        subscale_items: dict[str, list[tuple[float, float, float]]] = {}

        for q in instrument.questions:
            if q.id not in responses:
                continue
            raw = responses[q.id]
            # Reverse score if needed
            if q.reverse_scored:
                raw = (q.max_value + q.min_value) - raw
            normalized = (raw - q.min_value) / (q.max_value - q.min_value) if q.max_value > q.min_value else 0
            subscale_items.setdefault(q.subscale, []).append((float(raw), normalized, float(q.max_value)))

        result: list[SubscaleScore] = []
        for name, items in subscale_items.items():
            raw_avg = sum(i[0] for i in items) / len(items)
            norm_avg = sum(i[1] for i in items) / len(items)
            interp_map = _INTERP_MAP.get(instrument.instrument_type, _MOOD_INTERP)
            interp = "Unknown"
            for threshold, label, _ in interp_map:
                if norm_avg <= threshold:
                    interp = label
                    break

            result.append(SubscaleScore(
                name=name,
                raw_score=round(raw_avg, 2),
                normalized=round(min(1.0, max(0.0, norm_avg)), 4),
                interpretation=interp,
            ))

        return result

    def _compute_overall(self, instrument, subscale_scores: list[SubscaleScore]) -> tuple[float, float]:
        """Compute overall score from subscales."""
        if not subscale_scores:
            return 0.0, 0.0

        if instrument.scoring_method == "sum":
            raw_total = sum(s.raw_score for s in subscale_scores)
            norm_avg = sum(s.normalized for s in subscale_scores) / len(subscale_scores)
            return raw_total, min(1.0, max(0.0, norm_avg))
        elif instrument.scoring_method == "profile":
            # For profile instruments, use mean of normalized scores
            norm_avg = sum(s.normalized for s in subscale_scores) / len(subscale_scores)
            raw_avg = sum(s.raw_score for s in subscale_scores) / len(subscale_scores)
            return raw_avg, min(1.0, max(0.0, norm_avg))
        else:  # mean
            raw_avg = sum(s.raw_score for s in subscale_scores) / len(subscale_scores)
            norm_avg = sum(s.normalized for s in subscale_scores) / len(subscale_scores)
            return raw_avg, min(1.0, max(0.0, norm_avg))

    def _interpret(self, instrument_type: InstrumentType, normalized: float) -> tuple[str, str]:
        """Get interpretation and recommendation for a normalized score."""
        interp_map = _INTERP_MAP.get(instrument_type, _MOOD_INTERP)
        for threshold, interp, recommendation in interp_map:
            if normalized <= threshold:
                return interp, recommendation
        return interp_map[-1][1], interp_map[-1][2]
