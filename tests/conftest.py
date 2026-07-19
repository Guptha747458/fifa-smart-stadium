"""Shared fixtures for StadiumGenius AI test suite."""
import pytest
from datetime import datetime, timedelta, timezone


@pytest.fixture
def sample_sensors():
    """A realistic set of sensor readings covering all density levels."""
    return [
        {"node": "GATE_A",      "density": 0.95, "people_est": 1425},
        {"node": "CONCOURSE_N", "density": 0.82, "people_est": 1230},
        {"node": "CONCOURSE_E", "density": 0.60, "people_est": 900},
        {"node": "CONCOURSE_S", "density": 0.45, "people_est": 675},
        {"node": "CONCOURSE_W", "density": 0.30, "people_est": 450},
        {"node": "FOOD_1",      "density": 0.70, "people_est": 350},
        {"node": "FOOD_2",      "density": 0.55, "people_est": 275},
        {"node": "REST_N",      "density": 0.20, "people_est": 60},
        {"node": "SEC_101",     "density": 0.10, "people_est": 100},
        {"node": "TRANSIT_HUB", "density": 0.88, "people_est": 1320},
    ]


@pytest.fixture
def nominal_sensors():
    """All sensors below warning threshold."""
    return [
        {"node": "GATE_A",      "density": 0.40, "people_est": 600},
        {"node": "CONCOURSE_N", "density": 0.50, "people_est": 750},
        {"node": "FOOD_1",      "density": 0.35, "people_est": 175},
        {"node": "TRANSIT_HUB", "density": 0.20, "people_est": 300},
    ]


@pytest.fixture
def kickoff_dt():
    """Kickoff datetime set to 45 minutes ago (mid first half)."""
    return datetime.now(timezone.utc) - timedelta(minutes=45)


@pytest.fixture
def sample_incident():
    """Sample incident dictionary for genai response tests."""
    return {
        "id": "INC-TEST-001",
        "kind": "medical",
        "node": "CONCOURSE_N",
        "severity": "high",
        "minute": 45.0,
        "reported_at": "2026-07-04T20:45:00Z",
    }
