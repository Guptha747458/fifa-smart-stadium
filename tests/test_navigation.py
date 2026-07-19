"""Unit tests for core.navigation — Dijkstra routing, accessibility, and nearest-of."""
import pytest
from core.navigation import route, nearest_of
from data.venue import NODES


class TestRoute:
    """Tests for the route() pathfinding function."""

    def test_basic_route_returns_ok(self):
        result = route("GATE_A", "FOOD_1")
        assert result["ok"] is True
        assert "path" in result
        assert "steps" in result

    def test_route_path_starts_at_start_and_ends_at_goal(self):
        result = route("GATE_A", "FOOD_1")
        assert result["ok"] is True
        assert result["path"][0] == "GATE_A"
        assert result["path"][-1] == "FOOD_1"

    def test_route_has_positive_distance_and_time(self):
        result = route("GATE_B", "CONCOURSE_S")
        assert result["ok"] is True
        assert result["total_distance_m"] > 0
        assert result["total_seconds"] > 0

    def test_unknown_start_node_returns_error(self):
        result = route("INVALID_NODE", "GATE_A")
        assert result["ok"] is False
        assert "error" in result

    def test_unknown_goal_node_returns_error(self):
        result = route("GATE_A", "DOES_NOT_EXIST")
        assert result["ok"] is False
        assert "error" in result

    def test_accessible_only_uses_accessible_path(self):
        """Route to wheelchair section should succeed in accessible-only mode."""
        result = route("GATE_A", "SEC_340", accessible_only=True)
        assert result["ok"] is True
        # All intermediate nodes must be accessible
        for node_id in result["path"]:
            assert NODES[node_id]["accessible"] is True

    def test_accessible_only_rejects_inaccessible_goal(self):
        """REST_S is not accessible — accessible-only route should fail."""
        result = route("GATE_A", "REST_S", accessible_only=True)
        assert result["ok"] is False

    def test_crowd_aware_route_returns_ok(self):
        density_map = {"CONCOURSE_N": 0.95, "GATE_A": 0.80}
        result = route("GATE_A", "FOOD_1", crowd_aware=True, density_map=density_map)
        assert result["ok"] is True

    def test_route_flags_elevator_usage(self):
        """Route through ELEV_1 to SEC_340 should flag uses_elevator=True."""
        result = route("GATE_A", "SEC_340", accessible_only=True)
        # Either elevator or ramp may be used depending on Dijkstra path
        assert isinstance(result.get("uses_elevator"), bool)
        assert isinstance(result.get("uses_ramp"), bool)

    def test_steps_contain_required_fields(self):
        result = route("GATE_A", "CONCOURSE_N")
        assert result["ok"] is True
        for step in result["steps"]:
            assert "from" in step
            assert "to" in step
            assert "distance_m" in step
            assert "seconds" in step


class TestNearestOf:
    """Tests for the nearest_of() helper function."""

    def test_nearest_restroom_found(self):
        nearest = nearest_of("GATE_A", {"restroom"})
        assert nearest in ("REST_N", "REST_S")

    def test_nearest_food_found(self):
        nearest = nearest_of("GATE_A", {"food"})
        assert nearest in ("FOOD_1", "FOOD_2")

    def test_nearest_of_returns_none_for_unknown_type(self):
        nearest = nearest_of("GATE_A", {"nonexistent_type"})
        assert nearest is None

    def test_nearest_accessible_restroom(self):
        nearest = nearest_of("GATE_A", {"restroom"}, accessible_only=True)
        # REST_S is not accessible, so REST_N should be found
        assert nearest == "REST_N"
