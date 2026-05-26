"""Tests for the psychometric assessment system."""

from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient


# ── Assessment Service Tests ─────────────────────────────────────

class TestAssessmentService:
    def setup_method(self):
        self._db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self._db_file.close()
        db_url = f"sqlite:///{self._db_file.name}"

        from db.behavior_repository import BehaviorRepository
        from services.assessment_service import AssessmentService

        self.repo = BehaviorRepository(db_url)
        self.repo.initialize()
        self.service = AssessmentService(self.repo)

    def teardown_method(self):
        try:
            os.unlink(self._db_file.name)
        except PermissionError:
            pass

    def test_list_instruments(self):
        instruments = self.service.list_instruments()
        assert len(instruments) == 5
        names = {i.instrument_type.value for i in instruments}
        assert "nasa_tlx" in names
        assert "pss4" in names
        assert "flow_short" in names
        assert "burnout_micro" in names
        assert "mood_check" in names

    def test_get_instrument(self):
        from models.assessment import InstrumentType
        inst = self.service.get_instrument(InstrumentType.NASA_TLX)
        assert inst is not None
        assert inst.name == "NASA Task Load Index"
        assert len(inst.questions) == 6

    def test_score_nasa_tlx(self):
        from models.assessment import AssessmentSubmission, InstrumentType
        submission = AssessmentSubmission(
            session_id="test-sess",
            user_id="test-user",
            instrument_type=InstrumentType.NASA_TLX,
            responses={
                "tlx_mental": 15,
                "tlx_physical": 5,
                "tlx_temporal": 12,
                "tlx_performance": 4,    # reverse scored
                "tlx_effort": 14,
                "tlx_frustration": 10,
            },
        )
        result = self.service.score(submission)
        assert result.instrument_type == InstrumentType.NASA_TLX
        assert result.user_id == "test-user"
        assert 0 <= result.normalized_score <= 1
        assert result.overall_score > 0
        assert len(result.subscale_scores) > 0
        assert result.interpretation != ""
        assert result.recommendation != ""
        assert result.severity in ("low", "moderate", "high", "critical")

    def test_score_pss4(self):
        from models.assessment import AssessmentSubmission, InstrumentType
        submission = AssessmentSubmission(
            session_id="test-sess",
            user_id="test-user",
            instrument_type=InstrumentType.PSS4,
            responses={
                "pss_unable_control": 3,
                "pss_confident": 1,       # reverse scored
                "pss_going_your_way": 1,   # reverse scored
                "pss_difficulties_piling": 3,
            },
        )
        result = self.service.score(submission)
        assert result.instrument_type == InstrumentType.PSS4
        assert result.normalized_score > 0.5  # high stress

    def test_score_flow_short(self):
        from models.assessment import AssessmentSubmission, InstrumentType
        submission = AssessmentSubmission(
            session_id="test-sess",
            user_id="test-user",
            instrument_type=InstrumentType.FLOW_SHORT,
            responses={
                "flow_absorbed": 6,
                "flow_thoughts": 5,
                "flow_not_notice": 6,
                "flow_difficulty": 5,
                "flow_mind_clear": 6,
                "flow_right_words": 5,
                "flow_knew_what": 6,
                "flow_control": 5,
                "flow_demand_skill": 6,
                "flow_effortless": 5,
            },
        )
        result = self.service.score(submission)
        assert result.instrument_type == InstrumentType.FLOW_SHORT
        assert result.normalized_score > 0.6  # high flow

    def test_score_burnout_micro(self):
        from models.assessment import AssessmentSubmission, InstrumentType
        submission = AssessmentSubmission(
            session_id="test-sess",
            user_id="test-user",
            instrument_type=InstrumentType.BURNOUT_MICRO,
            responses={
                "bo_emotionally_drained": 6,
                "bo_end_of_rope": 5,
                "bo_dont_care": 4,
                "bo_accomplishment": 2,   # reverse scored
                "bo_energy": 2,           # reverse scored
            },
        )
        result = self.service.score(submission)
        assert result.instrument_type == InstrumentType.BURNOUT_MICRO
        assert result.normalized_score > 0.5  # high burnout

    def test_score_mood_check(self):
        from models.assessment import AssessmentSubmission, InstrumentType
        submission = AssessmentSubmission(
            session_id="test-sess",
            user_id="test-user",
            instrument_type=InstrumentType.MOOD_CHECK,
            responses={
                "mood_energy": 7,
                "mood_focus": 8,
                "mood_stress": 3,
                "mood_motivation": 8,
                "mood_satisfaction": 7,
            },
        )
        result = self.service.score(submission)
        assert result.instrument_type == InstrumentType.MOOD_CHECK
        assert len(result.subscale_scores) == 5

    def test_missing_response_raises(self):
        from models.assessment import AssessmentSubmission, InstrumentType
        submission = AssessmentSubmission(
            session_id="test-sess",
            user_id="test-user",
            instrument_type=InstrumentType.NASA_TLX,
            responses={"tlx_mental": 10},  # missing 5 others
        )
        with pytest.raises(ValueError, match="Missing response"):
            self.service.score(submission)

    def test_out_of_range_raises(self):
        from models.assessment import AssessmentSubmission, InstrumentType
        submission = AssessmentSubmission(
            session_id="test-sess",
            user_id="test-user",
            instrument_type=InstrumentType.NASA_TLX,
            responses={
                "tlx_mental": 99,  # max is 21
                "tlx_physical": 5,
                "tlx_temporal": 12,
                "tlx_performance": 4,
                "tlx_effort": 14,
                "tlx_frustration": 10,
            },
        )
        with pytest.raises(ValueError, match="out of range"):
            self.service.score(submission)

    def test_persistence_and_history(self):
        from models.assessment import AssessmentSubmission, InstrumentType
        for i in range(3):
            self.service.score(AssessmentSubmission(
                session_id=f"sess-{i}",
                user_id="persist-user",
                instrument_type=InstrumentType.MOOD_CHECK,
                responses={
                    "mood_energy": 5 + i,
                    "mood_focus": 5 + i,
                    "mood_stress": 5 - i,
                    "mood_motivation": 5 + i,
                    "mood_satisfaction": 5 + i,
                },
            ))
        results = self.service.get_history("persist-user")
        assert len(results) == 3

    def test_history_filter_by_instrument(self):
        from models.assessment import AssessmentSubmission, InstrumentType
        self.service.score(AssessmentSubmission(
            session_id="s1", user_id="filter-user",
            instrument_type=InstrumentType.MOOD_CHECK,
            responses={"mood_energy": 5, "mood_focus": 5, "mood_stress": 5, "mood_motivation": 5, "mood_satisfaction": 5},
        ))
        self.service.score(AssessmentSubmission(
            session_id="s2", user_id="filter-user",
            instrument_type=InstrumentType.PSS4,
            responses={"pss_unable_control": 2, "pss_confident": 2, "pss_going_your_way": 2, "pss_difficulties_piling": 2},
        ))
        mood_only = self.service.get_history("filter-user", InstrumentType.MOOD_CHECK)
        assert len(mood_only) == 1
        assert mood_only[0].instrument_type == InstrumentType.MOOD_CHECK

    def test_trend_analysis(self):
        from models.assessment import AssessmentSubmission, InstrumentType
        # Create improving trend (decreasing stress)
        for stress_level in [3, 3, 2, 1, 1]:
            self.service.score(AssessmentSubmission(
                session_id="trend-s", user_id="trend-user",
                instrument_type=InstrumentType.PSS4,
                responses={
                    "pss_unable_control": stress_level,
                    "pss_confident": 4 - stress_level,
                    "pss_going_your_way": 4 - stress_level,
                    "pss_difficulties_piling": stress_level,
                },
            ))
        trend = self.service.get_trend("trend-user", InstrumentType.PSS4)
        assert trend.user_id == "trend-user"
        assert len(trend.points) == 5
        assert trend.direction in ("improving", "stable", "worsening")

    def test_severity_levels(self):
        from models.assessment import AssessmentSubmission, InstrumentType

        # Low stress = low severity
        result_low = self.service.score(AssessmentSubmission(
            session_id="sev-1", user_id="sev-user",
            instrument_type=InstrumentType.PSS4,
            responses={"pss_unable_control": 0, "pss_confident": 4, "pss_going_your_way": 4, "pss_difficulties_piling": 0},
        ))
        assert result_low.severity == "low"

        # High stress = high/critical severity
        result_high = self.service.score(AssessmentSubmission(
            session_id="sev-2", user_id="sev-user",
            instrument_type=InstrumentType.PSS4,
            responses={"pss_unable_control": 4, "pss_confident": 0, "pss_going_your_way": 0, "pss_difficulties_piling": 4},
        ))
        assert result_high.severity in ("high", "critical")

    def test_wellbeing_snapshot(self):
        from models.assessment import AssessmentSubmission, InstrumentType
        self.service.score(AssessmentSubmission(
            session_id="wb-s", user_id="wb-user",
            instrument_type=InstrumentType.PSS4,
            responses={"pss_unable_control": 2, "pss_confident": 3, "pss_going_your_way": 3, "pss_difficulties_piling": 1},
        ))
        self.service.score(AssessmentSubmission(
            session_id="wb-s", user_id="wb-user",
            instrument_type=InstrumentType.MOOD_CHECK,
            responses={"mood_energy": 7, "mood_focus": 8, "mood_stress": 3, "mood_motivation": 7, "mood_satisfaction": 6},
        ))
        snapshot = self.service.compute_wellbeing("wb-user")
        assert snapshot.user_id == "wb-user"
        assert snapshot.self_report_stress is not None
        assert 0 <= snapshot.composite_wellbeing <= 1


