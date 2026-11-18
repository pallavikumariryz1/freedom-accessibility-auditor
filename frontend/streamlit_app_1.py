import io
import os
import sys
from pathlib import Path
from datetime import datetime
import requests
import streamlit as st
from PIL import Image, ExifTags

# Ensure project root is in sys.path so `services` imports work cleanly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from freedom_accessibility_auditor_v4.services.vision_auditor2 import analyze_footpath_image

API_BASE_URL = os.getenv("FREEDOM_API_URL", "http://127.0.0.1:8080")

st.set_page_config(
    page_title="FreeDom To All | Vigilance Accessibility Auditor",
    page_icon="👁️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# 1. CUSTOM CSS (Grey + Light Indigo Background, Mathematical HUD Theme)
# ---------------------------------------------------------
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@600;800;900&family=JetBrains+Mono:wght@400;600;700&family=Inter:wght@400;600;700&display=swap');

.stApp {
    background: linear-gradient(135deg, #d7dce8 0%, #c6cfe6 50%, #cfd6ea 100%);
    color: #141136;
    font-family: 'Inter', sans-serif;
}

.hero-banner {
    background: linear-gradient(135deg, #0b0922 0%, #171342 60%, #221c5c 100%);
    border: 2px solid #f5b942;
    border-radius: 16px;
    padding: 22px 28px;
    margin-bottom: 18px;
    box-shadow: 0 12px 32px rgba(13, 11, 38, 0.28);
    text-align: center;
}
.hero-title {
    font-family: 'Orbitron', sans-serif;
    font-size: 2.3rem;
    font-weight: 900;
    color: #ffffff;
    letter-spacing: 2px;
    margin: 0;
}
.hero-title span {
    color: #f5b942;
}
.hero-acronym {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.02rem;
    font-weight: 700;
    color: #f5b942;
    letter-spacing: 1.5px;
    margin-top: 6px;
}
.hero-sub {
    font-family: 'Orbitron', sans-serif;
    font-size: 0.92rem;
    color: #cbd5f5;
    letter-spacing: 2.5px;
    margin-top: 8px;
    text-transform: uppercase;
}

/* Mathematical Neural-Optic Vigilance Eye HUD */
.hud-stage {
    position: relative;
    background: radial-gradient(circle at 50% 50%, #141238 0%, #09081a 70%, #04030c 100%);
    border: 2px solid #f5b942;
    border-radius: 16px;
    padding: 14px;
    box-shadow: 0 14px 36px rgba(10, 9, 30, 0.45), inset 0 0 32px rgba(245, 185, 66, 0.14);
    overflow: hidden;
}

/* Precision Cartesian Coordinate Grid Overlay */
.math-grid-overlay {
    position: relative;
    width: 100%;
    border-radius: 10px;
    background-image:
        linear-gradient(to right, rgba(139, 90, 43, 0.22) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(139, 90, 43, 0.22) 1px, transparent 1px),
        linear-gradient(to right, rgba(245, 185, 66, 0.12) 1px, transparent 1px),
        linear-gradient(to bottom, rgba(245, 185, 66, 0.12) 1px, transparent 1px);
    background-size: 100px 100px, 100px 100px, 20px 20px, 20px 20px;
    overflow: hidden;
}

/* Radar Sweep Conic Beam */
.radar-sweep {
    position: absolute;
    top: 50%;
    left: 50%;
    width: 440px;
    height: 440px;
    margin-top: -220px;
    margin-left: -220px;
    border-radius: 50%;
    background: conic-gradient(
        from 0deg,
        rgba(245, 185, 66, 0.34) 0deg,
        rgba(245, 185, 66, 0.08) 42deg,
        transparent 80deg,
        transparent 360deg
    );
    animation: radarSpin 4.5s linear infinite;
    pointer-events: none;
}

/* Vertical & Horizontal Laser Telemetry Beams */
.scan-beam-y {
    position: absolute;
    left: 0;
    width: 100%;
    height: 2px;
    background: linear-gradient(90deg, transparent, #f5b942, #ffffff, #f5b942, transparent);
    box-shadow: 0 0 12px #f5b942, 0 0 22px #f5b942;
    animation: laserScanY 3.4s ease-in-out infinite;
    pointer-events: none;
}

@keyframes radarSpin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

@keyframes laserScanY {
    0%, 100% { top: 8%; opacity: 0.45; }
    50% { top: 92%; opacity: 1; }
}

@keyframes orbitCW {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

@keyframes orbitCCW {
    0% { transform: rotate(360deg); }
    100% { transform: rotate(0deg); }
}

@keyframes pupilVigilance {
    0%, 100% { transform: translate(0px, 0px) scale(1); }
    20% { transform: translate(-18px, -3px) scale(1.06); }
    45% { transform: translate(18px, 2px) scale(0.95); }
    70% { transform: translate(-10px, 4px) scale(1.08); }
    85% { transform: translate(12px, -3px) scale(1); }
}

@keyframes synapsePulse {
    0%, 100% { opacity: 0.35; r: 3; }
    50% { opacity: 1; r: 5; }
}

.ring-cw {
    transform-origin: 350px 185px;
    animation: orbitCW 16s linear infinite;
}
.ring-ccw {
    transform-origin: 350px 185px;
    animation: orbitCCW 11s linear infinite;
}
.vigilant-pupil {
    animation: pupilVigilance 5.5s ease-in-out infinite;
}
.synapse-node {
    animation: synapsePulse 2.2s ease-in-out infinite;
}

.hud-footer-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: rgba(10, 9, 28, 0.92);
    border-top: 1px solid rgba(245, 185, 66, 0.45);
    padding: 8px 14px;
    margin-top: 8px;
    border-radius: 8px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: #f5b942;
}

/* Sign-in Card */
.signin-card {
    background: rgba(255, 255, 255, 0.92);
    border: 2px solid #141136;
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 10px 28px rgba(20, 17, 54, 0.15);
}

/* Journey Celebration Animation */
@keyframes moveForward {
    0% { transform: translateX(0px); }
    50% { transform: translateX(26px); }
    100% { transform: translateX(0px); }
}
@keyframes hurrahPop {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.06); }
}
.traveler-group {
    animation: moveForward 4.2s ease-in-out infinite;
}
.hurrah-badge {
    transform-origin: 560px 44px;
    animation: hurrahPop 2s ease-in-out infinite;
}
</style>
"""

# ---------------------------------------------------------
# 2. MATHEMATICAL + NEURAL-OPTIC VIGILANCE EYE SVG (NO INDENTATION)
# ---------------------------------------------------------
MATH_NEURAL_EYE_SVG = """
<div class="hud-stage">
<div class="math-grid-overlay">
<div class="radar-sweep"></div>
<div class="scan-beam-y"></div>
<svg viewBox="0 0 700 370" width="100%" height="310" xmlns="http://www.w3.org/2000/svg">
<defs>
<radialGradient id="irisCoreGrad" cx="50%" cy="50%" r="50%">
<stop offset="0%" stop-color="#ffffff" stop-opacity="1"/>
<stop offset="22%" stop-color="#f5b942" stop-opacity="0.98"/>
<stop offset="56%" stop-color="#8b5a2b" stop-opacity="0.92"/>
<stop offset="85%" stop-color="#1d1854" stop-opacity="0.95"/>
<stop offset="100%" stop-color="#09081a" stop-opacity="1"/>
</radialGradient>
<radialGradient id="scleraGlow" cx="50%" cy="50%" r="50%">
<stop offset="0%" stop-color="#2a246e" stop-opacity="0.55"/>
<stop offset="70%" stop-color="#110e30" stop-opacity="0.88"/>
<stop offset="100%" stop-color="#070614" stop-opacity="0.98"/>
</radialGradient>
<clipPath id="eyeAlmondClip">
<path d="M 115 185 Q 350 42 585 185 Q 350 328 115 185 Z"/>
</clipPath>
</defs>

<!-- Mathematical Polar & Cartesian Axes -->
<line x1="20" y1="185" x2="680" y2="185" stroke="#f5b942" stroke-width="1" stroke-dasharray="6 4" opacity="0.55"/>
<line x1="350" y1="15" x2="350" y2="355" stroke="#f5b942" stroke-width="1" stroke-dasharray="6 4" opacity="0.55"/>
<line x1="160" y1="30" x2="540" y2="340" stroke="#8b5a2b" stroke-width="0.8" stroke-dasharray="3 5" opacity="0.45"/>
<line x1="540" y1="30" x2="160" y2="340" stroke="#8b5a2b" stroke-width="0.8" stroke-dasharray="3 5" opacity="0.45"/>

<!-- Mathematical Coordinate Labels -->
<text x="356" y="26" fill="#f5b942" font-family="JetBrains Mono, monospace" font-size="10" opacity="0.85">+Y [90°] ZENITH</text>
<text x="356" y="356" fill="#f5b942" font-family="JetBrains Mono, monospace" font-size="10" opacity="0.85">-Y [270°] NADIR</text>
<text x="24" y="179" fill="#cbd5f5" font-family="JetBrains Mono, monospace" font-size="10" opacity="0.8">-X [180°]</text>
<text x="615" y="179" fill="#cbd5f5" font-family="JetBrains Mono, monospace" font-size="10" opacity="0.8">+X [0°]</text>
<text x="24" y="28" fill="#f5b942" font-family="JetBrains Mono, monospace" font-size="11" font-weight="bold">YOLO_V8_OPTIC_MATRIX :: CONF 0.996</text>
<text x="495" y="28" fill="#86efac" font-family="JetBrains Mono, monospace" font-size="10">MODE: VIGILANCE_LOCK [ACTIVE]</text>

<!-- Polar Radar Range Circles -->
<circle cx="350" cy="185" r="158" fill="none" stroke="#8b5a2b" stroke-width="1" stroke-dasharray="2 6" opacity="0.65"/>
<circle cx="350" cy="185" r="126" fill="none" stroke="#f5b942" stroke-width="1.2" stroke-dasharray="14 6 2 6" opacity="0.75" class="ring-cw"/>
<circle cx="350" cy="185" r="98" fill="none" stroke="#ffffff" stroke-width="1" stroke-dasharray="8 8" opacity="0.55" class="ring-ccw"/>

<!-- Outer Almond Eye Contours (Dark Indigo + Golden + White) -->
<path d="M 95 185 Q 350 22 605 185 Q 350 348 95 185 Z" fill="none" stroke="#8b5a2b" stroke-width="1.5" opacity="0.7"/>
<path d="M 115 185 Q 350 42 585 185 Q 350 328 115 185 Z" fill="url(#scleraGlow)" stroke="#f5b942" stroke-width="2.5"/>
<path d="M 135 185 Q 350 62 565 185 Q 350 308 135 185 Z" fill="none" stroke="#ffffff" stroke-width="1" stroke-dasharray="4 4" opacity="0.6"/>

<!-- Neural Network Connections & Synapses Inside Eye -->
<g clip-path="url(#eyeAlmondClip)">
<line x1="170" y1="185" x2="255" y2="135" stroke="#f5b942" stroke-width="1" opacity="0.5"/>
<line x1="170" y1="185" x2="255" y2="235" stroke="#f5b942" stroke-width="1" opacity="0.5"/>
<line x1="255" y1="135" x2="350" y2="185" stroke="#ffffff" stroke-width="1" opacity="0.45"/>
<line x1="255" y1="235" x2="350" y2="185" stroke="#ffffff" stroke-width="1" opacity="0.45"/>
<line x1="530" y1="185" x2="445" y2="135" stroke="#f5b942" stroke-width="1" opacity="0.5"/>
<line x1="530" y1="185" x2="445" y2="235" stroke="#f5b942" stroke-width="1" opacity="0.5"/>
<line x1="445" y1="135" x2="350" y2="185" stroke="#ffffff" stroke-width="1" opacity="0.45"/>
<line x1="445" y1="235" x2="350" y2="185" stroke="#ffffff" stroke-width="1" opacity="0.45"/>

<circle cx="170" cy="185" r="4" fill="#f5b942" class="synapse-node"/>
<circle cx="255" cy="135" r="4" fill="#ffffff" class="synapse-node"/>
<circle cx="255" cy="235" r="4" fill="#f5b942" class="synapse-node"/>
<circle cx="530" cy="185" r="4" fill="#f5b942" class="synapse-node"/>
<circle cx="445" cy="135" r="4" fill="#ffffff" class="synapse-node"/>
<circle cx="445" cy="235" r="4" fill="#f5b942" class="synapse-node"/>

<!-- Moving Vigilant Iris & Pupil Assembly -->
<g class="vigilant-pupil">
<circle cx="350" cy="185" r="76" fill="url(#irisCoreGrad)" stroke="#f5b942" stroke-width="2.5"/>
<circle cx="350" cy="185" r="56" fill="none" stroke="#8b5a2b" stroke-width="2" stroke-dasharray="6 3"/>
<circle cx="350" cy="185" r="40" fill="none" stroke="#ffffff" stroke-width="1.2" stroke-dasharray="2 4"/>
<circle cx="350" cy="185" r="24" fill="#09081a" stroke="#f5b942" stroke-width="2"/>
<circle cx="350" cy="185" r="9" fill="#f5b942"/>
<circle cx="342" cy="176" r="5" fill="#ffffff" opacity="0.95"/>
<line x1="315" y1="185" x2="385" y2="185" stroke="#ffffff" stroke-width="1" opacity="0.7"/>
<line x1="350" y1="150" x2="350" y2="220" stroke="#ffffff" stroke-width="1" opacity="0.7"/>
</g>
</g>

<!-- YOLO Corner Bounding-Box Reticle Brackets -->
<path d="M 90 85 L 90 55 L 125 55" fill="none" stroke="#f5b942" stroke-width="3"/>
<path d="M 610 85 L 610 55 L 575 55" fill="none" stroke="#f5b942" stroke-width="3"/>
<path d="M 90 285 L 90 315 L 125 315" fill="none" stroke="#f5b942" stroke-width="3"/>
<path d="M 610 285 L 610 315 L 575 315" fill="none" stroke="#f5b942" stroke-width="3"/>
<rect x="90" y="55" width="520" height="260" fill="none" stroke="#f5b942" stroke-width="1" stroke-dasharray="8 6" opacity="0.5"/>
</svg>
</div>
<div class="hud-footer-bar">
<span>VECTOR: Δx=0.004 Δy=-0.002 | GRID: 20px/100px</span>
<span>FOCUS · DETECT · OBJECT · ELIMINATE</span>
<span>GUARDIAN NEURAL VISION</span>
</div>
</div>
"""

# ---------------------------------------------------------
# 3. INCLUSIVE JOURNEY DESTINATION ANIMATION SVG (NO INDENTATION)
# ---------------------------------------------------------
INCLUSIVE_JOURNEY_SVG = """
<div style="background:#0f0d2e; border:2px solid #f5b942; border-radius:14px; padding:12px; margin-top:12px;">
<svg viewBox="0 0 680 185" width="100%" height="165" xmlns="http://www.w3.org/2000/svg">
<rect x="0" y="0" width="680" height="185" rx="10" fill="#121038"/>
<!-- Footpath Lane (Top) -->
<rect x="14" y="24" width="520" height="68" rx="8" fill="#1e1b54" stroke="#9ec5e8" stroke-width="1.5"/>
<text x="24" y="40" fill="#cbd5f5" font-family="JetBrains Mono, monospace" font-size="10">AUDITED TACTILE FOOTPATH :: BARRIER-FREE</text>
<!-- Roadway Lane (Bottom) -->
<rect x="14" y="102" width="520" height="68" rx="8" fill="#181642" stroke="#f5b942" stroke-width="1.5"/>
<line x1="24" y1="136" x2="520" y2="136" stroke="#f5b942" stroke-width="2" stroke-dasharray="14 10"/>
<text x="24" y="118" fill="#f5b942" font-family="JetBrains Mono, monospace" font-size="10">VERIFIED SAFE ROADWAY :: HAZARD-FREE</text>

<!-- Safe Destination Archway -->
<rect x="546" y="20" width="120" height="150" rx="12" fill="#133b2e" stroke="#4ade80" stroke-width="2.5"/>
<text x="606" y="78" text-anchor="middle" fill="#4ade80" font-family="Orbitron, sans-serif" font-size="12" font-weight="bold">SAFE</text>
<text x="606" y="96" text-anchor="middle" fill="#ffffff" font-family="Orbitron, sans-serif" font-size="11" font-weight="bold">ZONE</text>
<g class="hurrah-badge">
<rect x="552" y="108" width="108" height="44" rx="8" fill="#f5b942"/>
<text x="606" y="126" text-anchor="middle" fill="#141136" font-family="Orbitron, sans-serif" font-size="10" font-weight="900">HURRAH!</text>
<text x="606" y="141" text-anchor="middle" fill="#141136" font-family="Inter, sans-serif" font-size="8.5" font-weight="700">ARRIVED SAFELY</text>
</g>

<!-- Moving Inclusive Travelers -->
<g class="traveler-group">
<!-- 1. Wheelchair User -->
<circle cx="72" cy="54" r="6" fill="#f5b942"/>
<path d="M 72 60 L 72 72 L 84 72" stroke="#ffffff" stroke-width="3" fill="none"/>
<circle cx="72" cy="76" r="9" fill="none" stroke="#4ade80" stroke-width="2.5"/>
<circle cx="85" cy="81" r="4" fill="#4ade80"/>

<!-- 2. Visually Impaired Traveler with White Cane -->
<circle cx="175" cy="52" r="6" fill="#ffffff"/>
<line x1="175" y1="58" x2="175" y2="75" stroke="#9ec5e8" stroke-width="3"/>
<line x1="175" y1="75" x2="169" y2="86" stroke="#9ec5e8" stroke-width="2.5"/>
<line x1="175" y1="75" x2="181" y2="86" stroke="#9ec5e8" stroke-width="2.5"/>
<line x1="178" y1="64" x2="202" y2="86" stroke="#ffffff" stroke-width="2.5"/>
<circle cx="202" cy="86" r="2.5" fill="#f5b942"/>

<!-- 3. Elder with Walking Stick -->
<circle cx="285" cy="54" r="6" fill="#cbd5f5"/>
<path d="M 285 60 Q 289 68 285 76" stroke="#f5b942" stroke-width="3" fill="none"/>
<line x1="285" y1="76" x2="280" y2="86" stroke="#f5b942" stroke-width="2.5"/>
<line x1="285" y1="76" x2="290" y2="86" stroke="#f5b942" stroke-width="2.5"/>
<line x1="292" y1="65" x2="296" y2="86" stroke="#8b5a2b" stroke-width="2.5"/>

<!-- 4. Pedestrian -->
<circle cx="395" cy="52" r="6" fill="#4ade80"/>
<line x1="395" y1="58" x2="395" y2="75" stroke="#ffffff" stroke-width="3"/>
<line x1="395" y1="75" x2="389" y2="86" stroke="#ffffff" stroke-width="2.5"/>
<line x1="395" y1="75" x2="402" y2="86" stroke="#ffffff" stroke-width="2.5"/>

<!-- 5. Safe Car on Roadway -->
<rect x="210" y="132" width="84" height="22" rx="6" fill="#f5b942"/>
<path d="M 224 132 L 236 119 L 270 119 L 282 132 Z" fill="#ffffff"/>
<circle cx="228" cy="155" r="7" fill="#09081a" stroke="#ffffff" stroke-width="2"/>
<circle cx="276" cy="155" r="7" fill="#09081a" stroke="#ffffff" stroke-width="2"/>
</g>
</svg>
</div>
"""

# ---------------------------------------------------------
# 4. SESSION STATE & HELPERS
# ---------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_name" not in st.session_state:
    st.session_state.user_name = "Citizen Guardian"
if "mobility_profile" not in st.session_state:
    st.session_state.mobility_profile = "Wheelchair / Assisted Mobility"
if "audit_history" not in st.session_state:
    st.session_state.audit_history = []


def check_backend_health() -> bool:
    try:
        res = requests.get(f"{API_BASE_URL}/health", timeout=2)
        return res.status_code == 200
    except Exception:
        return False


def extract_gps_info(pil_img: Image.Image):
    try:
        exif_raw = pil_img._getexif()
        if not exif_raw:
            return None, None
        gps_info = {}
        for tag, val in exif_raw.items():
            decoded = ExifTags.TAGS.get(tag, tag)
            if decoded == "GPSInfo":
                for t in val:
                    sub_decoded = ExifTags.GPSTAGS.get(t, t)
                    gps_info[sub_decoded] = val[t]
        if not gps_info:
            return None, None

        def _to_deg(value):
            d, m, s = value
            return float(d) + float(m) / 60.0 + float(s) / 3600.0

        lat = _to_deg(gps_info["GPSLatitude"])
        if gps_info.get("GPSLatitudeRef", "N") != "N":
            lat = -lat
        lon = _to_deg(gps_info["GPSLongitude"])
        if gps_info.get("GPSLongitudeRef", "E") != "E":
            lon = -lon
        return round(lat, 6), round(lon, 6)
    except Exception:
        return None, None


# ---------------------------------------------------------
# 5. RENDER HERO HEADER & MATHEMATICAL NEURAL-OPTIC EYE
# ---------------------------------------------------------
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown(
    """
    <div class="hero-banner">
        <div class="hero-title"><span>FreeDom</span> To All</div>
        <div class="hero-acronym">FREE TO DOMINATE: DETECT | OBJECT | ELIMINATE</div>
        <div class="hero-sub">Your Path &nbsp;|&nbsp; Your Journey &nbsp;|&nbsp; Your Way</div>
    </div>
    """,
    unsafe_allow_html=True,
)

backend_online = check_backend_health()
with st.sidebar:
    st.markdown("### 🛡️ FreeDom Vigilance Status")
    if backend_online:
        st.success(f"FastAPI + SQLite: ONLINE ({API_BASE_URL})")
    else:
        st.warning("FastAPI Backend: OFFLINE (Local AI Mode)")
    st.info("Use the sidebar pages to open **Smart Map & Routing**.")

st.markdown(MATH_NEURAL_EYE_SVG, unsafe_allow_html=True)

# ---------------------------------------------------------
# 6. SIGN-IN GATEWAY + INCLUSIVE JOURNEY CELEBRATION
# ---------------------------------------------------------
if not st.session_state.authenticated:
    st.markdown("### 🔐 Enter the Vigilance Network")
    col_journey, col_login = st.columns([1.35, 1])

    with col_journey:
        st.markdown(INCLUSIVE_JOURNEY_SVG, unsafe_allow_html=True)
        st.caption(
            "Every audit protects wheelchair users, visually impaired citizens, elders, pedestrians, and drivers."
        )

    with col_login:
        st.markdown('<div class="signin-card">', unsafe_allow_html=True)
        name_input = st.text_input("Your Name / Guardian Handle", value="Pallavi")
        profile_input = st.selectbox(
            "Select Your Primary Mobility Profile",
            [
                "Wheelchair / Assisted Mobility",
                "Visually Impaired (Voice-First Mode)",
                "Elder Pedestrian",
                "Two-Wheeler / Cycle Rider",
                "Four-Wheeler Driver",
                "Civic Volunteer / RWA Member",
            ],
        )
        if st.button("🚀 Claim Your Path & Start Auditing", use_container_width=True, type="primary"):
            st.session_state.authenticated = True
            st.session_state.user_name = name_input.strip() or "Citizen Guardian"
            st.session_state.mobility_profile = profile_input
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ---------------------------------------------------------
# 7. AUTHENTICATED PHONE + PC FOOTPATH & ROAD AUDITOR
# ---------------------------------------------------------
top_c1, top_c2 = st.columns([3, 1])
with top_c1:
    st.success(
        f"Welcome, **{st.session_state.user_name}** | Active Mode: **{st.session_state.mobility_profile}**"
    )
with top_c2:
    if st.button("Switch Profile / Sign Out", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

st.markdown("### 📸 Capture or Upload Footpath / Road Evidence (Phone + PC)")
tab_cam, tab_pc = st.tabs(["📱 Mobile Camera Capture", "💻 PC Drag-and-Drop Upload"])

uploaded_bytes = None
file_name = "capture.jpg"

with tab_cam:
    cam_file = st.camera_input("Point camera at footpath hazard, pothole, or obstruction")
    if cam_file is not None:
        uploaded_bytes = cam_file.getvalue()
        file_name = cam_file.name or "mobile_capture.jpg"

with tab_pc:
    pc_file = st.file_uploader(
        "Upload road or footpath image (JPG, PNG, WEBP)",
        type=["jpg", "jpeg", "png", "webp"],
    )
    if pc_file is not None:
        uploaded_bytes = pc_file.getvalue()
        file_name = pc_file.name

if uploaded_bytes:
    pil_image = Image.open(io.BytesIO(uploaded_bytes)).convert("RGB")
    exif_lat, exif_lon = extract_gps_info(pil_image)

    c_geo1, c_geo2, c_geo3 = st.columns([1, 1, 1.4])
    with c_geo1:
        lat = st.number_input("Latitude", value=exif_lat if exif_lat else 28.613900, format="%.6f")
    with c_geo2:
        lon = st.number_input("Longitude", value=exif_lon if exif_lon else 77.209000, format="%.6f")
    with c_geo3:
        landmark = st.text_input("Street / Landmark Note", value="Main Market Footpath Sector 4")

    if st.button("👁️ Run FreeDom Neural Audit & Save Ticket", type="primary", use_container_width=True):
        with st.spinner("Scanning surface geometry, cracks, waterlogging, and mobility clearance..."):
            report = analyze_footpath_image(pil_image)
            ticket_id = f"FDM-{datetime.now().strftime('%H%M%S')}"
            pdf_bytes = None

            if backend_online:
                try:
                    files = {"file": (file_name, uploaded_bytes, "image/jpeg")}
                    data = {
                        "latitude": lat,
                        "longitude": lon,
                        "reporter_name": st.session_state.user_name,
                        "mobility_profile": st.session_state.mobility_profile,
                        "landmark_note": landmark,
                    }
                    resp = requests.post(f"{API_BASE_URL}/api/audits/upload", files=files, data=data, timeout=15)
                    if resp.status_code == 200:
                        api_res = resp.json()
                        ticket_id = api_res.get("ticket_id", ticket_id)
                        if api_res.get("municipal_pdf_ready"):
                            pdf_resp = requests.get(f"{API_BASE_URL}/api/audits/{ticket_id}/pdf", timeout=10)
                            if pdf_resp.status_code == 200:
                                pdf_bytes = pdf_resp.content
                except Exception as exc:
                    st.warning(f"Saved locally (Backend sync notice: {exc})")

            st.divider()
            st.markdown(f"#### 🎯 Audit Verdict — Ticket `{ticket_id}` | Severity: **{report['severity_level']}**")

            img_col1, img_col2 = st.columns(2)
            with img_col1:
                st.image(pil_image, caption="Original Evidence", use_container_width=True)
            with img_col2:
                st.image(report["annotated_image"], caption="YOLO Vigilance Bounding-Box Detection", use_container_width=True)

            m1, m2, m3 = st.columns(3)
            m1.metric("Wheelchair Safety", "SAFE" if report["wheelchair_safe"] else "UNSAFE")
            m2.metric("Elder & Blind Safety", "SAFE" if report["elder_safe"] else "CAUTION / UNSAFE")
            m3.metric("Hazards Detected", len(report["detections"]))

            st.error(f"**Wheelchair & Stroller Advisory:** {report['wheelchair_advisory']}")
            st.warning(f"**Elders & Visually Impaired Advisory:** {report['elder_advisory']}")
            st.info(
                f"""**Civic Action & Reroute Plan ({report['action_track']}):**
{report['reroute_suggestion']}"""
            )

            with st.expander("🚗 Vehicle Compatibility Breakdown (2W / 3W / 4W)"):
                st.write(report["vehicle_advisory"])

            if pdf_bytes:
                st.download_button(
                    label="📄 Download Official Municipal Grievance PDF",
                    data=pdf_bytes,
                    file_name=f"{ticket_id}_Municipal_Grievance.pdf",
                    mime="application/pdf",
                    type="primary",
                )
