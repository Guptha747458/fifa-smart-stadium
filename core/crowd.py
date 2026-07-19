"""Intelligent Crowd Management engine.

- Consumes live sensor density.
- Flags bottlenecks (density > threshold) and predicts trend (rising/stable/falling).
- Generates automated alerts + dynamic re-routing suggestions + staff guidance.
- Safety recommendations for high-risk phases (halftime, end-of-match).
"""
import json
from data.venue import NODES

DENSITY_WARN = 0.75
DENSITY_CRIT = 0.90


def analyze(sensors, phase="", intensity=0.0):
    """sensors: list of {node, density, people_est, ...}"""
    alerts = []
    hotspots = []
    for s in sensors:
        d = s["density"]
        node = s["node"]
        name = NODES.get(node, {}).get("name", node)
        typ = NODES.get(node, {}).get("type", "")
        if d >= DENSITY_CRIT:
            level = "critical"
        elif d >= DENSITY_WARN:
            level = "warning"
        else:
            level = "ok"
        hotspots.append({"node": node, "name": name, "type": typ,
                         "density": d, "level": level,
                         "people_est": s.get("people_est", 0)})
        if level in ("warning", "critical"):
            alerts.append(_make_alert(node, name, level, d, typ))
    return {
        "phase": phase,
        "intensity": intensity,
        "hotspots": sorted(hotspots, key=lambda h: -h["density"]),
        "alerts": alerts,
        "summary": _summary(alerts, intensity, phase),
    }


def _make_alert(node, name, level, density, typ):
    reroute = _reroute_for(node)
    staff = _staff_guidance(node, level, typ)
    safety = _safety_rec(level, typ)
    return {
        "node": node, "name": name, "level": level,
        "density": round(density, 3),
        "reroute": reroute,
        "staff_guidance": staff,
        "safety": safety,
    }


def _reroute_for(node):
    # Pick an alternative concourse/entrance to divert flow.
    if NODES.get(node, {}).get("type") == "entrance":
        return "Divert incoming fans to adjacent gates; open overflow lanes."
    if NODES.get(node, {}).get("type") == "concourse":
        return "Open secondary corridors; reroute through opposite concourse."
    if NODES.get(node, {}).get("type") == "transit":
        return "Stagger shuttle departures; promote walking routes to alternate hubs."
    return "Open adjacent gates / expand queue lanes."


def _staff_guidance(node, level, typ):
    if level == "critical":
        return (f"Deploy 4+ stewards to {NODES.get(node,{}).get('name',node)}. "
                f"Initiate flow control and halt new entries until density < 0.8.")
    return (f"Position 2 stewards at {NODES.get(node,{}).get('name',node)}; "
            f"monitor and prepare to throttle entry.")


def _safety_rec(level, typ):
    if level == "critical" and typ in ("concourse", "entrance"):
        return ("High crush risk. Activate one-way flow, disable opposing movement, "
                "and broadcast calm audio guidance.")
    return "Maintain visible steward presence and clear signage."


def _summary(alerts, intensity, phase):
    crit = sum(1 for a in alerts if a["level"] == "critical")
    warn = sum(1 for a in alerts if a["level"] == "warning")
    if crit:
        head = f"CRITICAL: {crit} bottleneck(s) detected during {phase}."
    elif warn:
        head = f"Caution: {warn} congestion zone(s) forming during {phase}."
    else:
        head = f"Flow nominal during {phase}."
    if intensity >= 0.9:
        head += " High-traffic phase — keep reactive teams on standby."
    return head


def predict_trend(history):
    """history: list of recent overall intensity values (oldest..newest)."""
    if len(history) < 3:
        return "insufficient_data"
    recent = history[-3:]
    if recent[-1] - recent[0] > 0.05:
        return "rising"
    if recent[0] - recent[-1] > 0.05:
        return "falling"
    return "stable"


if __name__ == "__main__":
    sample = [{"node": "GATE_A", "density": 0.95, "people_est": 1400},
              {"node": "CONCOURSE_N", "density": 0.8, "people_est": 1200}]
    print(json.dumps(analyze(sample, "end_peak", 0.98), indent=2))
