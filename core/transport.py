"""Transportation & Logistics engine.

- Integrated trip planner: stadium -> public transit / parking / last-mile.
- Predictive traffic/congestion alerts and departure time recommendations.
- Dynamic EV charging locator and parking spot assignment.
"""
from data.venue import NODES

def plan_trip(start_node: str, destination_type: str, match_phase: str, minute: float) -> dict:
    """Plans a trip from the stadium node to a target transportation point.
    Returns details on best departure times, routing options, and EV chargers if applicable.
    """
    # Find matching transport nodes in venue
    transports = []
    for n, d in NODES.items():
        if d["type"] in ("transit", "parking"):
            transports.append({"node": n, "name": d["name"], "type": d["type"], "accessible": d["accessible"]})
            
    # Heuristics based on match phase
    # Pre-peak/kickoff -> arrival traffic. Halftime/end_peak/egress -> departure traffic.
    is_egress = match_phase in ("halftime", "end_peak", "egress")
    
    # Base recommendation
    delay_recommendation = "Depart immediately"
    crowd_delay_sec = 0
    
    if is_egress:
        if match_phase == "end_peak":
            delay_recommendation = "Delay departure by 30-45 minutes. Enjoy post-match interviews on the big screen to avoid the main egress bottleneck at gates."
            crowd_delay_sec = 1800
        elif match_phase == "egress":
            delay_recommendation = "Delay departure by 15-20 minutes. Concourse traffic is heavy, transit lines are at peak."
            crowd_delay_sec = 900
        elif match_phase == "halftime":
            delay_recommendation = "Make it quick: 15-minute rush underway. Return to seats shortly."
            crowd_delay_sec = 300

    # Let's formulate options
    options = []
    for t in transports:
        mode = "Transit (Train/Bus)" if t["type"] == "transit" else "Private Vehicle"
        if "Shuttle" in t["name"]:
            mode = "Shuttle Service"
            
        base_time_min = 15 if t["type"] == "transit" else 25
        est_travel_min = base_time_min + int(crowd_delay_sec / 60)
        
        opt = {
            "node": t["node"],
            "name": t["name"],
            "mode": mode,
            "est_travel_time_min": est_travel_min,
            "accessible": t["accessible"],
            "status": "Heavy Congestion" if is_egress else "Clear Flow",
        }
        
        # EV charging details for East Parking
        if t["node"] == "PARKING_E":
            opt["ev_charging"] = {
                "available_chargers": max(0, 40 - int(abs(minute) % 38)),
                "type": "Level 2 (J1772)",
                "location": "Row C, Slots 1-40",
                "reserve_url": "/api/transport/reserve-ev"
            }
            
        options.append(opt)
        
    return {
        "ok": True,
        "start": start_node,
        "destination_type": destination_type,
        "match_phase": match_phase,
        "minute": minute,
        "departure_recommendation": delay_recommendation,
        "crowd_delay_seconds": crowd_delay_sec,
        "options": options
    }
