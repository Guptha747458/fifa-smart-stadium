/* StadiumGenius AI — front-end logic.
   Vanilla JS, no build step. Talks to FastAPI REST + WebSocket.
   Accessibility: ARIA live regions, keyboard nav, high-contrast toggle. */
"use strict";

const API = "";
let LANG = "en";
let LANGS = [];
let ACTIVE_PATH = [];
let LATEST_DENSITY = {};
let SHOWN_TOASTS = new Set();
let USER_GREEN_POINTS = 0;

const NODES_COORDS = {
  "GATE_A": { name: "Gate A (North)", type: "entrance", x: 100, y: 30, accessible: true },
  "GATE_B": { name: "Gate B (East)", type: "entrance", x: 400, y: 60, accessible: true },
  "GATE_C": { name: "Gate C (South)", type: "entrance", x: 200, y: 380, accessible: true },
  "GATE_D": { name: "Gate D (West)", type: "entrance", x: 20, y: 200, accessible: true },
  "CONCOURSE_N": { name: "North Concourse", type: "concourse", x: 100, y: 120, accessible: true },
  "CONCOURSE_E": { name: "East Concourse", type: "concourse", x: 300, y: 140, accessible: true },
  "CONCOURSE_S": { name: "South Concourse", type: "concourse", x: 200, y: 300, accessible: true },
  "CONCOURSE_W": { name: "West Concourse", type: "concourse", x: 100, y: 200, accessible: true },
  "SEC_101": { name: "Section 101 (Lower)", type: "seat", x: 180, y: 170, accessible: true },
  "SEC_120": { name: "Section 120 (Lower)", type: "seat", x: 250, y: 180, accessible: true },
  "SEC_305": { name: "Section 305 (Upper)", type: "seat", x: 190, y: 240, accessible: true },
  "SEC_340": { name: "Section 340 (Upper, wheelchair)", type: "seat", x: 140, y: 220, accessible: true },
  "REST_N": { name: "Restroom North (accessible)", type: "restroom", x: 130, y: 100, accessible: true },
  "REST_S": { name: "Restroom South", type: "restroom", x: 230, y: 320, accessible: false },
  "FOOD_1": { name: "Food Vendor #1 (Halal/Veg)", type: "food", x: 150, y: 130, accessible: true },
  "FOOD_2": { name: "Food Vendor #2 (Local cuisine)", type: "food", x: 270, y: 150, accessible: true },
  "ELEV_1": { name: "Accessible Elevator 1", type: "elevator", x: 110, y: 140, accessible: true },
  "RAMP_1": { name: "Wheelchair Ramp 1", type: "ramp", x: 80, y: 170, accessible: true },
  "EXIT_N": { name: "Emergency Exit North", type: "exit", x: 100, y: 70, accessible: true },
  "EXIT_S": { name: "Emergency Exit South", type: "exit", x: 200, y: 340, accessible: true },
  "TRANSIT_HUB": { name: "Transit Hub", type: "transit", x: 10, y: 30, accessible: true },
  "PARKING_E": { name: "East Parking (EV charging)", type: "parking", x: 440, y: 60, accessible: true },
  "SHUTTLE": { name: "Shuttle Stop", type: "transit", x: 70, y: 20, accessible: true },
  "MEDICAL": { name: "First Aid / Medical", type: "medical", x: 180, y: 110, accessible: true },
  "INFO": { name: "Fan Info Desk", type: "info", x: 160, y: 90, accessible: true }
};

