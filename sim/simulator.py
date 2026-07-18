"""Real-time data simulator for StadiumGenius AI.

Generates streaming crowd-density, sensor, transit, and incident events that feed
the operational dashboard and crowd-management engine. Designed to be deterministic
with a seed so demos are reproducible.
"""
import json
import math
import random
import time
from datetime import datetime, timedelta
from pathlib import Path

from data.venue import NODES, VENUE

# logical "hotspots" we track density for (concourses + gates + key nodes)
HOTSPOTS = [n for n, d in NODES.items() if d["type"] in
            ("entrance", "concourse", "seat", "food", "restroom", "transit")]

# match timeline phases (relative minutes from kickoff=0)
PHASES = [
    ("pre_gates", -180, -30, 0.55),   # fans arriving
    ("pre_peak", -30, 0, 0.85),       # bottleneck risk
    ("kickoff", 0, 15, 0.95),         # full
    ("first_half", 15, 45, 0.70),
    ("halftime", 45, 60, 0.90),       # movement spike
    ("second_half", 60, 90, 0.70),
    ("end_peak", 90, 100, 0.98),      # egress bottleneck risk
    ("egress", 100, 160, 0.60),
]


def phase_for(minute):
    for name, a, b, intensity in PHASES:
        if a <= minute < b:
            return name, intensity
    return "idle", 0.2


def minute_now(kickoff_dt):
    delta = (datetime.utcnow() - kickoff_dt).total_seconds() / 60.0
    return delta


def density_at(node, phase_intensity, t, rng):
    """Return 0..1 crowd density for a node given phase + noise."""
    base = NODES[node]
    typ = base["type"]
    # entrances/concourses spike during arrival & egress
    if typ == "entrance":
        factor = 1.2 if phase_intensity > 0.8 else 0.7
    elif typ == "concourse":
        factor = 1.1 if phase_intensity > 0.7 else 0.8
    elif typ == "food":
        factor = 1.0 if phase_intensity > 0.85 else 0.5
    elif typ == "seat":
        factor = 0.4 if phase_intensity < 0.95 else 0.2  # seats fill, then empty at egress
    elif typ == "transit":
        factor = 1.3 if phase_intensity > 0.9 else 0.6
    else:
        factor = 0.7
    noise = 0.15 * math.sin(t / 7.0 + hash(node) % 10) + rng.uniform(-0.08, 0.08)
    val = phase_intensity * factor + noise
    return max(0.0, min(1.0, val))


def sensor_reading(node, density, rng):
    """Translate density into physical-ish sensor readings."""
    people = int(density * (NODES[node].get("capacity", 4000) if NODES[node]["type"] == "seat" else 1500))
    return {
        "node": node,
        "density": round(density, 3),
        "people_est": people,
        "co2_ppm": int(420 + density * 600 + rng.uniform(-20, 20)),
        "noise_db": int(60 + density * 35 + rng.uniform(-3, 3)),
        "throughput_per_min": int(density * 220),
    }


def maybe_incident(rng, minute):
    """Sporadically emit incidents for the ops dashboard."""
    if rng.random() < 0.02:
        kinds = ["medical", "security", "weather", "crowd_surge", "lost_child"]
        kind = rng.choice(kinds)
        node = rng.choice(HOTSPOTS)
        sev = rng.choice(["low", "medium", "high"])
        return {
            "id": f"INC-{int(time.time())}-{rng.randint(100,999)}",
            "kind": kind,
            "node": node,
            "severity": sev,
            "minute": round(minute, 1),
            "reported_at": datetime.utcnow().isoformat() + "Z",
        }
    return None


def generate_tick(kickoff_dt, rng, t):
    minute = minute_now(kickoff_dt)
    phase, intensity = phase_for(minute)
    sensors = []
    for node in HOTSPOTS:
        d = density_at(node, intensity, t, rng)
        sensors.append(sensor_reading(node, d, rng))
    inc = maybe_incident(rng, minute)
    return {
        "t": t,
        "minute": round(minute, 1),
        "phase": phase,
        "intensity": round(intensity, 2),
        "sensors": sensors,
        "incident": inc,
    }


def run_forever(seed=42, interval=2.0):
    """Run a live tick loop; print JSON each interval (used by sim.run)."""
    rng = random.Random(seed)
    kickoff = datetime.utcnow() - timedelta(minutes=45)  # start mid pre-match
    t = 0
    print(json.dumps({"status": "simulator_started", "kickoff": kickoff.isoformat() + "Z"}))
    try:
        while True:
            tick = generate_tick(kickoff, rng, t)
            print(json.dumps(tick))
            t += 1
            time.sleep(interval)
    except KeyboardInterrupt:
        print(json.dumps({"status": "stopped"}))


if __name__ == "__main__":
    import sys
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 42
    run_forever(seed=seed)
