"""FastAPI backend for StadiumGenius AI.

Endpoints:
- GET  /                       -> serves the web UI (index.html)
- GET  /api/languages          -> supported languages
- POST /api/chat               -> RAG-grounded multilingual assistant
- POST /api/translate          -> translate text to target language
- POST /api/navigate           -> accessibility-first / crowd-aware routing
- GET  /api/crowd              -> crowd analysis from latest sensor tick
- GET  /api/ops                -> operational intelligence snapshot
- WS   /ws/live                -> streaming live sensor + crowd + incident feed
"""
import asyncio
import json
import random
import time
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

import core.sustainability as sustainability_engine
import core.transport as transport_engine
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from core import chat as genai_chat, translate as genai_translate
from core import route as nav_route, nearest_of
from core import analyze as crowd_analyze, predict_trend
from core import generate_incident_response
from core.genai import recommend_fan_experience
from data.venue import NODES
from sim.simulator import generate_tick, HOTSPOTS

WEB_DIR = Path(__file__).parent.parent / "web"
ASSET_DIR = Path(__file__).parent.parent / "data"

# Configure allowed CORS origins from environment or default to localhost dev origins
_RAW_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000"
)
ALLOWED_ORIGINS: List[str] = [o.strip() for o in _RAW_ORIGINS.split(",") if o.strip()]

app = FastAPI(title="StadiumGenius AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Inject HTTP security headers into every response."""
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "connect-src 'self' ws: wss:; "
        "img-src 'self' data:;"
    )
    return response

# --- in-process live simulator state (protected by asyncio lock) ----------
_sim_lock = asyncio.Lock()

SIM_STATE = {
    "kickoff": datetime.now(timezone.utc) - timedelta(minutes=45),
    "t": 0,
    "last_tick": None,
    "history": [],
    "rng": random.Random(42),
    "incidents": []
}

# --- Crowd analysis cache: avoids re-running crowd_analyze() for same tick --
_CROWD_CACHE: dict = {"tick_t": -1, "analysis": None}


def _get_crowd_analysis(tick: dict) -> dict:
    """Return cached crowd analysis for the current tick, or compute and cache."""
    if _CROWD_CACHE["tick_t"] != tick["t"]:
        analysis = crowd_analyze(tick["sensors"], tick["phase"], tick["intensity"])
        analysis["trend"] = predict_trend(SIM_STATE["history"])
        analysis["minute"] = tick["minute"]
        _CROWD_CACHE["tick_t"] = tick["t"]
        _CROWD_CACHE["analysis"] = analysis
    return _CROWD_CACHE["analysis"]


def _tick():
    SIM_STATE["t"] += 1
    tick = generate_tick(SIM_STATE["kickoff"], SIM_STATE["rng"], SIM_STATE["t"])
    SIM_STATE["last_tick"] = tick
    SIM_STATE["history"].append(tick["intensity"])
    if len(SIM_STATE["history"]) > 20:
        SIM_STATE["history"].pop(0)

    # Check if simulator generated a random incident
    if tick.get("incident"):
        inc = tick["incident"]
        res = generate_incident_response(inc)
        inc["response_steps"] = res.get("response_steps", "")
        SIM_STATE["incidents"].append(inc)
        if len(SIM_STATE["incidents"]) > 10:
            SIM_STATE["incidents"].pop(0)

    return tick


async def _ensure_ticking():
    if SIM_STATE["last_tick"] is None:
        _tick()