const EDGES_LIST = [
  { from: "GATE_A", to: "CONCOURSE_N" },
  { from: "GATE_B", to: "CONCOURSE_E" },
  { from: "GATE_C", to: "CONCOURSE_S" },
  { from: "GATE_D", to: "CONCOURSE_W" },
  { from: "CONCOURSE_N", to: "CONCOURSE_E" },
  { from: "CONCOURSE_E", to: "CONCOURSE_S" },
  { from: "CONCOURSE_S", to: "CONCOURSE_W" },
  { from: "CONCOURSE_W", to: "CONCOURSE_N" },
  { from: "CONCOURSE_N", to: "REST_N" },
  { from: "CONCOURSE_N", to: "FOOD_1" },
  { from: "CONCOURSE_N", to: "ELEV_1" },
  { from: "CONCOURSE_N", to: "INFO" },
  { from: "CONCOURSE_N", to: "MEDICAL" },
  { from: "CONCOURSE_N", to: "EXIT_N" },
  { from: "CONCOURSE_E", to: "FOOD_2" },
  { from: "CONCOURSE_E", to: "SEC_101" },
  { from: "CONCOURSE_E", to: "SEC_120" },
  { from: "CONCOURSE_S", to: "REST_S" },
  { from: "CONCOURSE_S", to: "SEC_305" },
  { from: "CONCOURSE_S", to: "SEC_340" },
  { from: "CONCOURSE_S", to: "EXIT_S" },
  { from: "CONCOURSE_W", to: "SEC_340" },
  { from: "CONCOURSE_W", to: "RAMP_1" },
  { from: "ELEV_1", to: "SEC_340" },
  { from: "RAMP_1", to: "CONCOURSE_N" },
  { from: "GATE_D", to: "TRANSIT_HUB" },
  { from: "GATE_A", to: "SHUTTLE" },
  { from: "GATE_B", to: "PARKING_E" },
  { from: "SEC_101", to: "SEC_120" },
  { from: "SEC_305", to: "SEC_340" }
];

function el(id) { return document.getElementById(id); }

