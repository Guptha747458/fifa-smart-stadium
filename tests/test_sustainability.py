"""Unit tests for core.sustainability — metrics calculation and recycling guidance."""
import pytest
from core.sustainability import get_metrics, get_recycling_guidance


class TestGetMetrics:
    """Tests for the get_metrics() function."""

    def test_returns_all_required_keys(self):
        metrics = get_metrics(minute=45.0, intensity=0.70)
        assert "energy_kw" in metrics
        assert "water_l_min" in metrics
        assert "waste_rate_kg_min" in metrics
        assert "diversion_rate_pct" in metrics
        assert "cumulative" in metrics

    def test_cumulative_contains_all_keys(self):
        metrics = get_metrics(minute=45.0, intensity=0.70)
        cum = metrics["cumulative"]
        assert "waste_kg" in cum
        assert "recycled_kg" in cum
        assert "co2_saved_kg" in cum

    def test_energy_scales_with_intensity(self):
        low = get_metrics(minute=30.0, intensity=0.20)
        high = get_metrics(minute=30.0, intensity=0.90)
        assert high["energy_kw"] > low["energy_kw"]

    def test_water_scales_with_intensity(self):
        low = get_metrics(minute=30.0, intensity=0.20)
        high = get_metrics(minute=30.0, intensity=0.90)
        assert high["water_l_min"] > low["water_l_min"]

    def test_no_negative_values(self):
        metrics = get_metrics(minute=0.0, intensity=0.0)
        assert metrics["energy_kw"] >= 0
        assert metrics["water_l_min"] >= 0
        assert metrics["waste_rate_kg_min"] >= 0

    def test_diversion_rate_is_percentage(self):
        metrics = get_metrics(minute=60.0, intensity=0.75)
        # Should be a percent value roughly between 35 and 55
        assert 20.0 <= metrics["diversion_rate_pct"] <= 80.0

    def test_recycled_kg_less_than_or_equal_to_waste_kg(self):
        metrics = get_metrics(minute=90.0, intensity=0.98)
        assert metrics["cumulative"]["recycled_kg"] <= metrics["cumulative"]["waste_kg"]

    def test_co2_saved_proportional_to_recycled(self):
        metrics = get_metrics(minute=90.0, intensity=0.98)
        expected_co2 = int(metrics["cumulative"]["recycled_kg"] * 2.1)
        assert abs(metrics["cumulative"]["co2_saved_kg"] - expected_co2) <= 2  # rounding tolerance


class TestGetRecyclingGuidance:
    """Tests for the get_recycling_guidance() function."""

    def test_plastic_bottle_goes_to_recycling(self):
        result = get_recycling_guidance("plastic bottle")
        assert "Recycling" in result["bin"]
        assert result["points"] > 0

    def test_aluminum_can_goes_to_recycling(self):
        result = get_recycling_guidance("aluminum can")
        assert "Recycling" in result["bin"]

    def test_hot_dog_wrapper_goes_to_compost(self):
        result = get_recycling_guidance("hot dog wrapper")
        assert "Compost" in result["bin"]
        assert result["points"] > 0

    def test_food_scraps_go_to_compost(self):
        result = get_recycling_guidance("food")
        assert "Compost" in result["bin"]

    def test_unknown_item_goes_to_landfill(self):
        result = get_recycling_guidance("mystery item xyz")
        assert "Landfill" in result["bin"]

    def test_returns_tip_string(self):
        result = get_recycling_guidance("cup")
        assert isinstance(result["tip"], str)
        assert len(result["tip"]) > 0

    def test_returns_co2_saved_value(self):
        result = get_recycling_guidance("glass bottle")
        assert "co2_saved_g" in result
        assert isinstance(result["co2_saved_g"], int)

    def test_item_name_preserved_lowercase(self):
        result = get_recycling_guidance("  Plastic Bottle  ")
        assert result["item"] == "plastic bottle"
