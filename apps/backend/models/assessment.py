"""Psychometric assessment models — validated instruments for baseline calibration.

Instruments implemented:
1. NASA-TLX (Task Load Index) — 6 subscales of workload perception
2. PSS-4 (Perceived Stress Scale) — 4-item stress screening
3. Flow Short Scale — 10-item flow/absorption self-report
4. Burnout Micro-Assessment — 5-item burnout screening (MBI-derived)
5. Custom Mood Check — 5-dimension mood snapshot
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, computed_field


# ── Instrument definitions ────────────────────────────────────────

class InstrumentType(str, Enum):
    NASA_TLX = "nasa_tlx"
    PSS4 = "pss4"
    FLOW_SHORT = "flow_short"
    BURNOUT_MICRO = "burnout_micro"
    MOOD_CHECK = "mood_check"


class AssessmentQuestion(BaseModel):
    """Single question in an instrument."""
    id: str
    text: str
    subscale: str
    min_value: int = 1
    max_value: int = 7
    reverse_scored: bool = False
    anchor_low: str = "Very Low"
    anchor_high: str = "Very High"


class InstrumentDefinition(BaseModel):
    """Full instrument definition with questions and scoring instructions."""
    instrument_type: InstrumentType
    name: str
    description: str
    estimated_seconds: int
    questions: list[AssessmentQuestion]
    scoring_method: str
    research_basis: str


# ── NASA-TLX (6 subscales, each 1-21) ────────────────────────────

NASA_TLX = InstrumentDefinition(
    instrument_type=InstrumentType.NASA_TLX,
    name="NASA Task Load Index",
    description="Measures perceived workload across 6 dimensions. Developed by NASA's Human Performance Research Group. Used in 1000+ studies to validate cognitive load estimates.",
    estimated_seconds=90,
    scoring_method="mean",
    research_basis="Hart & Staveland (1988). Development of NASA-TLX. Advances in Psychology, 52, 139-183.",
    questions=[
        AssessmentQuestion(id="tlx_mental", text="How mentally demanding was this work session?", subscale="mental_demand", min_value=1, max_value=21, anchor_low="Very Low", anchor_high="Very High"),
        AssessmentQuestion(id="tlx_physical", text="How physically demanding was this work session?", subscale="physical_demand", min_value=1, max_value=21, anchor_low="Very Low", anchor_high="Very High"),
        AssessmentQuestion(id="tlx_temporal", text="How hurried or rushed was the pace of work?", subscale="temporal_demand", min_value=1, max_value=21, anchor_low="Very Low", anchor_high="Very High"),
        AssessmentQuestion(id="tlx_performance", text="How successful were you in accomplishing what you were asked to do?", subscale="performance", min_value=1, max_value=21, reverse_scored=True, anchor_low="Perfect", anchor_high="Failure"),
        AssessmentQuestion(id="tlx_effort", text="How hard did you have to work to accomplish your level of performance?", subscale="effort", min_value=1, max_value=21, anchor_low="Very Low", anchor_high="Very High"),
        AssessmentQuestion(id="tlx_frustration", text="How insecure, discouraged, irritated, stressed, and annoyed were you?", subscale="frustration", min_value=1, max_value=21, anchor_low="Very Low", anchor_high="Very High"),
    ],
)

# ── PSS-4 (Perceived Stress Scale — 4 items, 0-4 Likert) ─────────

PSS4 = InstrumentDefinition(
    instrument_type=InstrumentType.PSS4,
    name="Perceived Stress Scale (4-item)",
    description="Brief validated measure of perceived stress over the past work period. Used globally in 500+ occupational health studies.",
    estimated_seconds=45,
    scoring_method="sum",
    research_basis="Cohen, Kamarck & Mermelstein (1983). A global measure of perceived stress. J Health Soc Behav, 24(4), 385-396.",
    questions=[
        AssessmentQuestion(id="pss_unable_control", text="How often have you felt unable to control the important things in your work?", subscale="perceived_helplessness", min_value=0, max_value=4, anchor_low="Never", anchor_high="Very Often"),
        AssessmentQuestion(id="pss_confident", text="How often have you felt confident about your ability to handle your work problems?", subscale="perceived_efficacy", min_value=0, max_value=4, reverse_scored=True, anchor_low="Never", anchor_high="Very Often"),
        AssessmentQuestion(id="pss_going_your_way", text="How often have you felt that things were going your way?", subscale="perceived_efficacy", min_value=0, max_value=4, reverse_scored=True, anchor_low="Never", anchor_high="Very Often"),
        AssessmentQuestion(id="pss_difficulties_piling", text="How often have you felt difficulties were piling up so high that you could not overcome them?", subscale="perceived_helplessness", min_value=0, max_value=4, anchor_low="Never", anchor_high="Very Often"),
    ],
)

# ── Flow Short Scale (10 items, 1-7 Likert) ──────────────────────

FLOW_SHORT = InstrumentDefinition(
    instrument_type=InstrumentType.FLOW_SHORT,
    name="Flow Short Scale",
    description="Measures flow experience — the optimal state of absorption, challenge-skill balance, and intrinsic motivation during work.",
    estimated_seconds=75,
    scoring_method="mean",
    research_basis="Rheinberg, Vollmeyer & Engeser (2003). Die Erfassung des Flow-Erlebens. Diagnostik von Motivation und Selbstkonzept.",
    questions=[
        AssessmentQuestion(id="flow_absorbed", text="I was completely absorbed in what I was doing.", subscale="absorption", min_value=1, max_value=7, anchor_low="Strongly Disagree", anchor_high="Strongly Agree"),
        AssessmentQuestion(id="flow_thoughts", text="My thoughts ran fluidly and smoothly.", subscale="fluency", min_value=1, max_value=7, anchor_low="Strongly Disagree", anchor_high="Strongly Agree"),
        AssessmentQuestion(id="flow_not_notice", text="I didn't notice time passing.", subscale="absorption", min_value=1, max_value=7, anchor_low="Strongly Disagree", anchor_high="Strongly Agree"),
        AssessmentQuestion(id="flow_difficulty", text="I had no difficulty concentrating.", subscale="fluency", min_value=1, max_value=7, anchor_low="Strongly Disagree", anchor_high="Strongly Agree"),
        AssessmentQuestion(id="flow_mind_clear", text="My mind was completely clear.", subscale="fluency", min_value=1, max_value=7, anchor_low="Strongly Disagree", anchor_high="Strongly Agree"),
        AssessmentQuestion(id="flow_right_words", text="The right thoughts occurred of their own accord.", subscale="fluency", min_value=1, max_value=7, anchor_low="Strongly Disagree", anchor_high="Strongly Agree"),
        AssessmentQuestion(id="flow_knew_what", text="I knew what I had to do each step of the way.", subscale="fluency", min_value=1, max_value=7, anchor_low="Strongly Disagree", anchor_high="Strongly Agree"),
        AssessmentQuestion(id="flow_control", text="I felt I had everything under control.", subscale="fluency", min_value=1, max_value=7, anchor_low="Strongly Disagree", anchor_high="Strongly Agree"),
        AssessmentQuestion(id="flow_demand_skill", text="The demands of the task matched my abilities.", subscale="challenge_skill", min_value=1, max_value=7, anchor_low="Strongly Disagree", anchor_high="Strongly Agree"),
        AssessmentQuestion(id="flow_effortless", text="I felt the task was almost effortless.", subscale="challenge_skill", min_value=1, max_value=7, anchor_low="Strongly Disagree", anchor_high="Strongly Agree"),
    ],
)

# ── Burnout Micro-Assessment (5 items, MBI-inspired) ─────────────

BURNOUT_MICRO = InstrumentDefinition(
    instrument_type=InstrumentType.BURNOUT_MICRO,
    name="Burnout Micro-Assessment",
    description="5-item screening for emotional exhaustion, depersonalization, and reduced accomplishment — the three core burnout dimensions.",
    estimated_seconds=40,
    scoring_method="mean",
    research_basis="Maslach & Jackson (1981). The measurement of experienced burnout. J Organizational Behavior, 2(2), 99-113.",
    questions=[
        AssessmentQuestion(id="bo_emotionally_drained", text="I feel emotionally drained from my work.", subscale="exhaustion", min_value=1, max_value=7, anchor_low="Never", anchor_high="Every Day"),
        AssessmentQuestion(id="bo_end_of_rope", text="I feel I'm at the end of my rope.", subscale="exhaustion", min_value=1, max_value=7, anchor_low="Never", anchor_high="Every Day"),
        AssessmentQuestion(id="bo_dont_care", text="I've become more callous toward my work since starting.", subscale="depersonalization", min_value=1, max_value=7, anchor_low="Never", anchor_high="Every Day"),
        AssessmentQuestion(id="bo_accomplishment", text="I feel I'm positively influencing others through my work.", subscale="accomplishment", min_value=1, max_value=7, reverse_scored=True, anchor_low="Never", anchor_high="Every Day"),
        AssessmentQuestion(id="bo_energy", text="I feel full of energy at work.", subscale="accomplishment", min_value=1, max_value=7, reverse_scored=True, anchor_low="Never", anchor_high="Every Day"),
    ],
)

# ── Custom Mood Check (5 dimensions, 1-10 slider) ────────────────

MOOD_CHECK = InstrumentDefinition(
    instrument_type=InstrumentType.MOOD_CHECK,
    name="Quick Mood Check",
    description="5-dimension mood snapshot for rapid self-report. Takes 15 seconds. Designed for frequent use (every 1-2 hours).",
    estimated_seconds=15,
    scoring_method="profile",
    research_basis="Russell (1980). A circumplex model of affect. J Personality and Social Psychology, 39(6), 1161-1178.",
    questions=[
        AssessmentQuestion(id="mood_energy", text="How is your energy level right now?", subscale="energy", min_value=1, max_value=10, anchor_low="Exhausted", anchor_high="Energized"),
        AssessmentQuestion(id="mood_focus", text="How focused do you feel?", subscale="focus", min_value=1, max_value=10, anchor_low="Scattered", anchor_high="Laser-focused"),
        AssessmentQuestion(id="mood_stress", text="How stressed do you feel?", subscale="stress", min_value=1, max_value=10, anchor_low="Calm", anchor_high="Overwhelmed"),
        AssessmentQuestion(id="mood_motivation", text="How motivated are you to work right now?", subscale="motivation", min_value=1, max_value=10, anchor_low="No motivation", anchor_high="Highly driven"),
        AssessmentQuestion(id="mood_satisfaction", text="How satisfied are you with your progress today?", subscale="satisfaction", min_value=1, max_value=10, anchor_low="Dissatisfied", anchor_high="Very satisfied"),
    ],
)

INSTRUMENT_CATALOG: dict[InstrumentType, InstrumentDefinition] = {
    InstrumentType.NASA_TLX: NASA_TLX,
    InstrumentType.PSS4: PSS4,
    InstrumentType.FLOW_SHORT: FLOW_SHORT,
    InstrumentType.BURNOUT_MICRO: BURNOUT_MICRO,
    InstrumentType.MOOD_CHECK: MOOD_CHECK,
}


# ── Request / Response models ────────────────────────────────────

class AssessmentSubmission(BaseModel):
    """User submits responses for an assessment."""
    session_id: str = Field(..., min_length=1, max_length=128)
    user_id: str = Field(..., min_length=1, max_length=128)
    instrument_type: InstrumentType
    responses: dict[str, int] = Field(..., description="Mapping of question_id → response value")


class SubscaleScore(BaseModel):
    name: str
    raw_score: float
    normalized: float = Field(ge=0.0, le=1.0, description="0-1 normalized score")
    interpretation: str


class AssessmentResult(BaseModel):
    """Scored assessment result."""
    id: int = 0
    session_id: str
    user_id: str
    instrument_type: InstrumentType
    instrument_name: str
    subscale_scores: list[SubscaleScore]
    overall_score: float
    normalized_score: float = Field(ge=0.0, le=1.0)
    interpretation: str
    recommendation: str
    completed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @computed_field
    @property
    def severity(self) -> Literal["low", "moderate", "high", "critical"]:
        if self.normalized_score < 0.3:
            return "low"
        if self.normalized_score < 0.55:
            return "moderate"
        if self.normalized_score < 0.75:
            return "high"
        return "critical"


class AssessmentHistoryResponse(BaseModel):
    user_id: str
    assessments: list[AssessmentResult]
    total_count: int


class TrendPoint(BaseModel):
    instrument_type: InstrumentType
    score: float
    normalized: float
    completed_at: datetime


class AssessmentTrend(BaseModel):
    """Trend data for a specific instrument over time."""
    user_id: str
    instrument_type: InstrumentType
    points: list[TrendPoint]
    direction: Literal["improving", "stable", "worsening"]
    average: float
    latest: float


class WellbeingSnapshot(BaseModel):
    """Combined self-report + sensor composite for a point in time."""
    user_id: str
    timestamp: datetime
    sensor_stress: float | None = None
    sensor_cognitive_load: float | None = None
    sensor_attention: float | None = None
    self_report_stress: float | None = None
    self_report_energy: float | None = None
    self_report_flow: float | None = None
    self_report_burnout: float | None = None
    calibration_delta: float | None = Field(
        default=None,
        description="Difference between sensor estimation and self-report (positive = sensor overestimates)",
    )
    composite_wellbeing: float = Field(ge=0.0, le=1.0, default=0.5)
