"""Unit tests for core.crowd — crowd analysis and trend prediction engine."""
import pytest
from core.crowd import analyze, predict_trend, DENSITY_WARN, DENSITY_CRIT


class TestAnalyze:
    """Tests for the analyze() crowd management function."""

    def test_returns_expected_keys(self, sample_sensors):
        result = analyze(sample_sensors, phase="halftime", intensity=0.90)
        assert "phase" in result
        assert "intensity" in result
        assert "hotspots" in result
        assert "alerts" in result
        assert "summary" in result

    def test_phase_and_intensity_propagated(self, sample_sensors):
        result = analyze(sample_sensors, phase="kickoff", intensity=0.95)
        assert result["phase"] == "kickoff"
        assert result["intensity"] == 0.95

    def test_critical_alert_generated_above_threshold(self, sample_sensors):
        """GATE_A density=0.95 should generate a critical alert."""
        result = analyze(sample_sensors, phase="halftime", intensity=0.90)
        critical_nodes = [a["node"] for a in result["alerts"] if a["level"] == "critical"]
        assert "GATE_A" in critical_nodes

    def test_warning_alert_generated_for_concourse_n(self, sample_sensors):
        """CONCOURSE_N density=0.82 should generate a warning (>= 0.75)."""
        result = analyze(sample_sensors, phase="halftime", intensity=0.90)
        warning_nodes = [a["node"] for a in result["alerts"] if a["level"] == "warning"]
        assert "CONCOURSE_N" in warning_nodes

    def test_no_alerts_for_nominal_sensors(self, nominal_sensors):
        result = analyze(nominal_sensors, phase="first_half", intensity=0.70)
        assert result["alerts"] == []

    def test_hotspots_sorted_by_density_descending(self, sample_sensors):
        result = analyze(sample_sensors, phase="halftime", intensity=0.90)
        densities = [h["density"] for h in result["hotspots"]]
        assert densities == sorted(densities, reverse=True)

    def test_alert_includes_reroute_and_staff_guidance(self, sample_sensors):
        result = analyze(sample_sensors, phase="end_peak", intensity=0.98)
        critical = [a for a in result["alerts"] if a["level"] == "critical"]
        assert len(critical) > 0
        assert "reroute" in critical[0]
        assert "staff_guidance" in critical[0]

    def test_summary_contains_critical_keyword_when_critical_alerts(self, sample_sensors):
        result = analyze(sample_sensors, phase="end_peak", intensity=0.98)
        if any(a["level"] == "critical" for a in result["alerts"]):
            assert "CRITICAL" in result["summary"] or "critical" in result["summary"].lower()

    def test_high_intensity_appends_standby_message(self, sample_sensors):
        result = analyze(sample_sensors, phase="kickoff", intensity=0.95)
        assert "standby" in result["summary"].lower() or "reactive" in result["summary"].lower()

    def test_density_threshold_constants_are_sane(self):
        assert 0 < DENSITY_WARN < DENSITY_CRIT < 1.0


class TestPredictTrend:
    """Tests for the predict_trend() function."""

    def test_rising_trend(self):
        history = [0.50, 0.55, 0.62, 0.70, 0.78]
        assert predict_trend(history) == "rising"

    def test_falling_trend(self):
        history = [0.80, 0.72, 0.65, 0.60, 0.50]
        assert predict_trend(history) == "falling"

    def test_stable_trend(self):
        history = [0.65, 0.64, 0.66, 0.65, 0.64]
        assert predict_trend(history) == "stable"

    def test_insufficient_data_returns_correct_string(self):
        assert predict_trend([]) == "insufficient_data"
        assert predict_trend([0.5]) == "insufficient_data"
        assert predict_trend([0.5, 0.6]) == "insufficient_data"

    def test_exactly_three_elements_is_sufficient(self):
        result = predict_trend([0.50, 0.60, 0.70])
        assert result in ("rising", "falling", "stable")
