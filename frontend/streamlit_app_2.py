import io
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

import requests
import streamlit as st
from PIL import Image, ExifTags

# Ensure project root is importable for local fallback
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    from freedom_accessibility_auditor_v4.services.vision_auditor2 import analyze_footpath_image
except Exception:
    analyze_footpath_image = None

BACKEND_URL = os.getenv("FREEDOM_BACKEND_URL", "http://127.0.0.1:8080")

st.set_page_config(
    page_title="FreeDom | Footpath & Road Accessibility Auditor",
    page_icon="👁️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# 1. GLOBAL STYLING: GREY + LIGHT INDIGO CANVAS WITH HIGH-CONTRAST HUD
# ---------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
.stApp {
    background: linear-gradient(155deg, #d8dde9 0%, #c8d1e8 50%, #bcc6e2 100%);
    color: #141136;
}
[data-testid="stSidebar"] {
    background-color: #141136;
}
[data-testid="stSidebar"] * {
    color: #f4f6fb !important;
}
.freedom-hero {
    background: linear-gradient(135deg, #0c0a24 0%, #1b174a 60%, #262063 100%);
    border: 2px solid #f5b942;
    border-radius: 16px;
    padding: 22px 28px;
    margin-bottom: 18px;
    box-shadow: 0 12px 30px rgba(12, 10, 36, 0.25);
}
.freedom-title {
    font-size: 2.35rem;
    font-weight: 900;
    letter-spacing: 1px;
    color: #ffffff;
    margin: 0;
}
.freedom-title span {
    color: #f5b942;
}
.freedom-acronym {
    font-size: 1.05rem;
    font-weight: 700;
    color: #f5b942;
    letter-spacing: 1.5px;
    margin-top: 4px;
    text-transform: uppercase;
}
.freedom-tagline {
    font-size: 0.98rem;
    color: #e2e8f8;
    margin-top: 6px;
    font-weight: 500;
}
.status-pill-online {
    display: inline-block;
    background: rgba(16, 185, 129, 0.2);
    border: 1px solid #10b981;
    color: #a7f3d0;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 700;
    font-family: monospace;
}
.status-pill-offline {
    display: inline-block;
    background: rgba(245, 158, 11, 0.2);
    border: 1px solid #f59e0b;
    color: #fde68a;
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 700;
    font-family: monospace;
}
.signin-card {
    background: rgba(255, 255, 255, 0.94);
    border: 2px solid #141136;
    border-radius: 16px;
    padding: 20px 24px;
    box-shadow: 0 10px 25px rgba(20, 17, 54, 0.14);
}
.hud-stage {
    position: relative;
    background-color: #08071a;
    background-image:
        linear-gradient(to right, rgba(245, 185, 66, 0.16) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(245, 185, 66, 0.16) 1px, transparent 1px),
        linear-gradient(to right, rgba(139, 90, 43, 0.35) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(139, 90, 43, 0.35) 1px, transparent 1px);
    background-size: 24px 24px, 24px 24px, 120px 120px, 120px 120px;
    border: 2px solid #f5b942;
    border-radius: 16px;
    padding: 14px;
    overflow: hidden;
    box-shadow: 0 14px 34px rgba(8, 7, 26, 0.38);
}
.hud-laser-v {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 3px;
    background: linear-gradient(to bottom, transparent, #f5b942, #ffffff, #f5b942, transparent);
    box-shadow: 0 0 16px 4px rgba(245, 185, 66, 0.75);
    animation: laserSweepX 3.8s ease-in-out infinite alternate;
    pointer-events: none;
    z-index: 5;
}
@keyframes laserSweepX {
    0%   { left: 4%; }
    100% { left: 96%; }
}
@keyframes spinCW {
    0%   { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
@keyframes spinCCW {
    0%   { transform: rotate(360deg); }
    100% { transform: rotate(0deg); }
}
@keyframes pupilTrack {
    0%   { transform: translate(0px, 0px); }
    20%  { transform: translate(-18px, -4px); }
    45%  { transform: translate(20px, 3px); }
    70%  { transform: translate(-12px, 5px); }
    100% { transform: translate(0px, 0px); }
}
@keyframes hudPulse {
    0%, 100% { opacity: 0.75; }
    50%      { opacity: 1.0; }
}
.spin-cw {
    transform-origin: 350px 145px;
    animation: spinCW 16s linear infinite;
}
.spin-ccw {
    transform-origin: 350px 145px;
    animation: spinCCW 11s linear infinite;
}
.pupil-scan {
    animation: pupilTrack 5s ease-in-out infinite;
}
.hud-blink {
    animation: hudPulse 1.8s ease-in-out infinite;
}
@keyframes marchRight {
    0%   { transform: translateX(0px); }
    50%  { transform: translateX(18px); }
    100% { transform: translateX(0px); }
}
@keyframes hurrahPop {
    0%, 100% { transform: scale(1); }
    50%      { transform: scale(1.07); }
}
.march-anim {
    animation: marchRight 3.2s ease-in-out infinite;
}
.hurrah-badge {
    transform-origin: 560px 38px;
    animation: hurrahPop 1.6s ease-in-out infinite;
}
</style>
"""

# ---------------------------------------------------------------------------
# 2. CLEAN, UNINDENTED SVG: GRID-MESH YOLO VIGILANCE EYE & ROAD SCANNER
# ---------------------------------------------------------------------------
GRID_YOLO_EYE_HTML = """
<div class="hud-stage">
<div class="hud-laser-v"></div>
<svg viewBox="0 0 700 290" width="100%" xmlns="http://www.w3.org/2000/svg">
<defs>
<radialGradient id="irisGrad" cx="50%" cy="50%" r="50%">
<stop offset="0%" stop-color="#09071c"/>
<stop offset="32%" stop-color="#1a154d"/>
<stop offset="64%" stop-color="#8b5a2b"/>
<stop offset="88%" stop-color="#f5b942"/>
<stop offset="100%" stop-color="#fff4cc"/>
</radialGradient>
<radialGradient id="scleraGrad" cx="50%" cy="50%" r="55%">
<stop offset="0%" stop-color="#ffffff"/>
<stop offset="72%" stop-color="#e9edf7"/>
<stop offset="100%" stop-color="#b4bfe0"/>
</radialGradient>
<clipPath id="eyeClip">
<path d="M 155,145 Q 350,24 545,145 Q 350,266 155,145 Z"/>
</clipPath>
<pattern id="eyeMesh" width="16" height="16" patternUnits="userSpaceOnUse">
<path d="M 16 0 L 0 0 0 16" fill="none" stroke="#141136" stroke-width="0.65" stroke-opacity="0.28"/>
<circle cx="0" cy="0" r="1.1" fill="#8b5a2b" fill-opacity="0.45"/>
</pattern>
</defs>

<!-- Outer YOLO Detection Bounding Box -->
<rect x="132" y="34" width="436" height="222" fill="rgba(20,17,54,0.32)" stroke="#f5b942" stroke-width="1.6" stroke-dasharray="8 5" rx="6"/>
<!-- Corner Target Brackets -->
<path d="M 124,58 L 124,26 L 160,26" fill="none" stroke="#f5b942" stroke-width="3.5"/>
<path d="M 540,26 L 576,26 L 576,58" fill="none" stroke="#f5b942" stroke-width="3.5"/>
<path d="M 124,232 L 124,264 L 160,264" fill="none" stroke="#f5b942" stroke-width="3.5"/>
<path d="M 540,264 L 576,264 L 576,232" fill="none" stroke="#f5b942" stroke-width="3.5"/>

<!-- Top YOLO Class Label Pill -->
<rect x="132" y="10" width="295" height="22" fill="#f5b942" rx="4"/>
<text x="142" y="25" fill="#0d0b26" font-family="monospace" font-size="12" font-weight="900">YOLO_VIGILANCE_EYE :: CONF 0.996</text>
<text x="455" y="25" fill="#f5b942" font-family="monospace" font-size="11" font-weight="700" class="hud-blink">[ROAD_SCAN: ACTIVE]</text>

<!-- Left & Right Telemetry Coordinates -->
<text x="16" y="48" fill="#f5b942" font-family="monospace" font-size="10">GRID_X: 120px</text>
<text x="16" y="64" fill="#c8d1e8" font-family="monospace" font-size="10">PATH_MESH: ON</text>
<text x="16" y="80" fill="#d49b54" font-family="monospace" font-size="10">HAZARD_LOCK: 1</text>

<text x="588" y="48" fill="#f5b942" font-family="monospace" font-size="10">MODE: DOMINATE</text>
<text x="588" y="64" fill="#c8d1e8" font-family="monospace" font-size="10">DETECT: CRACKS</text>
<text x="588" y="80" fill="#10b981" font-family="monospace" font-size="10">SHIELD: ALL</text>

<!-- Eye Sclera + Overlaid Wireframe Grid Mesh -->
<path d="M 155,145 Q 350,24 545,145 Q 350,266 155,145 Z" fill="url(#scleraGrad)" stroke="#f5b942" stroke-width="3.2"/>
<g clip-path="url(#eyeClip)">
<rect x="150" y="20" width="400" height="250" fill="url(#eyeMesh)"/>
<!-- Perspective Road Detection Lines Inside Eye -->
<line x1="350" y1="145" x2="180" y2="255" stroke="#8b5a2b" stroke-width="1.3" stroke-dasharray="4 3"/>
<line x1="350" y1="145" x2="520" y2="255" stroke="#8b5a2b" stroke-width="1.3" stroke-dasharray="4 3"/>
<line x1="155" y1="145" x2="545" y2="145" stroke="#141136" stroke-width="1" stroke-opacity="0.45"/>

<!-- Vigilant Tracking Iris + Pupil -->
<g class="pupil-scan">
<circle cx="350" cy="145" r="68" fill="url(#irisGrad)" stroke="#141136" stroke-width="3"/>
<circle cx="350" cy="145" r="54" fill="none" stroke="#f5b942" stroke-width="1.5" stroke-dasharray="6 4"/>
<circle cx="350" cy="145" r="28" fill="#09071c" stroke="#f5b942" stroke-width="2"/>
<!-- Inner Crosshair & Specular Glint -->
<line x1="315" y1="145" x2="385" y2="145" stroke="#f5b942" stroke-width="1" stroke-opacity="0.8"/>
<line x1="350" y1="110" x2="350" y2="180" stroke="#f5b942" stroke-width="1" stroke-opacity="0.8"/>
<circle cx="339" cy="134" r="6.5" fill="#ffffff" fill-opacity="0.92"/>
<circle cx="361" cy="154" r="2.8" fill="#f5b942" fill-opacity="0.85"/>
</g>
</g>

<!-- Counter-Rotating Calibration Rings -->
<circle cx="350" cy="145" r="88" fill="none" stroke="#f5b942" stroke-width="1.6" stroke-dasharray="14 8 3 8" class="spin-cw"/>
<circle cx="350" cy="145" r="102" fill="none" stroke="#8b5a2b" stroke-width="1.4" stroke-dasharray="5 7" class="spin-ccw"/>

<!-- Bottom Telemetry Bar -->
<text x="135" y="280" fill="#f5b942" font-family="monospace" font-size="11" font-weight="700">DETECT: POTHOLES · CRACKS · ENCROACHMENTS</text>
<text x="455" y="280" fill="#ffffff" font-family="monospace" font-size="11" font-weight="700">ELIMINATE BARRIERS</text>
</svg>
</div>
"""

# ---------------------------------------------------------------------------
# 3. CLEAN, UNINDENTED SVG: INCLUSIVE DESTINATION CELEBRATION ("HURRAH!")
# ---------------------------------------------------------------------------
INCLUSIVE_JOURNEY_HTML = """
<div style="background:#0f0d2e; border:2px solid #f5b942; border-radius:14px; padding:12px; margin-bottom:12px;">
<svg viewBox="0 0 680 185" width="100%" xmlns="http://www.w3.org/2000/svg">
<!-- Sky & Horizon -->
<rect x="0" y="0" width="680" height="82" fill="#171442" rx="8"/>
<text x="16" y="24" fill="#f5b942" font-family="sans-serif" font-size="12" font-weight="800">AUDITED SAFE CORRIDOR :: ZERO BARRIERS</text>

<!-- Safe Destination Arch & Banner -->
<rect x="520" y="14" width="145" height="156" fill="rgba(16,185,129,0.16)" stroke="#10b981" stroke-width="2" stroke-dasharray="5 3" rx="8"/>
<g class="hurrah-badge">
<rect x="528" y="22" width="129" height="32" fill="#10b981" rx="6"/>
<text x="592" y="37" text-anchor="middle" fill="#08071a" font-family="sans-serif" font-size="11" font-weight="900">HURRAH! 🎉</text>
<text x="592" y="49" text-anchor="middle" fill="#08071a" font-family="sans-serif" font-size="8.5" font-weight="800">SAFE FOR ALL</text>
</g>

<!-- Upper Tactile Footpath -->
<rect x="0" y="82" width="680" height="48" fill="#cbd5e1"/>
<line x1="0" y1="106" x2="680" y2="106" stroke="#f5b942" stroke-width="2" stroke-dasharray="10 6"/>
<text x="12" y="96" fill="#141136" font-family="monospace" font-size="9" font-weight="700">TACTILE FOOTPATH (1.8m CLEAR)</text>

<!-- Lower Audited Roadway -->
<rect x="0" y="130" width="680" height="50" fill="#1e293b" rx="4"/>
<line x1="0" y1="155" x2="680" y2="155" stroke="#ffffff" stroke-width="2" stroke-dasharray="16 12"/>
<text x="12" y="174" fill="#94a3b8" font-family="monospace" font-size="9" font-weight="700">VERIFIED ROADWAY (POTHOLE-FREE)</text>

<!-- Inclusive Travelers Moving Safely Toward Destination -->
<g class="march-anim">
<!-- 1. Wheelchair User -->
<circle cx="95" cy="76" r="6" fill="#f5b942"/>
<path d="M 95,83 L 95,98 L 108,98 L 111,110" fill="none" stroke="#141136" stroke-width="3" stroke-linecap="round"/>
<circle cx="94" cy="107" r="10" fill="none" stroke="#141136" stroke-width="3"/>
<circle cx="111" cy="113" r="4" fill="#141136"/>

<!-- 2. Visually Impaired Traveler with White Cane -->
<circle cx="195" cy="72" r="6" fill="#f5b942"/>
<line x1="195" y1="79" x2="195" y2="100" stroke="#141136" stroke-width="3"/>
<line x1="195" y1="100" x2="188" y2="116" stroke="#141136" stroke-width="3"/>
<line x1="195" y1="100" x2="203" y2="116" stroke="#141136" stroke-width="3"/>
<line x1="199" y1="88" x2="225" y2="116" stroke="#ffffff" stroke-width="2.5"/>
<circle cx="226" cy="116" r="2.5" fill="#ef4444"/>

<!-- 3. Elder with Walking Stick -->
<circle cx="295" cy="74" r="6" fill="#e2e8f0"/>
<path d="M 295,81 Q 299,91 295,101" fill="none" stroke="#8b5a2b" stroke-width="3.2"/>
<line x1="295" y1="101" x2="290" y2="116" stroke="#8b5a2b" stroke-width="3"/>
<line x1="295" y1="101" x2="301" y2="116" stroke="#8b5a2b" stroke-width="3"/>
<line x1="303" y1="88" x2="306" y2="116" stroke="#f5b942" stroke-width="2.5"/>

<!-- 4. Pedestrian Celebrating Arrival -->
<circle cx="435" cy="71" r="6" fill="#f5b942"/>
<line x1="435" y1="78" x2="435" y2="100" stroke="#141136" stroke-width="3"/>
<polyline points="424,68 435,82 446,68" fill="none" stroke="#141136" stroke-width="2.6"/>
<line x1="435" y1="100" x2="429" y2="116" stroke="#141136" stroke-width="3"/>
<line x1="435" y1="100" x2="442" y2="116" stroke="#141136" stroke-width="3"/>

<!-- 5. Safe Vehicle on Roadway -->
<rect x="240" y="138" width="76" height="22" rx="6" fill="#f5b942" stroke="#ffffff" stroke-width="1.5"/>
<polygon points="252,138 262,127 294,127 304,138" fill="#38bdf8"/>
<circle cx="256" cy="161" r="7" fill="#0f172a" stroke="#ffffff" stroke-width="2"/>
<circle cx="300" cy="161" r="7" fill="#0f172a" stroke="#ffffff" stroke-width="2"/>
</g>
</svg>
</div>
"""

# ---------------------------------------------------------------------------
# 4. SESSION STATE & HELPER FUNCTIONS
# ---------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "mobility_profile" not in st.session_state:
    st.session_state.mobility_profile = "Wheelchair User"
if "audit_history" not in st.session_state:
    st.session_state.audit_history = []


def check_backend_health() -> bool:
    try:
        res = requests.get(f"{BACKEND_URL}/health", timeout=1.5)
        return res.status_code == 200
    except Exception:
        return False


def _convert_to_degrees(value) -> float:
    d = float(value[0])
    m = float(value[1])
    s = float(value[2])
    return d + (m / 60.0) + (s / 3600.0)


def extract_gps_from_image(pil_img: Image.Image) -> Optional[Dict[str, float]]:
    try:
        exif_data = pil_img._getexif()
        if not exif_data:
            return None
        gps_info = {}
        for tag_id, val in exif_data.items():
            tag_name = ExifTags.TAGS.get(tag_id, tag_id)
            if tag_name == "GPSInfo":
                for sub_id in val:
                    sub_name = ExifTags.GPSTAGS.get(sub_id, sub_id)
                    gps_info[sub_name] = val[sub_id]
        if "GPSLatitude" in gps_info and "GPSLongitude" in gps_info:
            lat = _convert_to_degrees(gps_info["GPSLatitude"])
            if gps_info.get("GPSLatitudeRef") != "N":
                lat = -lat
            lon = _convert_to_degrees(gps_info["GPSLongitude"])
            if gps_info.get("GPSLongitudeRef") != "E":
                lon = -lon
            return {"lat": round(lat, 6), "lon": round(lon, 6)}
    except Exception:
        pass
    return None


def submit_audit_to_backend(
    image_bytes: bytes,
    filename: str,
    lat: float,
    lon: float,
    notes: str,
) -> Optional[Dict]:
    try:
        files = {"file": (filename, image_bytes, "image/jpeg")}
        data = {
            "reporter_name": st.session_state.user_name or "Citizen Auditor",
            "mobility_profile": st.session_state.mobility_profile,
            "latitude": lat,
            "longitude": lon,
            "notes": notes,
        }
        resp = requests.post(f"{BACKEND_URL}/api/audits/upload", files=files, data=data, timeout=20)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        return None
    return None


# ---------------------------------------------------------------------------
# 5. RENDER HEADER & GRID-MESH YOLO VIGILANCE EYE HUD
# ---------------------------------------------------------------------------
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

backend_online = check_backend_health()
status_badge = (
    '<span class="status-pill-online">● FASTAPI + SQLITE BACKEND: ONLINE (PORT 8080)</span>'
    if backend_online
    else '<span class="status-pill-offline">● OFFLINE LOCAL VISION MODE (START PORT 8080 FOR DB)</span>'
)

st.markdown(
    f"""
<div class="freedom-hero">
<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
<div>
<h1 class="freedom-title"><span>FreeDom</span> To All</h1>
<div class="freedom-acronym">Free to Dominate: Detect | Object | Eliminate</div>
<div class="freedom-tagline">Your Path &nbsp;|&nbsp; Your Journey &nbsp;|&nbsp; Your Way &nbsp;—&nbsp; Crowd-Powered Footpath & Road Vigilance</div>
</div>
<div>{status_badge}</div>
</div>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(GRID_YOLO_EYE_HTML, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 6. SIDEBAR & SIGN-IN PORTAL WITH INCLUSIVE JOURNEY CELEBRATION
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 👁️ FreeDom Navigation")
    if st.session_state.authenticated:
        st.success(f"Signed in as **{st.session_state.user_name}**")
        st.caption(f"Profile: **{st.session_state.mobility_profile}**")
        if st.button("Sign Out", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()
    else:
        st.info("Sign in on the main screen to unlock Phone + PC Road & Footpath Auditing.")
    st.markdown("---")
    st.markdown("**Active Modules:**")
    st.markdown("- **Home:** YOLO Vigilance Capture")
    st.markdown("- **Page 1:** Smart Map & Routing")
    st.markdown("- **Page 2:** Civic & Citizen Hub")
    st.markdown("- **Page 3:** Voice Navigator")

if not st.session_state.authenticated:
    st.markdown("### 🚶‍♂️♿🦯🚗 Inclusive Vigilance Portal")
    col_scene, col_login = st.columns([1.35, 1], gap="large")

    with col_scene:
        st.markdown(INCLUSIVE_JOURNEY_HTML, unsafe_allow_html=True)
        st.caption(
            "Every citizen—whether on foot, in a wheelchair, navigating with a white cane, walking as an elder, or driving—deserves a barrier-free arrival."
        )

    with col_login:
        st.markdown('<div class="signin-card">', unsafe_allow_html=True)
        st.subheader("Enter FreeDom Auditor")
        with st.form("freedom_signin_form"):
            name_input = st.text_input("Your Name / Civic Handle", placeholder="e.g., Pallavi / RWA Sector-12")
            profile_input = st.selectbox(
                "Select Your Primary Mobility Profile",
                [
                    "Wheelchair User",
                    "Visually Impaired (Voice-First Mode)",
                    "Senior Citizen / Elder",
                    "Pedestrian / Stroller",
                    "Two-Wheeler / Cycle Rider",
                    "Four-Wheeler Driver",
                    "Civic Volunteer / RWA Member",
                ],
            )
            submitted = st.form_submit_button("Launch Vigilance Scanner →", use_container_width=True)
            if submitted:
                st.session_state.user_name = name_input.strip() or "Vigilant Citizen"
                st.session_state.mobility_profile = profile_input
                st.session_state.authenticated = True
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ---------------------------------------------------------------------------
# 7. AUTHENTICATED WORKSPACE: PHONE + PC CAPTURE & BOUNDING-BOX AUDIT
# ---------------------------------------------------------------------------
st.markdown("---")
st.subheader(f"📸 Live Footpath & Road Audit — Welcome, {st.session_state.user_name}")

tab_phone, tab_pc = st.tabs(["📱 Mobile Camera Capture", "💻 PC Drag-and-Drop Upload"])
captured_bytes = None
captured_name = "capture.jpg"

with tab_phone:
    cam_file = st.camera_input("Point your phone camera at any pothole, broken footpath, open drain, or encroachment")
    if cam_file is not None:
        captured_bytes = cam_file.getvalue()
        captured_name = f"mobile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"

with tab_pc:
    up_file = st.file_uploader("Upload a road or footpath photo from your computer", type=["jpg", "jpeg", "png", "webp"])
    if up_file is not None:
        captured_bytes = up_file.getvalue()
        captured_name = up_file.name

if captured_bytes is not None:
    pil_image = Image.open(io.BytesIO(captured_bytes))
    auto_gps = extract_gps_from_image(pil_image)

    default_lat = auto_gps["lat"] if auto_gps else 28.6139
    default_lon = auto_gps["lon"] if auto_gps else 77.2090

    if auto_gps:
        st.success(f"📍 Auto-extracted EXIF GPS Coordinates: **{default_lat}, {default_lon}**")
    else:
        st.info("📍 No embedded EXIF GPS found—confirm or adjust the coordinates below before running the YOLO scan.")

    c1, c2, c3 = st.columns([1, 1, 1.5])
    with c1:
        lat_val = st.number_input("Latitude", value=float(default_lat), format="%.6f")
    with c2:
        lon_val = st.number_input("Longitude", value=float(default_lon), format="%.6f")
    with c3:
        notes_val = st.text_input("Landmark / Street Note", placeholder="e.g., Near Gate 2 Metro Footpath")

    if st.button("🔍 Run YOLO Hazard Detection & Safety Audit", type="primary", use_container_width=True):
        with st.spinner("Scanning surface geometry, detecting cracks/potholes, and computing mobility safety..."):
            api_result = submit_audit_to_backend(captured_bytes, captured_name, lat_val, lon_val, notes_val)

            if api_result:
                st.success(f"✅ Saved to Spatial Database! Official Ticket ID: **{api_result['ticket_id']}**")
                col_img1, col_img2 = st.columns(2)
                with col_img1:
                    st.image(pil_image, caption="Original Captured Image", use_container_width=True)
                with col_img2:
                    ann_url = f"{BACKEND_URL}/api/audits/{api_result['ticket_id']}/image/annotated"
                    try:
                        ann_resp = requests.get(ann_url, timeout=5)
                        if ann_resp.status_code == 200:
                            st.image(ann_resp.content, caption="YOLO Bounding-Box Detection Output", use_container_width=True)
                        else:
                            st.image(pil_image, caption="Annotated Image", use_container_width=True)
                    except Exception:
                        st.image(pil_image, caption="Annotated Image", use_container_width=True)

                sev = api_result["severity_level"]
                if sev == "RED":
                    st.error(f"🚨 SEVERITY: **RED (CRITICAL HAZARD)** — {api_result['action_track']}")
                elif sev == "YELLOW":
                    st.warning(f"⚠️ SEVERITY: **YELLOW (MODERATE HAZARD)** — {api_result['action_track']}")
                else:
                    st.success(f"✅ SEVERITY: **GREEN (SAFE & PASSABLE)** — {api_result['action_track']}")

                st.markdown("### ♿ Mobility, Elder & Vehicle Safety Advisory")
                m1, m2 = st.columns(2)
                with m1:
                    st.markdown(f"**Wheelchair Safety:** {'✅ Safe' if api_result['wheelchair_safe'] else '❌ UNSAFE — Reroute Required'}")
                    st.markdown(f"**Elder & Blind Safety:** {'✅ Safe' if api_result['elder_safe'] else '❌ UNSAFE — High Trip/Fall Risk'}")
                    st.info(f"""**Reroute & Guidance:**
{api_result['reroute_suggestion']}""")
                with m2:
                    st.markdown(f"**Vehicle Compatibility:** {api_result['vehicle_advisory']}")
                    st.warning(f"""**Voice Alert (For Visually Impaired):**
"{api_result['voice_alert_text']}" """)

                if api_result.get("municipal_pdf_ready"):
                    try:
                        pdf_resp = requests.get(f"{BACKEND_URL}/api/audits/{api_result['ticket_id']}/pdf", timeout=5)
                        if pdf_resp.status_code == 200:
                            st.download_button(
                                label="📄 Download Official Municipal Grievance PDF",
                                data=pdf_resp.content,
                                file_name=f"{api_result['ticket_id']}_Municipal_Grievance.pdf",
                                mime="application/pdf",
                                use_container_width=True,
                            )
                    except Exception:
                        pass

            elif analyze_footpath_image is not None:
                local_report = analyze_footpath_image(captured_bytes, st.session_state.mobility_profile)
                col_img1, col_img2 = st.columns(2)
                with col_img1:
                    st.image(pil_image, caption="Original Captured Image", use_container_width=True)
                with col_img2:
                    st.image(local_report["annotated_image_bytes"], caption="YOLO Bounding-Box Detection Output", use_container_width=True)

                sev = local_report["severity_level"]
                if sev == "RED":
                    st.error(f"🚨 SEVERITY: **RED (CRITICAL HAZARD)** — {local_report['action_track']}")
                elif sev == "YELLOW":
                    st.warning(f"⚠️ SEVERITY: **YELLOW (MODERATE HAZARD)** — {local_report['action_track']}")
                else:
                    st.success(f"✅ SEVERITY: **GREEN (SAFE & PASSABLE)** — {local_report['action_track']}")

                st.info(f"""**Detailed Mobility & Reroute Suggestion:**
- **Wheelchair & Elder Verdict:** {local_report['wheelchair_advisory']}
- **Vehicle Safety:** {local_report['vehicle_advisory']}
- **Reroute Plan:** {local_report['reroute_suggestion']}""")
            else:
                st.error("Neither the FastAPI backend (port 8080) nor local vision_auditor.py could be reached.")
