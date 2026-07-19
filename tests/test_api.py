"""Integration tests for StadiumGenius AI FastAPI endpoints.

Uses FastAPI's TestClient (synchronous HTTPX) to exercise all REST routes
without starting a real server. WebSocket live feed is tested separately.
"""
import pytest
from fastapi.testclient import TestClient
from api.server import app

client = TestClient(app)


class TestHealthAndStaticRoutes:
    """Tests for static content serving."""

    def test_root_serves_html(self):
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")

    def test_nodes_endpoint(self):
        r = client.get("/api/nodes")
        assert r.status_code == 200
        data = r.json()
        assert "nodes" in data
        assert len(data["nodes"]) > 0


class TestLanguagesEndpoint:
    """Tests for GET /api/languages."""

    def test_returns_200(self):
        r = client.get("/api/languages")
        assert r.status_code == 200

    def test_returns_languages_list(self):
        r = client.get("/api/languages")
        data = r.json()
        assert "languages" in data
        assert len(data["languages"]) >= 50

    def test_each_language_has_code_and_name(self):
        r = client.get("/api/languages")
        for lang in r.json()["languages"]:
            assert "code" in lang
            assert "name" in lang

    def test_english_is_in_list(self):
        r = client.get("/api/languages")
        codes = [l["code"] for l in r.json()["languages"]]
        assert "en" in codes


class TestChatEndpoint:
    """Tests for POST /api/chat."""

    def test_chat_returns_200(self):
        r = client.post("/api/chat", json={"message": "Where is the exit?", "language": "en"})
        assert r.status_code == 200

    def test_chat_response_has_required_fields(self):
        r = client.post("/api/chat", json={"message": "Tell me about accessibility"})
        data = r.json()
        assert "answer" in data
        assert "language" in data
        assert "sources" in data
        assert "mode" in data

    def test_chat_defaults_to_english(self):
        r = client.post("/api/chat", json={"message": "What food is available?"})
        assert r.json()["language"] == "en"

    def test_chat_with_language_param(self):
        r = client.post("/api/chat", json={"message": "Where is the exit?", "language": "es"})
        assert r.status_code == 200
        assert r.json()["language"] == "es"

    def test_chat_empty_message_returns_400_or_answer(self):
        r = client.post("/api/chat", json={"message": ""})
        # Either validation error or graceful empty answer
        assert r.status_code in (200, 422)

    def test_chat_oversized_message_returns_422(self):
        r = client.post("/api/chat", json={"message": "x" * 5001, "language": "en"})
        assert r.status_code == 422


class TestTranslateEndpoint:
    """Tests for POST /api/translate."""

    def test_translate_returns_200(self):
        r = client.post("/api/translate", json={"text": "Hello", "target": "es", "source": "en"})
        assert r.status_code == 200

    def test_translate_response_has_ok_field(self):
        r = client.post("/api/translate", json={"text": "Hello", "target": "fr"})
        data = r.json()
        assert "ok" in data

    def test_translate_invalid_target_returns_error(self):
        r = client.post("/api/translate", json={"text": "Hello", "target": "xx_invalid"})
        assert r.status_code == 200
        assert r.json()["ok"] is False

    def test_translate_oversized_text_returns_422(self):
        r = client.post("/api/translate", json={"text": "y" * 5001, "target": "fr"})
        assert r.status_code == 422


class TestNavigationEndpoint:
    """Tests for POST /api/navigate."""

    def test_basic_route_ok(self):
        r = client.post("/api/navigate", json={"start": "GATE_A", "goal": "FOOD_1"})
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True

    def test_route_by_goal_type(self):
        r = client.post("/api/navigate", json={"start": "GATE_A", "goal_type": "restroom"})
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True

    def test_invalid_nodes_return_error(self):
        r = client.post("/api/navigate", json={"start": "FAKE_NODE", "goal": "ALSO_FAKE"})
        data = r.json()
        assert data["ok"] is False


class TestCrowdEndpoint:
    """Tests for GET /api/crowd."""

    def test_crowd_returns_200(self):
        r = client.get("/api/crowd")
        assert r.status_code == 200

    def test_crowd_has_required_fields(self):
        r = client.get("/api/crowd")
        data = r.json()
        assert "phase" in data
        assert "hotspots" in data
        assert "alerts" in data
        assert "trend" in data


class TestOpsEndpoint:
    """Tests for GET /api/ops."""

    def test_ops_returns_200(self):
        r = client.get("/api/ops")
        assert r.status_code == 200

    def test_ops_includes_incidents(self):
        r = client.get("/api/ops")
        data = r.json()
        assert "incidents" in data
        assert isinstance(data["incidents"], list)

    def test_ops_includes_staff_allocation(self):
        r = client.get("/api/ops")
        data = r.json()
        assert "staff_allocation" in data


class TestIncidentEndpoints:
    """Tests for incident creation and listing."""

    def test_create_incident_returns_ok(self):
        r = client.post("/api/incident", json={
            "kind": "medical",
            "node": "CONCOURSE_N",
            "severity": "high"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert "incident" in data

    def test_created_incident_has_id(self):
        r = client.post("/api/incident", json={
            "kind": "security",
            "node": "GATE_A",
            "severity": "medium"
        })
        inc = r.json()["incident"]
        assert "id" in inc
        assert inc["id"].startswith("INC-")

    def test_list_incidents_returns_list(self):
        r = client.get("/api/incidents")
        assert r.status_code == 200
        data = r.json()
        assert "incidents" in data
        assert isinstance(data["incidents"], list)


class TestSustainabilityEndpoints:
    """Tests for sustainability metrics and recycling guidance."""

    def test_sustainability_metrics_returns_200(self):
        r = client.get("/api/sustainability")
        assert r.status_code == 200

    def test_sustainability_metrics_has_energy(self):
        r = client.get("/api/sustainability")
        data = r.json()
        assert "energy_kw" in data

    def test_recycling_guidance_for_bottle(self):
        r = client.post("/api/sustainability/recycling", json={"item": "plastic bottle"})
        assert r.status_code == 200
        data = r.json()
        assert "bin" in data
        assert "points" in data

    def test_recycling_guidance_returns_tip(self):
        r = client.post("/api/sustainability/recycling", json={"item": "aluminum can"})
        data = r.json()
        assert "tip" in data
        assert len(data["tip"]) > 0


class TestTransportEndpoint:
    """Tests for POST /api/transport."""

    def test_transport_plan_returns_ok(self):
        r = client.post("/api/transport", json={"start_node": "SEC_101", "destination_type": "transit"})
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True

    def test_transport_returns_options_list(self):
        r = client.post("/api/transport", json={"start_node": "GATE_A"})
        data = r.json()
        assert "options" in data
        assert isinstance(data["options"], list)