# --- request models -------------------------------------------------------
class ChatReq(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    language: str = Field(default="en", max_length=10)


class TranslateReq(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    target: str = Field(..., max_length=10)
    source: str = Field(default="en", max_length=10)


class NavReq(BaseModel):
    start: str = Field(..., max_length=50)
    goal: Optional[str] = Field(default=None, max_length=50)
    goal_type: Optional[str] = Field(default=None, max_length=50)  # e.g. "restroom", "exit", "food"
    accessible_only: bool = False
    crowd_aware: bool = True


class IncidentReq(BaseModel):
    kind: str = Field(..., max_length=50)
    node: str = Field(..., max_length=50)
    severity: str = Field(..., max_length=20)

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: str) -> str:
        allowed = {"low", "medium", "high"}
        if v not in allowed:
            raise ValueError(f"severity must be one of {allowed}")
        return v


class SustainReq(BaseModel):
    item: str = Field(..., min_length=1, max_length=200)


class TransportReq(BaseModel):
    start_node: str = Field(..., max_length=50)
    destination_type: str = Field(default="transit", max_length=50)


class FanExpReq(BaseModel):
    preferences: List[str] = Field(default_factory=list)
    language: str = Field(default="en", max_length=10)


# --- REST routes ----------------------------------------------------------
@app.get("/api/languages")
def languages():
    from data.knowledge import LANGUAGES
    return {"languages": [{"code": c, "name": n} for c, n in LANGUAGES]}


@app.post("/api/chat")
def chat_endpoint(req: ChatReq):
    return genai_chat(req.message, req.language)


@app.post("/api/translate")
def translate_endpoint(req: TranslateReq):
    return genai_translate(req.text, req.target, req.source)


@app.post("/api/navigate")
def navigate(req: NavReq):
    goal = req.goal
    if not goal and req.goal_type:
        goal = nearest_of(req.start, {req.goal_type})
        if not goal:
            return JSONResponse({"ok": False, "error": f"No {req.goal_type} found"}, 404)
    density = {}
    if SIM_STATE["last_tick"]:
        density = {s["node"]: s["density"] for s in SIM_STATE["last_tick"]["sensors"]}
    result = nav_route(req.start, goal, accessible_only=req.accessible_only,
                       crowd_aware=req.crowd_aware, density_map=density)
    return result


@app.get("/api/crowd")
async def crowd():
    await _ensure_ticking()
    tick = SIM_STATE["last_tick"]
    analysis = _get_crowd_analysis(tick)  # cached — no duplicate compute
    return analysis


@app.get("/api/ops")
async def ops():
    await _ensure_ticking()
    tick = SIM_STATE["last_tick"]
    analysis = dict(_get_crowd_analysis(tick))  # shallow copy before mutating
    # staff allocation suggestions (simple heuristic)
    critical = [a for a in analysis["alerts"] if a["level"] == "critical"]
    analysis["staff_allocation"] = (
        f"Recommend {len(critical)*4 + 8} stewards active; "
        f"prioritize {', '.join(a['name'] for a in critical[:3]) or 'all concourses'}."
    )
    analysis["incidents"] = SIM_STATE["incidents"]
    return analysis


@app.get("/api/nodes")
def nodes():
    return {"nodes": NODES}


@app.post("/api/incident")
def create_incident(req: IncidentReq):
    inc = {
        "id": f"INC-{int(time.time())}-{random.randint(100, 999)}",
        "kind": req.kind,
        "node": req.node,
        "severity": req.severity,
        "minute": round(SIM_STATE["last_tick"]["minute"] if SIM_STATE["last_tick"] else 0.0, 1),
        "reported_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    res = generate_incident_response(inc)
    inc["response_steps"] = res.get("response_steps", "")
    SIM_STATE["incidents"].append(inc)
    if len(SIM_STATE["incidents"]) > 10:
        SIM_STATE["incidents"].pop(0)
    return {"ok": True, "incident": inc}


@app.get("/api/incidents")
def list_incidents():
    return {"incidents": SIM_STATE["incidents"]}


@app.get("/api/sustainability")
async def sustainability_metrics():
    await _ensure_ticking()
    tick = SIM_STATE["last_tick"]
    metrics = sustainability_engine.get_metrics(tick["minute"], tick["intensity"])
    return metrics


@app.post("/api/sustainability/recycling")
def recycling_query(req: SustainReq):
    return sustainability_engine.get_recycling_guidance(req.item)


@app.post("/api/transport")
async def transport_trip(req: TransportReq):
    await _ensure_ticking()
    tick = SIM_STATE["last_tick"]
    return transport_engine.plan_trip(req.start_node, req.destination_type, tick["phase"], tick["minute"])


@app.post("/api/fan-exp")
async def fan_experience(req: FanExpReq):
    await _ensure_ticking()
    tick = SIM_STATE["last_tick"]
    return recommend_fan_experience(tick["phase"], req.preferences, req.language)


# --- WebSocket live feed --------------------------------------------------
@app.websocket("/ws/live")
async def live(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            tick = _tick()
            analysis = crowd_analyze(tick["sensors"], tick["phase"], tick["intensity"])
            analysis["trend"] = predict_trend(SIM_STATE["history"])
            analysis["minute"] = tick["minute"]
            payload = {
                "tick": tick,
                "analysis": analysis,
                "incidents": SIM_STATE["incidents"]
            }
            await websocket.send_text(json.dumps(payload))
            await asyncio.sleep(2.0)
    except WebSocketDisconnect:
        return


# --- static UI ------------------------------------------------------------
@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")


app.mount("/assets", StaticFiles(directory=WEB_DIR / "assets"), name="assets")