// Toast alert notification generator
function showToast(message, type = "info") {
  const container = el("toast-container");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<strong>Status Notification</strong><br>${message}`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(20px)";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// Draw venue SVG map dynamically
function drawVenueMap(containerId, activePath = [], densityMap = {}) {
  const container = el(containerId);
  if (!container) return;

  let svg = `<svg class="venue-map-svg" viewBox="0 -10 460 410" xmlns="http://www.w3.org/2000/svg">`;

  // 1. Draw connections (edges)
  EDGES_LIST.forEach(edge => {
    const fromNode = NODES_COORDS[edge.from];
    const toNode = NODES_COORDS[edge.to];
    if (!fromNode || !toNode) return;

    let isActive = false;
    if (activePath.length > 0) {
      for (let i = 0; i < activePath.length - 1; i++) {
        if ((activePath[i] === edge.from && activePath[i + 1] === edge.to) ||
          (activePath[i] === edge.to && activePath[i + 1] === edge.from)) {
          isActive = true;
          break;
        }
      }
    }

    const edgeClass = isActive ? "map-edge route-active" : "map-edge";
    svg += `<line x1="${fromNode.x}" y1="${fromNode.y}" x2="${toNode.x}" y2="${toNode.y}" class="${edgeClass}" />`;
  });

  // 2. Draw stations (nodes)
  Object.entries(NODES_COORDS).forEach(([id, node]) => {
    const d = densityMap[id] || 0.0;
    let nodeColor = "#10b981"; // ok
    if (d >= 0.9) nodeColor = "#ef4444"; // crit
    else if (d >= 0.75) nodeColor = "#f59e0b"; // warn
    else if (d >= 0.5) nodeColor = "#fbbf24"; // medium

    let isStart = false;
    let isGoal = false;
    if (activePath.length > 0) {
      isStart = (id === activePath[0]);
      isGoal = (id === activePath[activePath.length - 1]);
    }

    let nodeClass = "map-node";
    if (isStart) nodeClass += " map-node-start";
    if (isGoal) nodeClass += " map-node-goal";

    svg += `
      <g class="${nodeClass}" onclick="handleNodeClick('${id}')" id="${containerId}-node-${id}">
        <circle cx="${node.x}" cy="${node.y}" r="7" fill="${nodeColor}" stroke="rgba(255,255,255,0.25)" stroke-width="2" />
        <text x="${node.x + 10}" y="${node.y + 4}" font-size="9" fill="${isStart || isGoal ? '#fff' : '#a0aec0'}">${node.name.split(" ")[0]}</text>
      </g>
    `;
  });

  svg += `</svg>`;
  container.innerHTML = svg;
}

// Click nodes context helper
let clickToggle = true; // true = start location selection, false = goal
window.handleNodeClick = function (id) {
  const activeTab = document.querySelector(".tab.active").dataset.tab;

  if (activeTab === "nav") {
    if (clickToggle) {
      el("nav-start").value = id;
      showToast("Starting point set to: " + NODES_COORDS[id].name);
      clickToggle = false;
    } else {
      el("nav-goal").value = id;
      showToast("Destination point set to: " + NODES_COORDS[id].name);
      clickToggle = true;
      el("nav-form").dispatchEvent(new Event("submit"));
    }
  } else if (activeTab === "transit") {
    el("transit-start").value = id;
    showToast("Route origin set to: " + NODES_COORDS[id].name);
    el("transit-form").dispatchEvent(new Event("submit"));
  } else if (activeTab === "crowd") {
    el("inc-node").value = id;
    showToast("Selected incident zone: " + NODES_COORDS[id].name);
  }
};

async function loadLanguages() {
  const r = await fetch(API + "/api/languages");
  const data = await r.json();
  LANGS = data.languages;
  const opts = LANGS.map(l => `<option value="${l.code}">${l.name}</option>`).join("");
  el("lang-select").innerHTML = opts;
  el("tr-source").innerHTML = `<option value="en">English (detect)</option>` + opts;
  el("tr-target").innerHTML = opts;
  el("tr-source").value = "en";
  el("tr-target").value = "es";
}

async function loadNodes() {
  const r = await fetch(API + "/api/nodes");
  const data = await r.json();
  const nodes = data.nodes;

  const startSel = el("nav-start");
  const goalSel = el("nav-goal");
  const incSel = el("inc-node");
  const transitSel = el("transit-start");

  const entries = Object.entries(nodes);
  const optionsHtml = entries.map(([k, v]) => `<option value="${k}">${v.name}</option>`).join("");

  startSel.innerHTML = optionsHtml;
  goalSel.innerHTML = `<option value="">— none (use type selector below) —</option>` + optionsHtml;
  incSel.innerHTML = optionsHtml;
  transitSel.innerHTML = optionsHtml;

  startSel.value = "GATE_A";
  transitSel.value = "SEC_101";
}

/* ---------- Tabs System ---------- */
document.querySelectorAll(".tab").forEach(tab => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(t => { t.classList.remove("active"); t.setAttribute("aria-selected", "false"); });
    document.querySelectorAll(".panel").forEach(p => { p.classList.remove("active"); p.hidden = true; });

    tab.classList.add("active"); tab.setAttribute("aria-selected", "true");
    const panel = el("panel-" + tab.dataset.tab);
    panel.classList.add("active"); panel.hidden = false;

    // Auto redraw maps on navigation/crowd changes
    if (tab.dataset.tab === "nav") {
      drawVenueMap("nav-map-wrapper", ACTIVE_PATH, LATEST_DENSITY);
    } else if (tab.dataset.tab === "crowd") {
      drawVenueMap("crowd-map-wrapper", [], LATEST_DENSITY);
    }
  });
});

/* ---------- Contrast ---------- */
el("contrast-btn").addEventListener("click", () => {
  const on = document.body.classList.toggle("hc");
  el("contrast-btn").setAttribute("aria-pressed", on ? "true" : "false");
});

/* ---------- Language Selection Event ---------- */
el("lang-select").addEventListener("change", e => {
  LANG = e.target.value;
  showToast("Language changed to " + e.target.options[e.target.selectedIndex].text);
});

/* ---------- Navigation Routing ---------- */
el("nav-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const goalType = el("nav-goaltype").value;
  const body = {
    start: el("nav-start").value,
    goal: el("nav-goal").value || null,
    goal_type: goalType || null,
    accessible_only: el("nav-acc").checked,
    crowd_aware: el("nav-crowd").checked,
  };

  const r = await fetch(API + "/api/navigate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  const data = await r.json();
  renderNav(data);
});

function renderNav(data) {
  const out = el("nav-result");
  if (!data.ok) {
    out.innerHTML = `<div class="alert warning">${data.error}</div>`;
    ACTIVE_PATH = [];
    drawVenueMap("nav-map-wrapper", [], LATEST_DENSITY);
    return;
  }

  ACTIVE_PATH = data.path;
  drawVenueMap("nav-map-wrapper", ACTIVE_PATH, LATEST_DENSITY);

  let html = `<div class="status-bar">
    <span>🧭 Route distance: <strong>${data.total_distance_m} m</strong> · Egress: <strong>~${data.total_seconds}s</strong></span>` +
    (data.accessible_only ? " <span class='badge ok'>♿ Accessible Routing</span>" : "") +
    (data.crowd_aware ? " <span class='badge warning'>👥 Live Crowd Avoidance</span>" : "") +
    `</div>`;

  if (data.uses_elevator) html += `<div class="step"><div>🛗 <strong>Accessible Elevator Path</strong></div><span class="badge ok">Activated</span></div>`;
  if (data.uses_ramp) html += `<div class="step"><div>♿ <strong>Wheelchair Ramp Connection</strong></div><span class="badge ok">Activated</span></div>`;

  data.steps.forEach((s, i) => {
    html += `<div class="step">
      <div><strong>${i + 1}.</strong> ${s.from_name} → ${s.to_name}</div>
      <span class="badge ok" style="background:rgba(255,255,255,0.06); color:var(--text); border:none;">${s.distance_m} m · ${s.seconds}s</span>
    </div>`;
  });
  out.innerHTML = html;
}

/* ---------- Incident Manual Simulator ---------- */
el("incident-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = {
    kind: el("inc-kind").value,
    node: el("inc-node").value,
    severity: el("inc-severity").value
  };

  const r = await fetch(API + "/api/incident", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  const data = await r.json();
  if (data.ok) {
    showToast(`Logged manually: ${body.kind} incident at ${NODES_COORDS[body.node].name}!`, "critical");
    // Trigger updates immediately
    const opsRes = await fetch(API + "/api/ops");
    const opsData = await opsRes.json();
    renderOps(opsData);
  }
});

/* ---------- Translate Phrases ---------- */
el("tr-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = {
    text: el("tr-text").value,
    target: el("tr-target").value,
    source: el("tr-source").value
  };
  const r = await fetch(API + "/api/translate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  const data = await r.json();
  el("tr-result").innerHTML = data.ok
    ? `<div class="alert"><span class="badge ok" style="margin-bottom:6px;">${data.method}</span><br><strong>${data.text}</strong></div>`
    : `<div class="alert warning">${data.error}</div>`;
});

/* ---------- LLM chat ---------- */
el("chat-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const msgInput = el("chat-msg");
  const msg = msgInput.value;
  if (!msg.trim()) return;

  // Append User message
  const log = el("chat-log");
  log.innerHTML += `<div class="chat-bubble user">${msg}</div>`;
  msgInput.value = "";
  log.scrollTop = log.scrollHeight;

  // Append temporary typing indicator
  const typId = "typing-" + Date.now();
  log.innerHTML += `<div class="chat-bubble bot" id="${typId}">StadiumGenius AI typing...</div>`;
  log.scrollTop = log.scrollHeight;

  const r = await fetch(API + "/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: msg, language: LANG })
  });
  const data = await r.json();

  // Replace indicator
  const indicator = el(typId);
  if (indicator) {
    indicator.innerHTML = `<div><span class="badge ok" style="margin-bottom:6px; font-size:0.7rem;">Grounded with ${data.mode}</span><br>${data.answer}</div>` +
      (data.sources.length ? `<div style="color:var(--muted);font-size:.75rem;margin-top:8px;">sources: ${data.sources.join(", ")}</div>` : "");
  }
  log.scrollTop = log.scrollHeight;
});

/* ---------- Smart Connection Trip Planner ---------- */
el("transit-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const body = {
    start_node: el("transit-start").value,
    destination_type: el("transit-mode").value
  };

  const r = await fetch(API + "/api/transport", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  const data = await r.json();
  if (data.ok) {
    el("transit-advisor-box").style.display = "block";
    el("transit-advisor-rec").innerHTML = `📢 <strong>Egress Advisor Rec:</strong> ${data.departure_recommendation}`;

    // Render list of trip connection modes
    let html = "";
    data.options.forEach(opt => {
      let evBadge = "";
      if (opt.ev_charging) {
        evBadge = `
          <div class="ai-recommendation-box" style="margin-top:8px; border-color:var(--success);">
            <strong>⚡ EV Spot Assigned:</strong> Row C Slots 1-40 (${opt.ev_charging.available_chargers} chargers open)
          </div>
        `;
      }

      html += `
        <div class="card" style="margin-bottom:12px;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <h3>${opt.name}</h3>
            <span class="badge ${opt.status === 'Clear Flow' ? 'ok' : 'warning'}">${opt.status}</span>
          </div>
          <div style="margin-top:6px; font-size:0.95rem; color:var(--muted);">
            Mode: <strong>${opt.mode}</strong> | Travel duration: <strong>${opt.est_travel_time_min} mins</strong>
          </div>
          ${evBadge}
        </div>
      `;
    });
    el("transit-options-log").innerHTML = html;
  }
});

/* ---------- Smart Waste gamification tracker ---------- */
el("sustain-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const item = el("sustain-item-input").value;

  const r = await fetch(API + "/api/sustainability/recycling", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ item: item })
  });
  const data = await r.json();

  // Add points
  USER_GREEN_POINTS += data.points;
  el("user-green-points").innerText = USER_GREEN_POINTS;

  // Render search results
  el("sustain-guide-result").innerHTML = `
    <div class="card" style="border-left: 5px solid var(--success);">
      <h3>Disposal Solution: <strong>${data.bin}</strong></h3>
      <p style="margin-top:6px; font-size:0.95rem;">${data.tip}</p>
      <div style="margin-top:10px; display:flex; gap:10px;">
        <span class="badge ok">+${data.points} FIFA Green Points</span>
        <span class="badge ok" style="background:rgba(16,185,129,0.15)">saves ${data.co2_saved_g}g CO₂ equivalents</span>
      </div>
    </div>
  `;
  showToast(`Earned +${data.points} FIFA Green Points! Wallet updated.`, "success");
  el("sustain-item-input").value = "";
});

async function updateSustainabilityStats() {
  const r = await fetch(API + "/api/sustainability");
  const metrics = await r.json();

  el("sustain-energy-val").innerText = `${metrics.energy_kw} kW`;
  el("sustain-water-val").innerText = `${metrics.water_l_min} L/min`;

  el("sustain-diversion-pct").innerText = `${metrics.diversion_rate_pct}%`;
  el("sustain-progress-bar").style.width = `${metrics.diversion_rate_pct}%`;

  el("sustain-waste-total").innerText = `${metrics.cumulative.waste_kg.toLocaleString()} kg`;
  el("sustain-co2-total").innerText = `${metrics.cumulative.co2_saved_kg.toLocaleString()} kg`;
}

/* ---------- Live WebSocket Streaming Feed ---------- */
function startLive() {
  let ws;
  const protocol = location.protocol === "https:" ? "wss://" : "ws://";
  const address = protocol + location.host + "/ws/live";

  try {
    ws = new WebSocket(address);
  } catch (e) {
    showToast("WebSocket start failure, retrying...", "warning");
    return;
  }

  ws.onmessage = (ev) => {
    const { tick, analysis, incidents } = JSON.parse(ev.data);

    // Keep internal values
    const densityMap = {};
    tick.sensors.forEach(s => {
      densityMap[s.node] = s.density;
    });
    LATEST_DENSITY = densityMap;

    // Draw current active maps
    const activeTab = document.querySelector(".tab.active").dataset.tab;
    if (activeTab === "nav") {
      drawVenueMap("nav-map-wrapper", ACTIVE_PATH, LATEST_DENSITY);
    } else if (activeTab === "crowd") {
      drawVenueMap("crowd-map-wrapper", [], LATEST_DENSITY);
    }

    // Updates components
    updateMatchClock(tick);
    renderCrowd(tick, analysis);
    renderOps(analysis);
    updateSustainabilityStats();

    // Check for new incident toasts
    if (tick.incident && !SHOWN_TOASTS.has(tick.incident.id)) {
      SHOWN_TOASTS.add(tick.incident.id);
      showToast(`🔥 Alert: ${tick.incident.severity.toUpperCase()} incident reported: ${tick.incident.kind} at ${NODES_COORDS[tick.incident.node].name}!`, "critical");
    }
  };

  ws.onerror = () => {
    el("crowd-status").textContent = "Live simulator feed disconnected.";
  };

  ws.onclose = () => {
    setTimeout(startLive, 3000); // auto reconnect
  };
}

function updateMatchClock(tick) {
  const clock = el("match-clock-time");
  if (!clock) return;

  let phaseText = tick.phase.toUpperCase().replace("_", " ");
  clock.innerHTML = `Min: <strong>${tick.minute}</strong> (${phaseText})`;
}

function renderCrowd(tick, analysis) {
  el("crowd-status").innerHTML =
    `Phase: <strong>${tick.phase}</strong> · Match min: <strong>${tick.minute}</strong> · ` +
    `Trend: <strong>${analysis.trend.toUpperCase()}</strong> · ${analysis.summary}`;

  const alerts = el("crowd-alerts");
  if (!analysis.alerts.length) {
    alerts.innerHTML = `<div class="alert"><span class="badge ok">Nominal</span> No active bottlenecks reported.</div>`;
  } else {
    alerts.innerHTML = analysis.alerts.map(a =>
      `<div class="alert ${a.level}">
         <div class="alert-header">
           <strong>${a.name}</strong>
           <span class="badge ${a.level}">${a.level}</span>
         </div>
         <div>Density: <strong>${(a.density * 100).toFixed(0)}%</strong></div>
         <div style="margin-top:6px;">↪ ${a.reroute}</div>
         <div style="margin-top:4px; font-size:0.92rem; color:var(--muted)">👷 Steward guide: ${a.staff_guidance}</div>
       </div>`).join("");
  }

  // Render heatmap tiles
  el("crowd-heat").innerHTML = analysis.hotspots.map(h => {
    let d = h.density;
    let nodeColor = "#10b981"; // ok
    if (d >= 0.9) nodeColor = "#ef4444"; // crit
    else if (d >= 0.75) nodeColor = "#f59e0b"; // warn
    else if (d >= 0.5) nodeColor = "#fbbf24"; // medium

    return `<div class="heat-cell" style="background:${nodeColor}" 
      title="${h.name}: ${(h.density * 100).toFixed(0)}%">${h.name}<br>${(h.density * 100).toFixed(0)}%</div>`;
  }).join("");
}

function renderOps(analysis) {
  el("ops-summary").innerHTML = `⚡ <strong>Operations Summary:</strong> ${analysis.summary}`;

  const crit = analysis.alerts.filter(a => a.level === "critical").length;
  const warn = analysis.alerts.filter(a => a.level === "warning").length;
  const peak = analysis.hotspots[0];

  el("ops-kpis").innerHTML = `
    <div class="kpi">
      <div class="num" style="color:var(--crit)">${analysis.alerts.length}</div>
      <div class="lbl">Active Alerts (${crit} crit / ${warn} warn)</div>
    </div>
    <div class="kpi">
      <div class="num" style="color:var(--accent)">${(analysis.intensity * 100).toFixed(0)}%</div>
      <div class="lbl">Crowd Pressure</div>
    </div>
    <div class="kpi">
      <div class="num">${peak ? peak.name.split(" ")[0] : "—"}</div>
      <div class="lbl">Busiest Zone (${(peak ? peak.density * 100 : 0).toFixed(0)}%)</div>
    </div>
    <div class="kpi">
      <div class="num" style="color:var(--accent2)">${analysis.trend.toUpperCase()}</div>
      <div class="lbl">Predictive Trend</div>
    </div>`;

  // Render live dispatches + incident log
  const logDiv = el("ops-incidents");
  let html = `<div class="card" style="border-left:4px solid var(--accent2);"><strong>Recommended Steward Deployment:</strong> ${analysis.staff_allocation || "Nominal staffing sufficient."}</div>`;

  if (analysis.incidents && analysis.incidents.length > 0) {
    const list = [...analysis.incidents].reverse(); // latest first
    list.forEach(inc => {
      const locationName = NODES_COORDS[inc.node] ? NODES_COORDS[inc.node].name : inc.node;
      let sevColor = "ok";
      if (inc.severity === "high") sevColor = "critical";
      else if (inc.severity === "medium") sevColor = "warning";

      html += `
        <div class="alert ${sevColor}">
          <div class="alert-header">
            <strong>${inc.kind.toUpperCase()} - Reported at Min ${inc.minute}</strong>
            <span class="badge ${sevColor}">${inc.severity} Severity</span>
          </div>
          <div>Location Node: <strong>${locationName}</strong></div>
          <div class="ai-recommendation-box">
            <strong>StadiumGenius AI Copilot Response Actions:</strong><br>
            <div style="white-space: pre-wrap; margin-top: 6px;">${inc.response_steps || "Analyzing incident context and generating emergency dispatches..."}</div>
          </div>
        </div>
      `;
    });
  } else {
    html += `<div class="alert"><span class="badge ok">nominal</span> No active safety dispatches logged.</div>`;
  }

  logDiv.innerHTML = html;
}

/* ---------- Init ---------- */
(async function init() {
  await loadLanguages();
  await loadNodes();

  // Initial draw
  drawVenueMap("nav-map-wrapper", [], {});
  drawVenueMap("crowd-map-wrapper", [], {});

  startLive();
})();
