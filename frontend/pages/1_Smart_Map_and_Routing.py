import os
import sys
import folium
import requests
import streamlit as st
from streamlit_folium import st_folium

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from services.routing_engine import compute_safe_detour_route, evaluate_area_road_status

BACKEND_URL = os.getenv("FREEDOM_BACKEND_URL", "http://127.0.0.1:8080")

st.set_page_config(
    page_title="Smart Map & Routing | FreeDom",
    page_icon="🗺️",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #d7dce8 0%, #c6cfe6 100%);
    }
    .map-banner {
        background: linear-gradient(135deg, #141136 0%, #261c6e 60%, #4a396c 100%);
        color: #ffffff;
        padding: 1.3rem 1.7rem;
        border-radius: 14px;
        border-left: 6px solid #f5b942;
        margin-bottom: 1.1rem;
    }
    .map-banner h1 {
        color: #f5b942 !important;
        margin: 0 0 0.3rem 0 !important;
        font-size: 1.85rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="map-banner">
        <h1>🗺️ FreeDom Smart Accessibility Map & Multi-Modal Safe Routing</h1>
        <p style="margin:0; color:#e2e8f0;">
            Select any area on the map to inspect real-time road status, vehicle compatibility (2W/3W/4W),
            wheelchair & elder safety, and Municipal vs. Citizen action zones.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


def fetch_audits():
    try:
        resp = requests.get(f"{BACKEND_URL}/api/audits", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                return data
            return data.get("results") or data.get("audits") or data.get("items") or []
    except Exception as exc:
        st.error(f"Cannot reach FastAPI backend at {BACKEND_URL}: {exc}")
    return []


audits = fetch_audits()

if "inspect_lat" not in st.session_state:
    st.session_state.inspect_lat = 28.613900
if "inspect_lon" not in st.session_state:
    st.session_state.inspect_lon = 77.209000

col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([1, 1, 1])
with col_ctrl1:
    st.session_state.inspect_lat = st.number_input("Inspect Latitude", value=float(st.session_state.inspect_lat), format="%.6f")
with col_ctrl2:
    st.session_state.inspect_lon = st.number_input("Inspect Longitude", value=float(st.session_state.inspect_lon), format="%.6f")
with col_ctrl3:
    scan_radius = st.slider("Area Inspection Radius (km)", min_value=0.2, max_value=5.0, value=1.0, step=0.2)

status = evaluate_area_road_status(
    audits=audits,
    center_lat=st.session_state.inspect_lat,
    center_lon=st.session_state.inspect_lon,
    radius_km=scan_radius,
)

m1, m2, m3, m4 = st.columns(4)
m1.metric("🛡️ Area Safety Score", f"{status.get('area_score', status.get('accessibility_score', 50))}/100")
m2.metric("🚨 Severe Hazards (RED)", status["red_count"])
m3.metric("⚠️ Minor Repairs (YELLOW)", status["yellow_count"])
m4.metric("📍 Total Active Pins", status["nearby_count"])

map_col, info_col = st.columns([1.45, 1])

with map_col:
    st.subheader("Interactive Hazard & Safe-Route Map (Click Anywhere to Inspect)")
    fmap = folium.Map(
        location=[st.session_state.inspect_lat, st.session_state.inspect_lon],
        zoom_start=15,
        tiles="OpenStreetMap",
    )

    folium.Circle(
        location=[st.session_state.inspect_lat, st.session_state.inspect_lon],
        radius=scan_radius * 1000,
        color="#261c6e",
        fill=True,
        fill_opacity=0.08,
        tooltip="Selected Inspection Zone",
    ).add_to(fmap)

    for item in audits:
        try:
            alat = float(item.get("latitude", 0.0))
            alon = float(item.get("longitude", 0.0))
            sev = item.get("severity_level", "YELLOW")
            tid = item.get("ticket_id", "N/A")
            tstatus = item.get("ticket_status", "OPEN")
            color = "green" if tstatus == "RESOLVED" else ("red" if sev == "RED" else "orange")

            folium.Marker(
                location=[alat, alon],
                popup=f"<b>{tid}</b> ({sev})<br>Status: {tstatus}<br>{item.get('reroute_suggestion', '')}",
                tooltip=f"{tid} — {sev} ({tstatus})",
                icon=folium.Icon(color=color, icon="exclamation-sign" if sev == "RED" else "info-sign"),
            ).add_to(fmap)

            if tstatus != "RESOLVED" and sev in {"RED", "YELLOW"}:
                folium.Circle(
                    location=[alat, alon],
                    radius=45 if sev == "RED" else 25,
                    color="#dc2626" if sev == "RED" else "#f59e0b",
                    fill=True,
                    fill_opacity=0.25,
                ).add_to(fmap)
        except Exception:
            continue

    st.markdown("**Plan Barrier-Free / Safe Vehicle Route**")
    r_c1, r_c2, r_c3 = st.columns(3)
    with r_c1:
        dest_lat = st.number_input("Destination Lat", value=round(st.session_state.inspect_lat + 0.0045, 6), format="%.6f")
    with r_c2:
        dest_lon = st.number_input("Destination Lon", value=round(st.session_state.inspect_lon + 0.0045, 6), format="%.6f")
    with r_c3:
        travel_mode = st.selectbox(
            "Traveler / Vehicle Mode",
            ["Wheelchair / Elder", "Visually Impaired (Cane)", "Two-Wheeler / Cycle", "Three-Wheeler / Auto", "Four-Wheeler / Car"],
        )

    route_coords, route_note = compute_safe_detour_route(
        start_lat=st.session_state.inspect_lat,
        start_lon=st.session_state.inspect_lon,
        end_lat=dest_lat,
        end_lon=dest_lon,
        audits=audits,
        travel_mode=travel_mode,
    )

    folium.PolyLine(
        locations=route_coords,
        color="#f5b942",
        weight=6,
        opacity=0.95,
        dash_array="10, 6",
        tooltip=route_note,
    ).add_to(fmap)

    folium.Marker(
        location=[dest_lat, dest_lon],
        tooltip="Destination Safe Zone",
        icon=folium.Icon(color="darkblue", icon="flag"),
    ).add_to(fmap)

    map_state = st_folium(fmap, height=470, width=None)
    if map_state and map_state.get("last_clicked"):
        clicked = map_state["last_clicked"]
        if abs(clicked["lat"] - st.session_state.inspect_lat) > 1e-6 or abs(clicked["lng"] - st.session_state.inspect_lon) > 1e-6:
            st.session_state.inspect_lat = round(clicked["lat"], 6)
            st.session_state.inspect_lon = round(clicked["lng"], 6)
            st.rerun()

    st.success(f"🧭 **Route Guidance:** {route_note}")

with info_col:
    st.subheader("Area Road Status & Vehicle Safety")
    with st.container(border=True):
        st.markdown("**♿ Wheelchair & Stroller Passability**")
        if "UNSAFE" in status["wheelchair_status"]:
            st.error(status["wheelchair_status"])
        elif "CAUTION" in status["wheelchair_status"]:
            st.warning(status["wheelchair_status"])
        else:
            st.success(status["wheelchair_status"])

        st.markdown("**🦯 Elders & Visually Impaired Safety**")
        if "UNSAFE" in status["elder_blind_status"]:
            st.error(status["elder_blind_status"])
        elif "CAUTION" in status["elder_blind_status"]:
            st.warning(status["elder_blind_status"])
        else:
            st.success(status["elder_blind_status"])

    with st.container(border=True):
        st.markdown("**🚗 Vehicle Compatibility Verdict**")
        st.write(f"• **Two-Wheelers / Cycles:** {status['two_wheeler_status']}")
        st.write(f"• **Three-Wheelers / Autos:** {status['three_wheeler_status']}")
        st.write(f"• **Four-Wheelers / Cars:** {status['four_wheeler_status']}")

    with st.container(border=True):
        st.markdown("**🏛️ Municipal vs. Citizen Action Track**")
        st.info(status["civic_summary"])
