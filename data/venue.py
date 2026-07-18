"""Simulated venue map: a directed/weighted graph of a FIFA 2026 stadium + fan zone.

Nodes represent places (gates, seats, restrooms, food, exits, transit, accessible
facilities). Edges carry distance (m), base_walk_time (s), and accessibility flags.
This is the knowledge base for navigation + RAG.
"""
import json
from pathlib import Path

VENUE = {
    "name": "FIFA26 MetLife Stadium (Simulated)",
    "capacity": 82500,
    "entrances": ["GATE_A", "GATE_B", "GATE_C", "GATE_D"],
}

# node_id: {name, type, x, y, zone, accessible(bool), languages_supported}
NODES = {
    "GATE_A": {"name": "Gate A (North)", "type": "entrance", "x": 100, "y": 0, "zone": "outside", "accessible": True},
    "GATE_B": {"name": "Gate B (East)", "type": "entrance", "x": 400, "y": 50, "zone": "outside", "accessible": True},
    "GATE_C": {"name": "Gate C (South)", "type": "entrance", "x": 200, "y": 400, "zone": "outside", "accessible": True},
    "GATE_D": {"name": "Gate D (West)", "type": "entrance", "x": 0, "y": 200, "zone": "outside", "accessible": True},
    "CONCOURSE_N": {"name": "North Concourse", "type": "concourse", "x": 100, "y": 80, "zone": "concourse", "accessible": True},
    "CONCOURSE_E": {"name": "East Concourse", "type": "concourse", "x": 320, "y": 120, "zone": "concourse", "accessible": True},
    "CONCOURSE_S": {"name": "South Concourse", "type": "concourse", "x": 200, "y": 320, "zone": "concourse", "accessible": True},
    "CONCOURSE_W": {"name": "West Concourse", "type": "concourse", "x": 80, "y": 200, "zone": "concourse", "accessible": True},
    "SEC_101": {"name": "Section 101 (Lower)", "type": "seat", "x": 150, "y": 150, "zone": "lower", "accessible": True},
    "SEC_120": {"name": "Section 120 (Lower)", "type": "seat", "x": 250, "y": 160, "zone": "lower", "accessible": True},
    "SEC_305": {"name": "Section 305 (Upper)", "type": "seat", "x": 180, "y": 220, "zone": "upper", "accessible": True},
    "SEC_340": {"name": "Section 340 (Upper, wheelchair)", "type": "seat", "x": 120, "y": 240, "zone": "upper", "accessible": True},
    "REST_N": {"name": "Restroom North (accessible)", "type": "restroom", "x": 110, "y": 70, "zone": "concourse", "accessible": True},
    "REST_S": {"name": "Restroom South", "type": "restroom", "x": 210, "y": 310, "zone": "concourse", "accessible": False},
    "FOOD_1": {"name": "Food Vendor #1 (Halal/Veg)", "type": "food", "x": 130, "y": 110, "zone": "concourse", "accessible": True},
    "FOOD_2": {"name": "Food Vendor #2 (Local cuisine)", "type": "food", "x": 270, "y": 130, "zone": "concourse", "accessible": True},
    "ELEV_1": {"name": "Accessible Elevator 1", "type": "elevator", "x": 90, "y": 90, "zone": "concourse", "accessible": True},
    "RAMP_1": {"name": "Wheelchair Ramp 1", "type": "ramp", "x": 70, "y": 100, "zone": "concourse", "accessible": True},
    "EXIT_N": {"name": "Emergency Exit North", "type": "exit", "x": 100, "y": 40, "zone": "concourse", "accessible": True},
    "EXIT_S": {"name": "Emergency Exit South", "type": "exit", "x": 200, "y": 360, "zone": "concourse", "accessible": True},
    "TRANSIT_HUB": {"name": "Transit Hub (Train/Bus)", "type": "transit", "x": 0, "y": 0, "zone": "outside", "accessible": True},
    "PARKING_E": {"name": "East Parking (EV charging)", "type": "parking", "x": 500, "y": 50, "zone": "outside", "accessible": True},
    "SHUTTLE": {"name": "Shuttle Stop", "type": "transit", "x": 60, "y": -20, "zone": "outside", "accessible": True},
    "MEDICAL": {"name": "First Aid / Medical", "type": "medical", "x": 160, "y": 100, "zone": "concourse", "accessible": True},
    "INFO": {"name": "Fan Info Desk", "type": "info", "x": 140, "y": 90, "zone": "concourse", "accessible": True},
}

# edges: (from, to, distance_m, base_seconds, accessible_only(bool))
EDGES = [
    ("GATE_A", "CONCOURSE_N", 80, 60, False),
    ("GATE_B", "CONCOURSE_E", 80, 60, False),
    ("GATE_C", "CONCOURSE_S", 80, 60, False),
    ("GATE_D", "CONCOURSE_W", 80, 60, False),
    ("CONCOURSE_N", "CONCOURSE_E", 220, 165, False),
    ("CONCOURSE_E", "CONCOURSE_S", 220, 165, False),
    ("CONCOURSE_S", "CONCOURSE_W", 220, 165, False),
    ("CONCOURSE_W", "CONCOURSE_N", 220, 165, False),
    ("CONCOURSE_N", "REST_N", 40, 35, False),
    ("CONCOURSE_N", "FOOD_1", 50, 40, False),
    ("CONCOURSE_N", "ELEV_1", 30, 25, False),
    ("CONCOURSE_N", "INFO", 45, 38, False),
    ("CONCOURSE_N", "MEDICAL", 70, 55, False),
    ("CONCOURSE_N", "EXIT_N", 40, 35, False),
    ("CONCOURSE_E", "FOOD_2", 50, 40, False),
    ("CONCOURSE_E", "SEC_101", 70, 55, False),
    ("CONCOURSE_E", "SEC_120", 60, 48, False),
    ("CONCOURSE_S", "REST_S", 40, 35, False),
    ("CONCOURSE_S", "SEC_305", 70, 55, False),
    ("CONCOURSE_S", "SEC_340", 80, 62, False),
    ("CONCOURSE_S", "EXIT_S", 40, 35, False),
    ("CONCOURSE_W", "SEC_340", 60, 48, False),
    ("CONCOURSE_W", "RAMP_1", 30, 25, False),
    ("ELEV_1", "SEC_340", 90, 120, True),   # elevator is accessible-only path to upper wheelchair section
    ("RAMP_1", "CONCOURSE_N", 35, 40, True),
    ("GATE_D", "TRANSIT_HUB", 120, 90, False),
    ("GATE_A", "SHUTTLE", 100, 75, False),
    ("GATE_B", "PARKING_E", 120, 90, False),
    ("SEC_101", "SEC_120", 90, 70, False),
    ("SEC_305", "SEC_340", 60, 48, False),
]


def build_graph():
    graph = {n: [] for n in NODES}
    for f, t, d, s, acc in EDGES:
        # bidirectional
        graph[f].append({"to": t, "dist": d, "secs": s, "accessible": acc})
        graph[t].append({"to": f, "dist": d, "secs": s, "accessible": acc})
    return graph


def export_json(path=None):
    out = {
        "venue": VENUE,
        "nodes": NODES,
        "edges": [
            {"from": f, "to": t, "dist": d, "secs": s, "accessible": acc}
            for f, t, d, s, acc in EDGES
        ],
    }
    if path:
        Path(path).write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


if __name__ == "__main__":
    export_json(Path(__file__).parent / "venue_graph.json")
    print("venue_graph.json written")
