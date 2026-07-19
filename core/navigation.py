"""Smart Navigation & Wayfinding engine.

- Dijkstra shortest-path over the venue graph.
- Accessibility-first mode: only accessible edges + accessible nodes.
- Crowd-aware mode: edge cost inflated by live density (dynamic re-routing).
- Returns step-by-step directions with distances/times and accessibility flags.
"""
import heapq
import json
from data.venue import NODES, build_graph

_graph = build_graph()


def _edge_cost(edge, density_map, crowd_aware):
    base = edge["secs"]
    if crowd_aware:
        d = density_map.get(edge["to"], 0.0)
        # up to 2.5x slowdown in dense areas -> dynamic re-routing
        base *= (1.0 + 2.0 * d)
    # accessible paths (elevator/ramp) are slower; keep as-is but penalize less
    return base


def route(start, goal, accessible_only=False, crowd_aware=False, density_map=None):
    density_map = density_map or {}
    if start not in NODES or goal not in NODES:
        return {"ok": False, "error": "Unknown node(s)"}
    if accessible_only and not (NODES[start]["accessible"] and NODES[goal]["accessible"]):
        return {"ok": False, "error": "Start or goal is not accessible"}

    dist = {n: float("inf") for n in NODES}
    prev = {n: None for n in NODES}
    dist[start] = 0
    pq = [(0, start)]
    while pq:
        d, u = heapq.heappop(pq)
        if u == goal:
            break
        if d > dist[u]:
            continue
        for edge in _graph[u]:
            if accessible_only and not NODES[edge["to"]]["accessible"]:
                continue
            cost = _edge_cost(edge, density_map, crowd_aware)
            nd = d + cost
            if nd < dist[edge["to"]]:
                dist[edge["to"]] = nd
                prev[edge["to"]] = u
                heapq.heappush(pq, (nd, edge["to"]))

    if dist[goal] == float("inf"):
        return {"ok": False, "error": "No path found"}

    # reconstruct
    path = []
    cur = goal
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()

    steps = []
    total_dist = 0
    total_secs = 0
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        # find edge
        edge = next(e for e in _graph[u] if e["to"] == v)
        total_dist += edge["dist"]
        total_secs += _edge_cost(edge, density_map, crowd_aware)
        steps.append({
            "from": u, "from_name": NODES[u]["name"],
            "to": v, "to_name": NODES[v]["name"],
            "distance_m": edge["dist"],
            "seconds": round(_edge_cost(edge, density_map, crowd_aware)),
            "accessible": NODES[v]["accessible"],
            "type": NODES[v]["type"],
        })
    return {
        "ok": True,
        "start": start, "goal": goal,
        "accessible_only": accessible_only,
        "crowd_aware": crowd_aware,
        "path": path,
        "total_distance_m": total_dist,
        "total_seconds": round(total_secs),
        "steps": steps,
        "uses_elevator": any(NODES[s["to"]]["type"] == "elevator" for s in steps),
        "uses_ramp": any(NODES[s["to"]]["type"] == "ramp" for s in steps),
    }


def nearest_of(start, types, accessible_only=False):
    """Find nearest node of given type (for 'nearest restroom' style queries)."""
    best = None
    best_cost = float("inf")
    for n, d in NODES.items():
        if d["type"] in types and (not accessible_only or d["accessible"]):
            r = route(start, n, accessible_only=accessible_only)
            if r["ok"] and r["total_seconds"] < best_cost:
                best_cost = r["total_seconds"]
                best = n
    return best


if __name__ == "__main__":
    r = route("GATE_A", "SEC_340", accessible_only=True)
    print(json.dumps(r, indent=2))
