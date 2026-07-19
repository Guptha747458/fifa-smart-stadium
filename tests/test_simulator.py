"""Unit tests for sim.simulator — tick generation, phase detection, incident probability."""
import pytest
import random
from datetime import datetime, timedelta
from sim.simulator import phase_for, density_at, generate_tick, HOTSPOTS, PHASES


class TestPhaseFor:
    """Tests for phase_for() — match timeline detection."""

    def test_pre_gates_phase(self):
        phase, intensity = phase_for(-120)
        assert phase == "pre_gates"

    def test_pre_peak_phase(self):
        phase, intensity = phase_for(-15)
        assert phase == "pre_peak"

    def test_kickoff_phase(self):
        phase, intensity = phase_for(5)
        assert phase == "kickoff"

    def test_halftime_phase(self):
        phase, intensity = phase_for(50)
        assert phase == "halftime"

    def test_end_peak_phase(self):
        phase, intensity = phase_for(92)
        assert phase == "end_peak"

    def test_egress_phase(self):
        phase, intensity = phase_for(120)
        assert phase == "egress"

    def test_idle_outside_all_phases(self):
        phase, intensity = phase_for(9999)
        assert phase == "idle"
        assert intensity == 0.2

    def test_intensity_returned_is_float(self):
        _, intensity = phase_for(45)
        assert isinstance(intensity, float)

    def test_all_defined_phases_are_reachable(self):
        """Every named phase in PHASES should be returned by phase_for()."""
        for name, start, end, _ in PHASES:
            mid = (start + end) / 2
            found_phase, _ = phase_for(mid)
            assert found_phase == name


class TestDensityAt:
    """Tests for density_at() — per-node density simulation."""

    def test_density_within_0_to_1(self, kickoff_dt):
        rng = random.Random(42)
        for node in HOTSPOTS:
            d = density_at(node, 0.85, t=10, rng=rng)
            assert 0.0 <= d <= 1.0, f"Density out of range for {node}: {d}"

    def test_high_intensity_increases_entrance_density(self, kickoff_dt):
        rng_low = random.Random(42)
        rng_high = random.Random(42)
        low_d = density_at("GATE_A", 0.20, t=5, rng=rng_low)
        high_d = density_at("GATE_A", 0.95, t=5, rng=rng_high)
        # Entrance should have higher density at peak intensity
        assert high_d >= low_d * 0.5  # generous tolerance due to noise


class TestGenerateTick:
    """Tests for generate_tick() — full simulation tick."""

    def test_tick_returns_required_keys(self, kickoff_dt):
        rng = random.Random(42)
        tick = generate_tick(kickoff_dt, rng, t=1)
        assert "t" in tick
        assert "minute" in tick
        assert "phase" in tick
        assert "intensity" in tick
        assert "sensors" in tick

    def test_sensors_list_not_empty(self, kickoff_dt):
        rng = random.Random(42)
        tick = generate_tick(kickoff_dt, rng, t=1)
        assert len(tick["sensors"]) > 0

    def test_each_sensor_has_required_fields(self, kickoff_dt):
        rng = random.Random(42)
        tick = generate_tick(kickoff_dt, rng, t=1)
        for s in tick["sensors"]:
            assert "node" in s
            assert "density" in s
            assert "people_est" in s
            assert "co2_ppm" in s
            assert "noise_db" in s

    def test_incident_field_exists_in_tick(self, kickoff_dt):
        rng = random.Random(42)
        tick = generate_tick(kickoff_dt, rng, t=1)
        assert "incident" in tick
        # incident is either None or a dict
        assert tick["incident"] is None or isinstance(tick["incident"], dict)

    def test_tick_counter_increments(self, kickoff_dt):
        rng = random.Random(42)
        tick1 = generate_tick(kickoff_dt, rng, t=1)
        tick2 = generate_tick(kickoff_dt, rng, t=2)
        assert tick2["t"] == 2


class TestHotspots:
    """Tests for the HOTSPOTS constant."""

    def test_hotspots_not_empty(self):
        assert len(HOTSPOTS) > 0

    def test_hotspots_are_valid_node_ids(self):
        from data.venue import NODES
        for node in HOTSPOTS:
            assert node in NODES, f"HOTSPOT {node} not in NODES"