# ── API Integration Tests ────────────────────────────────────────

@pytest.fixture
def client():
    os.environ["enable_auth"] = "false"
    from config import get_settings
    get_settings.cache_clear()
    from main import app
    with TestClient(app) as c:
        yield c
    os.environ.pop("enable_auth", None)
    get_settings.cache_clear()


class TestAssessmentAPI:
    def test_list_instruments(self, client: TestClient):
        resp = client.get("/api/v1/assessments/instruments")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["instruments"]) == 5

    def test_get_instrument_detail(self, client: TestClient):
        resp = client.get("/api/v1/assessments/instruments/nasa_tlx")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "NASA Task Load Index"
        assert len(data["questions"]) == 6

    def test_submit_and_score(self, client: TestClient):
        resp = client.post("/api/v1/assessments/submit", json={
            "session_id": "api-s1",
            "user_id": "api-user-1",
            "instrument_type": "mood_check",
            "responses": {
                "mood_energy": 7,
                "mood_focus": 8,
                "mood_stress": 4,
                "mood_motivation": 6,
                "mood_satisfaction": 7,
            },
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["instrument_type"] == "mood_check"
        assert 0 <= data["normalized_score"] <= 1
        assert "severity" in data
        assert len(data["subscale_scores"]) == 5

    def test_submit_validation_error(self, client: TestClient):
        resp = client.post("/api/v1/assessments/submit", json={
            "session_id": "api-s2",
            "user_id": "api-user-2",
            "instrument_type": "nasa_tlx",
            "responses": {"tlx_mental": 10},
        })
        # Should return 500 or 422 due to validation error
        assert resp.status_code in (422, 500)

    def test_history(self, client: TestClient):
        import uuid
        uid = f"hist-{uuid.uuid4().hex[:8]}"
        for i in range(3):
            client.post("/api/v1/assessments/submit", json={
                "session_id": f"h-{i}",
                "user_id": uid,
                "instrument_type": "mood_check",
                "responses": {"mood_energy": 5, "mood_focus": 5, "mood_stress": 5, "mood_motivation": 5, "mood_satisfaction": 5},
            })
        resp = client.get(f"/api/v1/assessments/history/{uid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 3

    def test_trend(self, client: TestClient):
        import uuid
        uid = f"trend-{uuid.uuid4().hex[:8]}"
        for i in range(3):
            client.post("/api/v1/assessments/submit", json={
                "session_id": f"t-{i}",
                "user_id": uid,
                "instrument_type": "pss4",
                "responses": {"pss_unable_control": i, "pss_confident": 3, "pss_going_your_way": 3, "pss_difficulties_piling": i},
            })
        resp = client.get(f"/api/v1/assessments/trend/{uid}/pss4")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == uid
        assert len(data["points"]) == 3

    def test_wellbeing(self, client: TestClient):
        import uuid
        uid = f"wb-{uuid.uuid4().hex[:8]}"
        resp = client.get(f"/api/v1/assessments/wellbeing/{uid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == uid
        assert 0 <= data["composite_wellbeing"] <= 1
