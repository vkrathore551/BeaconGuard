
"""
BEACONGUARD — THE LAST BEACON
Emergency survival and route-planning dashboard.

Install:
    python -m pip install streamlit folium streamlit-folium requests

Run:
    python -m streamlit run ui.py --server.port 8503
"""

from collections import deque
import random
import html

import requests
import streamlit as st
import folium
from streamlit_folium import st_folium


# ============================================================
# 1. PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="BeaconGuard | The Last Beacon",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 2. SIMULATION SETTINGS — STRICTLY 10 x 10
# ============================================================

GRID_SIZE = 10

FRIENDS = {
    "Aarav": (0, 0),
    "Mira": (0, 2),
}

BEACON = (9, 9)

DEFAULT_DANGER_ZONES = {
    (1, 3), (2, 3), (3, 3),
    (4, 6), (5, 6), (6, 2), (7, 7),
}

MOVES = (
    (1, 0),
    (-1, 0),
    (0, 1),
    (0, -1),
)

OBSTACLES = {
    (0, 5), (1, 5), (2, 5), (3, 1),
    (3, 7), (4, 1), (5, 3), (6, 6),
    (7, 2), (8, 4), (8, 7),
}


# ============================================================
# 3. PROFESSIONAL DARK THEME
# ============================================================

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    .stApp {
        background: radial-gradient(
            circle at 10% 0%,
            #132b45 0%,
            #081321 48%,
            #07101c 100%
        );
        color: #edf5ff;
    }

    [data-testid="stHeader"] {
        background: rgba(7, 16, 28, .88);
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #102137, #091321);
        border-right: 1px solid #263d56;
    }

    [data-testid="stSidebar"] * {
        color: #eaf3ff;
    }

    h1, h2, h3, h4, p, label {
        color: #edf5ff;
    }

    .hero {
        padding: 28px 30px;
        border: 1px solid #2b4b6a;
        border-radius: 20px;
        background: linear-gradient(120deg, #163858, #0e2035);
        margin-bottom: 18px;
    }

    .eyebrow {
        color: #76c9ff;
        text-transform: uppercase;
        letter-spacing: 2px;
        font-size: 11px;
        font-weight: 800;
    }

    .hero-title {
        font-size: clamp(28px, 4vw, 44px);
        font-weight: 800;
        line-height: 1.12;
        margin: 8px 0;
        color: white;
    }

    .muted {
        color: #a8bdd3;
        font-size: 13px;
        line-height: 1.6;
    }

    .metric {
        background: linear-gradient(145deg, #152b43, #0e1d30);
        border: 1px solid #294562;
        border-radius: 16px;
        padding: 20px;
        min-height: 112px;
    }

    .metric-label {
        color: #a8c5e2;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 1px;
        text-transform: uppercase;
    }

    .metric-value {
        font-size: 29px;
        font-weight: 800;
        color: white;
        margin: 7px 0;
    }

    .metric-note {
        color: #9bb6d2;
        font-size: 12px;
    }

    .panel {
        border: 1px solid #29435e;
        border-radius: 16px;
        background: rgba(18, 37, 59, .78);
        padding: 18px;
    }

    .city-grid {
        display: grid;
        grid-template-columns: repeat(10, minmax(0, 1fr));
        gap: 5px;
        width: 100%;
    }

    .cell {
        min-width: 0;
        min-height: 54px;
        border: 1px solid #2d455d;
        border-radius: 8px;
        background: #edf3fa;
        color: #30465d;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        font-size: 18px;
        line-height: 1.1;
        overflow: hidden;
    }

    .cell small {
        color: #34495e;
        font-size: 9px;
        margin-top: 4px;
    }

    .cell.route {
        background: #c9f7df;
        border-color: #28a56a;
    }

    .cell.danger {
        background: #ffd6dc;
        border-color: #e24a66;
    }

    .cell.blocked {
        background: #343b48;
        border-color: #6c7481;
    }

    .cell.friend {
        background: #b8ddff;
        border-color: #3289d3;
    }

    .cell.beacon {
        background: #ffe4a6;
        border-color: #d99b23;
    }

    .cell.obstacle {
        background: #687386;
        border-color: #9ba7b8;
    }

    .legend {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        font-size: 12px;
        color: #bfd0e2;
        margin: 10px 0 15px;
    }

    @media (max-width: 700px) {
        .cell {
            min-height: 35px;
            font-size: 13px;
        }

        .cell small {
            font-size: 7px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 4. SESSION STATE
# ============================================================

def initialize_state():
    defaults = {
        "countdown": 180,
        "horde_cells": set(),
        "routes": {},
        "horde_active": False,
        "status": "MONITORING",
        "last_action": "System initialized",
        "log": ["Beacon signal detected. Mission ready."],
        "message": "Mission ready. Find safe routes to begin.",
        "message_type": "info",
        "route_ready": False,
        "real_route": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialize_state()


def log_event(message):
    """Keep the latest ten mission events."""
    events = list(st.session_state.log)
    events.insert(0, message)
    st.session_state.log = events[:10]


def set_message(message, kind="info"):
    st.session_state.message = message
    st.session_state.message_type = kind


# ============================================================
# 5. SAFE ROUTE ALGORITHM — BREADTH-FIRST SEARCH
# ============================================================

def find_safe_route(
    start,
    destination=BEACON,
    danger_zones=None,
    blocked_roads=None,
    grid_size=GRID_SIZE,
):
    danger = (
        set(danger_zones or ())
        | set(blocked_roads or ())
        | set(OBSTACLES)
    )

    start = tuple(start)
    destination = tuple(destination)

    if start in danger or destination in danger:
        return None

    queue = deque([(start, [start])])
    visited = {start}

    while queue:
        cell, path = queue.popleft()

        if cell == destination:
            return path

        for dr, dc in MOVES:
            nxt = (cell[0] + dr, cell[1] + dc)
            row, col = nxt

            if not (
                0 <= row < grid_size
                and 0 <= col < grid_size
            ):
                continue

            if nxt in danger or nxt in visited:
                continue

            visited.add(nxt)
            queue.append((nxt, path + [nxt]))

    return None


def calculate_routes():
    danger = (
        set(DEFAULT_DANGER_ZONES)
        | set(st.session_state.horde_cells)
    )

    results = {}

    for name, start in FRIENDS.items():
        results[name] = find_safe_route(
            start=start,
            destination=BEACON,
            danger_zones=danger,
        )

    st.session_state.routes = results
    st.session_state.route_ready = True

    return results


# ============================================================
# 6. ZOMBIE HORDE — MULTIPLE CELLS PER WAVE
# ============================================================

def trigger_horde():
    if not st.session_state.route_ready:
        calculate_routes()

    current_danger = (
        set(DEFAULT_DANGER_ZONES)
        | set(st.session_state.horde_cells)
        | set(OBSTACLES)
    )

    candidates = []

    for route in st.session_state.routes.values():
        if route and len(route) > 2:
            candidates.extend(route[1:-1])

    candidates = list(dict.fromkeys(
        cell for cell in candidates
        if cell not in current_danger
        and cell not in FRIENDS.values()
        and cell != BEACON
    ))

    if not candidates:
        candidates = [
            (r, c)
            for r in range(GRID_SIZE)
            for c in range(GRID_SIZE)
            if (r, c) not in current_danger
            and (r, c) not in FRIENDS.values()
            and (r, c) != BEACON
        ]

    if not candidates:
        set_message(
            "The grid is overwhelmed. Reset the mission to play again.",
            "error",
        )
        return

    # Add a horde wave of 5–8 new cells.
    wave_size = min(random.randint(5, 8), len(candidates))
    chosen = random.sample(candidates, wave_size)

    st.session_state.horde_cells.update(chosen)
    st.session_state.horde_active = True
    st.session_state.status = "HORDE DETECTED"
    st.session_state.last_action = (
        f"Zombie horde advanced: {wave_size} new danger cells"
    )

    routes = calculate_routes()
    available = sum(route is not None for route in routes.values())

    log_event(
        f"Horde wave detected: {wave_size} new cells blocked. "
        "Safe routes recalculated."
    )

    set_message(
        f"Horde wave detected! {wave_size} cells are now blocked. "
        f"{available}/2 survivors have a safe route.",
        "warning",
    )


# ============================================================
# 7. RESET SIMULATION
# ============================================================

def reset_simulation():
    st.session_state.countdown = 180
    st.session_state.horde_cells = set()
    st.session_state.routes = {}
    st.session_state.horde_active = False
    st.session_state.status = "MONITORING"
    st.session_state.last_action = "Simulation reset"
    st.session_state.log = [
        "Simulation reset. Beacon signal detected."
    ]
    st.session_state.route_ready = False

    set_message(
        "Mission reset. Find a safe route to begin.",
        "info",
    )


# ============================================================
# 8. DASHBOARD METRIC COMPONENT
# ============================================================

def render_metric(label, value, note):
    st.markdown(
        f'<div class="metric">'
        f'<div class="metric-label">{html.escape(str(label))}</div>'
        f'<div class="metric-value">{html.escape(str(value))}</div>'
        f'<div class="metric-note">{html.escape(str(note))}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ============================================================
# 9. SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown("## 🛡️ Mission Control")
    st.caption("THE LAST BEACON • SURVIVAL SIMULATION")

    st.divider()

    st.markdown("### 📡 Mission Briefing")
    st.markdown("**Survivors:** Aarav and Mira")
    st.markdown("**Objective:** Reach the emergency beacon")
    st.markdown(f"**Simulation grid:** {GRID_SIZE} × {GRID_SIZE}")
    st.markdown("**Route engine:** Breadth-First Search")

    st.divider()

    st.markdown("### 🎯 Objectives")
    st.markdown(
        "1. Find safe routes.\n"
        "2. Avoid danger zones.\n"
        "3. React to the zombie horde.\n"
        "4. Reach the beacon."
    )

    st.divider()

    st.caption(
        "Demonstration simulation only. "
        "Not for real emergency navigation."
    )


# ============================================================
# 10. MAIN DASHBOARD HEADER
# ============================================================

st.markdown(
    '<div class="hero">'
    '<div class="eyebrow">Emergency Survival Intelligence</div>'
    '<div class="hero-title">BEACONGUARD<br>THE LAST BEACON</div>'
    '<div class="muted">Two survivors. One beacon. Every route matters. '
    'Plan, react, survive.</div></div>',
    unsafe_allow_html=True,
)


# ============================================================
# 11. TOP METRICS
# ============================================================

danger_count = len(
    set(DEFAULT_DANGER_ZONES)
    | set(st.session_state.horde_cells)
    | set(OBSTACLES)
)

col1, col2, col3 = st.columns(3)

with col1:
    render_metric(
        "⏱ Beacon Countdown",
        f"{st.session_state.countdown}s",
        "Simulated time remaining",
    )

with col2:
    render_metric("🧍 Survivors", "02", "Aarav + Mira")

with col3:
    render_metric(
        "☣ Danger / Blocked Cells",
        danger_count,
        "Within the 10 × 10 grid",
    )


# ============================================================
# 12. EMERGENCY CONTROLS
# ============================================================

st.markdown("## 🚨 Emergency Controls")

button1, button2, button3 = st.columns(3)

with button1:
    if st.button(
        "🧭 Find Safe Routes",
        use_container_width=True,
        type="primary",
    ):
        routes = calculate_routes()
        available = sum(
            route is not None for route in routes.values()
        )

        if available == 2:
            st.session_state.status = "ROUTES CALCULATED"
            kind = "success"
        elif available == 1:
            st.session_state.status = "PARTIAL ROUTE AVAILABLE"
            kind = "warning"
        else:
            st.session_state.status = "NO SAFE ROUTES"
            kind = "error"

        st.session_state.last_action = "Safe routes calculated"

        log_event(
            f"Safe-route calculation complete: {available}/2 "
            "survivors have a route."
        )

        set_message(
            f"{available} of 2 survivors have a safe route "
            "to the beacon.",
            kind,
        )

with button2:
    if st.button(
        "🧟 Simulate Zombie Horde",
        use_container_width=True,
    ):
        trigger_horde()

with button3:
    if st.button(
        "🔄 Reset Simulation",
        use_container_width=True,
    ):
        reset_simulation()


message_type = st.session_state.message_type
message = st.session_state.message

if message_type == "warning":
    st.warning(message)
elif message_type == "error":
    st.error(message)
elif message_type == "success":
    st.success(message)
else:
    st.info(message)

st.markdown(
    f'<div class="panel"><b>Mission Status:</b> '
    f'{html.escape(st.session_state.status)}<br>'
    f'<span class="muted">Last action: '
    f'{html.escape(st.session_state.last_action)}</span></div>',
    unsafe_allow_html=True,
)


# ============================================================
# 13. SIMULATED SURVIVAL GRID — EXACTLY 100 CELLS
# ============================================================

st.markdown("## 🗺️ Simulated Survival Grid")

st.caption(
    "Fictional 10 × 10 grid. The real-world street map "
    "below is a separate feature."
)

st.markdown(
    '<div class="legend">'
    '<span>🟩 Safe route</span>'
    '<span>🟥 Danger</span>'
    '<span>🟦 Survivor</span>'
    '<span>🟨 Beacon</span>'
    '<span>🧟 Horde</span>'
    '<span>⬛ Obstacle</span>'
    '<span>⬜ Open cell</span>'
    '</div>',
    unsafe_allow_html=True,
)

route_cells = set()

for route in st.session_state.routes.values():
    if route:
        route_cells.update(route)

danger = set(DEFAULT_DANGER_ZONES)
danger.update(st.session_state.horde_cells)

friend_at = {
    position: name for name, position in FRIENDS.items()
}

grid_html = ['<div class="city-grid">']

for row in range(GRID_SIZE):
    for col in range(GRID_SIZE):
        cell = (row, col)

        symbol = "·"
        css_class = "cell"
        tooltip = "Open city cell"

        if cell in friend_at:
            symbol = "🧍"
            css_class = "cell friend"
            tooltip = friend_at[cell]

        elif cell == BEACON:
            symbol = "📡"
            css_class = "cell beacon"
            tooltip = "Emergency beacon"

        elif cell in st.session_state.horde_cells:
            symbol = "🧟"
            css_class = "cell blocked"
            tooltip = "Simulated zombie horde"

        elif cell in OBSTACLES:
            symbol = "⬛"
            css_class = "cell obstacle"
            tooltip = "Blocked by obstacle"

        elif cell in danger:
            symbol = "⚠️"
            css_class = "cell danger"
            tooltip = "Danger zone"

        elif cell in route_cells:
            symbol = "➜"
            css_class = "cell route"
            tooltip = "Safe route"

        grid_html.append(
            f'<div class="{css_class}" '
            f'title="{html.escape(tooltip)}">'
            f'{symbol}<small>{row},{col}</small></div>'
        )

grid_html.append("</div>")

st.markdown(
    "".join(grid_html),
    unsafe_allow_html=True,
)


# ============================================================
# 14. ROUTE RESULTS
# ============================================================

st.markdown("## 🧭 Safe Route Results")

if not st.session_state.route_ready:
    st.info(
        "Click **Find Safe Routes** to calculate routes "
        "for Aarav and Mira."
    )
else:
    route_columns = st.columns(2)

    for index, (name, start) in enumerate(FRIENDS.items()):
        with route_columns[index]:
            st.markdown(f"### {name}")
            route = st.session_state.routes.get(name)

            if route:
                st.success(
                    f"Safe route available • {len(route) - 1} moves"
                )

                st.code(
                    " → ".join(f"({r},{c})" for r, c in route),
                    language="text",
                )

                st.caption(f"Start: {start} · Beacon: {BEACON}")
            else:
                st.error(
                    "No safe route available with the current "
                    "danger and blocked cells."
                )


# ============================================================
# 15. REAL-WORLD MAP AND DIRECTIONS
# ============================================================

st.divider()

st.markdown("## 🌍 Real-World Street Map & Directions")

st.caption(
    "OpenStreetMap tiles and public routing services are used "
    "for route estimates. Internet access required. "
    "Demonstration only."
)

default_start = (
    "Sapthagiri NPS University, Bengaluru, Karnataka, India"
)

default_destination = (
    "Bengaluru City Railway Station, Bengaluru, Karnataka, India"
)

map_col1, map_col2 = st.columns(2)

with map_col1:
    start_text = st.text_input(
        "Start location",
        value=default_start,
        key="real_start",
    )

with map_col2:
    end_text = st.text_input(
        "Destination",
        value=default_destination,
        key="real_end",
    )


def geocode(query):
    """Find a place using the public Nominatim geocoder."""
    url = "https://nominatim.openstreetmap.org/search"

    response = requests.get(
        url,
        params={
            "q": query,
            "format": "jsonv2",
            "limit": 1,
        },
        headers={
            "User-Agent": (
                "BeaconGuardHackathonDemo/1.0 (student project)"
            )
        },
        timeout=12,
    )

    response.raise_for_status()
    results = response.json()

    if not results:
        raise ValueError(f"Location not found: {query}")

    result = results[0]

    return (
        float(result["lat"]),
        float(result["lon"]),
        result.get("display_name", query),
    )


if st.button(
    "🌐 Find Real Road Directions",
    type="primary",
    use_container_width=True,
):
    if not start_text.strip() or not end_text.strip():
        set_message(
            "Enter both a start location and destination.",
            "error",
        )
    else:
        with st.spinner(
            "Looking up locations and requesting road directions..."
        ):
            try:
                start_lat, start_lon, start_label = geocode(
                    start_text.strip()
                )

                end_lat, end_lon, end_label = geocode(
                    end_text.strip()
                )

                route_url = (
                    "https://router.project-osrm.org/route/v1/"
                    f"driving/{start_lon},{start_lat};"
                    f"{end_lon},{end_lat}"
                )

                response = requests.get(
                    route_url,
                    params={
                        "overview": "full",
                        "geometries": "geojson",
                        "steps": "true",
                    },
                    timeout=20,
                )

                response.raise_for_status()
                payload = response.json()

                if (
                    payload.get("code") != "Ok"
                    or not payload.get("routes")
                ):
                    raise ValueError(
                        "The routing service could not find "
                        "a drivable route."
                    )

                route_data = payload["routes"][0]

                coordinates = [
                    (lat, lon)
                    for lon, lat
                    in route_data["geometry"]["coordinates"]
                ]

                st.session_state.real_route = {
                    "start": (
                        start_lat,
                        start_lon,
                        start_label,
                    ),
                    "end": (
                        end_lat,
                        end_lon,
                        end_label,
                    ),
                    "coords": coordinates,
                    "distance": route_data["distance"],
                    "duration": route_data["duration"],
                    "legs": route_data.get("legs", []),
                }

                log_event("Real-world route directions requested.")

                set_message(
                    "Real-world route loaded successfully.",
                    "success",
                )

            except requests.RequestException:
                set_message(
                    "Could not reach the map service. Check your "
                    "internet connection and try again.",
                    "error",
                )

            except (ValueError, KeyError, IndexError) as exc:
                set_message(str(exc), "error")


# ============================================================
# 16. DISPLAY REAL-WORLD ROUTE — FIXED MAP SCOPE
# ============================================================

real_route = st.session_state.real_route

if real_route:
    start_lat, start_lon, start_label = real_route["start"]
    end_lat, end_lon, end_label = real_route["end"]

    real_map = folium.Map(
        location=[
            (start_lat + end_lat) / 2,
            (start_lon + end_lon) / 2,
        ],
        zoom_start=12,
        control_scale=True,
        tiles="OpenStreetMap",
    )

    folium.Marker(
        [start_lat, start_lon],
        tooltip="Start",
        popup=html.escape(start_label),
        icon=folium.Icon(color="green", icon="play"),
    ).add_to(real_map)

    folium.Marker(
        [end_lat, end_lon],
        tooltip="Destination",
        popup=html.escape(end_label),
        icon=folium.Icon(color="red", icon="flag"),
    ).add_to(real_map)

    # Fictional demonstration markers, not live threats.
    zombie_locations = [
        (13.0350, 77.5190, "Zombie Horde Alpha"),
        (13.0550, 77.5350, "Zombie Horde Beta"),
        (13.0200, 77.5000, "Zombie Horde Gamma"),
    ]

    for zombie_lat, zombie_lon, zombie_name in zombie_locations:
        folium.Marker(
            location=[zombie_lat, zombie_lon],
            tooltip=zombie_name,
            popup=(
                f"⚠️ {html.escape(zombie_name)} — "
                "simulated danger marker, not a real alert"
            ),
            icon=folium.DivIcon(
                html=(
                    '<div style="background:#ff3030;color:white;'
                    'border:2px solid white;border-radius:50%;'
                    'width:34px;height:34px;text-align:center;'
                    'line-height:30px;font-size:20px;'
                    'box-shadow:0 0 12px #ff3030">🧟</div>'
                )
            ),
        ).add_to(real_map)

    folium.PolyLine(
        real_route["coords"],
        color="#00a6ff",
        weight=6,
        opacity=0.9,
        tooltip="Suggested driving route",
    ).add_to(real_map)

    real_map.fit_bounds(
        [
            [start_lat, start_lon],
            [end_lat, end_lon],
        ]
    )

    st_folium(
        real_map,
        width=None,
        height=480,
        returned_objects=[],
    )

    distance_km = real_route["distance"] / 1000
    duration_min = real_route["duration"] / 60

    metric1, metric2 = st.columns(2)

    with metric1:
        render_metric(
            "🚗 Route Distance",
            f"{distance_km:.1f} km",
            "Estimated road distance",
        )

    with metric2:
        render_metric(
            "⏱ Estimated Drive",
            f"{duration_min:.0f} min",
            "Traffic conditions may change this",
        )

    st.markdown("### Turn-by-Turn Directions")

    for leg in real_route.get("legs", []):
        for step in leg.get("steps", []):
            maneuver = step.get("maneuver", {})
            road_name = step.get("name") or "unnamed road"

            action = (
                maneuver.get("instruction")
                or maneuver.get("type", "Continue")
                .replace("_", " ")
                .title()
            )

            st.markdown(
                f"- **{html.escape(str(action))}** on "
                f"**{html.escape(str(road_name))}** — "
                f"{step.get('distance', 0):.0f} m"
            )

else:
    st.info(
        "Enter locations and click **Find Real Road Directions**. "
        "The survival grid works even if public map services "
        "are unavailable."
    )


# ============================================================
# 17. MISSION UPDATE AND EVENT LOG
# ============================================================

left_col, right_col = st.columns([1.2, 1])

with left_col:
    st.markdown("## 📍 Mission Update")

    st.markdown(
        f'<div class="panel"><b>'
        f'{html.escape(st.session_state.status)}</b><br>'
        f'<span class="muted">Last action: '
        f'{html.escape(st.session_state.last_action)}</span><hr>'
        '<span class="muted">Hackathon demonstration only. '
        'Real emergencies require verified official information '
        'and human judgment.</span></div>',
        unsafe_allow_html=True,
    )

with right_col:
    st.markdown("## 🛰️ Mission Event Log")

    with st.container(border=True):
        for event in st.session_state.log:
            st.markdown(f"• {html.escape(str(event))}")


# ============================================================
# 18. FOOTER
# ============================================================

st.divider()

st.markdown(
    '<div style="text-align:center;color:#91a9c2;'
    'font-size:11px;padding:10px;">'
    'BEACONGUARD • THE LAST BEACON<br>'
    'Survival route simulation + OpenStreetMap directions'
    '</div>',
    unsafe_allow_html=True,
)


