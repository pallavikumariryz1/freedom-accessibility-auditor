import os
import sys
import json
from datetime import datetime
from io import BytesIO
from pathlib import Path

import requests
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ExifTags
from streamlit_js_eval import get_geolocation

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

#from freedom_accessibility_auditor_v4.services.vision_auditor2 import analyze_footpath_image
from services.vision_auditor import analyze_footpath_image

API_BASE_URL = os.getenv("FREEDOM_API_URL", "http://127.0.0.1:8080")

st.set_page_config(
    page_title="FreeDom | Footpath & Road Accessibility Auditor",
    page_icon="👁️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# 1. GLOBAL STYLING & EXACT FREEDOM HEADER (MATCHING SCREENSHOT 1)
# ---------------------------------------------------------------------------
CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;800;900&family=Space+Grotesk:wght@400;600;700&display=swap');

.stApp {
    background: linear-gradient(135deg, #d7dce8 0%, #c6cfe6 50%, #d2d8e8 100%);
    color: #141136;
    font-family: 'Space Grotesk', sans-serif;
}

.freedom-hero {
    text-align: center;
    padding: 0.6rem 1rem 0.4rem 1rem;
    margin-bottom: 0.3rem;
}

.freedom-title {
    font-family: 'Orbitron', sans-serif !important;
    font-size: 5.8rem !important;
    font-weight: 900 !important;
    letter-spacing: 5px !important;
    line-height: 1.0 !important;
    text-transform: uppercase !important;
    margin: 0 auto 8px auto !important;
    display: inline-block !important;
    background: linear-gradient(
        90deg,
        #2b2273 0%,
        #322878 38%,
        #4a396c 62%,
        #63465a 82%,
        #7a504e 100%
    ) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    filter: none !important;
    text-shadow: none !important;
}



.freedom-sub-1 {
    font-family: 'Orbitron', sans-serif;
    font-weight: 800;
    font-size: clamp(0.85rem, 1.8vw, 1.15rem);
    letter-spacing: 0.14em;
    color: #1c1847;
    margin-top: 0.35rem;
    text-transform: uppercase;
}

.freedom-sub-2 {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: clamp(0.95rem, 1.6vw, 1.15rem);
    color: #1c1847;
    margin-top: 0.3rem;
}

.freedom-sub-2 span {
    color: #b87a08;
    font-weight: 700;
}



.journey-card {
    background: #ffffff;
    border: 2px solid #141136;
    border-radius: 16px;
    padding: 1.1rem 1.2rem;
    box-shadow: 0 8px 24px rgba(20, 17, 54, 0.08);
}

.journey-card-title {
    font-family: 'Orbitron', sans-serif;
    font-weight: 800;
    font-size: 1.05rem;
    letter-spacing: 0.08em;
    color: #141136;
    margin-bottom: 0.7rem;
    text-transform: uppercase;
}

.signin-card {
    background: rgba(255, 255, 255, 0.94);
    border: 2px solid #141136;
    border-radius: 16px;
    padding: 1.3rem 1.4rem;
    box-shadow: 0 8px 24px rgba(20, 17, 54, 0.08);
}

.status-pill-online {
    display: inline-block;
    background: #dcfce7;
    color: #166534;
    border: 1px solid #16a34a;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 700;
}

.status-pill-offline {
    display: inline-block;
    background: #fef3c7;
    color: #92400e;
    border: 1px solid #f59e0b;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 700;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# 2. MEDIUM-SIZED NEURAL-MESH EYE HUD (MATCHING SCREENSHOT 3 + NEURONS + GRID)
# ---------------------------------------------------------------------------
NEURAL_EYE_HUD_HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: transparent;
    display: flex;
    justify-content: center;
    align-items: center;
    font-family: 'Courier New', monospace;
    overflow: hidden;
  }
  .hud-shell {
    width: 100%;
    max-width: 620px;
    background: radial-gradient(circle at 50% 48%, #151936 0%, #0b0d1f 68%, #070814 100%);
    border: 1.5px solid rgba(245, 185, 66, 0.45);
    border-radius: 14px;
    box-shadow: 0 12px 30px rgba(10, 11, 30, 0.35), inset 0 0 32px rgba(245, 185, 66, 0.08);
    position: relative;
    overflow: hidden;
  }
  /* Sharp mathematical coordinate grid overlay */
  .grid-overlay {
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(to right, rgba(158, 197, 232, 0.13) 1px, transparent 1px),
      linear-gradient(to bottom, rgba(158, 197, 232, 0.13) 1px, transparent 1px),
      linear-gradient(to right, rgba(245, 185, 66, 0.22) 1px, transparent 1px),
      linear-gradient(to bottom, rgba(245, 185, 66, 0.22) 1px, transparent 1px);
    background-size: 22px 22px, 22px 22px, 110px 110px, 110px 110px;
    pointer-events: none;
  }
  /* Sweeping golden laser scan beam */
  .laser-beam {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 3px;
    background: linear-gradient(180deg, transparent 0%, rgba(245, 185, 66, 0.95) 50%, transparent 100%);
    box-shadow: 0 0 16px 4px rgba(245, 185, 66, 0.55);
    animation: scanSweep 4.2s ease-in-out infinite alternate;
    pointer-events: none;
    z-index: 5;
  }
  @keyframes scanSweep {
    0%   { left: 10%; }
    100% { left: 90%; }
  }
  @keyframes spinCW {
    0%   { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
  @keyframes spinCCW {
    0%   { transform: rotate(360deg); }
    100% { transform: rotate(0deg); }
  }
  @keyframes pupilVigilance {
    0%, 100% { transform: translate(0px, 0px); }
    25%      { transform: translate(-18px, -2px); }
    50%      { transform: translate(0px, 1px); }
    75%      { transform: translate(18px, -2px); }
  }
  @keyframes neuronPulse {
    0%, 100% { opacity: 0.45; r: 2.4; }
    50%      { opacity: 1; r: 3.9; }
  }
  .ring-cw  { transform-origin: 310px 155px; animation: spinCW 18s linear infinite; }
  .ring-ccw { transform-origin: 310px 155px; animation: spinCCW 12s linear infinite; }
  .iris-group { animation: pupilVigilance 5.5s ease-in-out infinite; }
  .neuron-node { animation: neuronPulse 2.4s ease-in-out infinite; }
  .n-delay-1 { animation-delay: 0.5s; }
  .n-delay-2 { animation-delay: 1.1s; }
  .n-delay-3 { animation-delay: 1.7s; }
</style>
</head>
<body>
<div class="hud-shell">
  <div class="grid-overlay"></div>
  <div class="laser-beam"></div>
  <svg viewBox="0 0 620 315" width="100%" height="auto" xmlns="http://www.w3.org/2000/svg">
    <defs>
      <!-- Luminous golden-brown-indigo iris gradient with extra shine -->
      <radialGradient id="luminousIris" cx="46%" cy="44%" r="54%">
        <stop offset="0%"   stop-color="#0d0b26"/>
        <stop offset="28%"  stop-color="#1a1647"/>
        <stop offset="52%"  stop-color="#8b5a2b"/>
        <stop offset="78%"  stop-color="#f5b942"/>
        <stop offset="93%"  stop-color="#ffe89e"/>
        <stop offset="100%" stop-color="#fff8dc"/>
      </radialGradient>
      <radialGradient id="eyeAura" cx="50%" cy="50%" r="50%">
        <stop offset="0%"   stop-color="rgba(245, 185, 66, 0.26)"/>
        <stop offset="65%"  stop-color="rgba(158, 197, 232, 0.08)"/>
        <stop offset="100%" stop-color="rgba(11, 13, 31, 0)"/>
      </radialGradient>
      <filter id="glowFilter" x="-30%" y="-30%" width="160%" height="160%">
        <feGaussianBlur stdDeviation="3" result="blur"/>
        <feMerge>
          <feMergeNode in="blur"/>
          <feMergeNode in="SourceGraphic"/>
        </feMerge>
      </filter>
    </defs>

    <!-- Soft luminous aura behind eye -->
    <ellipse cx="310" cy="155" rx="235" ry="95" fill="url(#eyeAura)"/>

    <!-- YOLO Bounding Box Header Tag & Corner Reticles -->
    <rect x="108" y="26" width="218" height="22" rx="4" fill="#f5b942"/>
    <text x="116" y="41" fill="#0d0b26" font-size="11.5" font-weight="bold" letter-spacing="0.8">
      YOLO_OPTIC_HUD :: 0.99 CONF
    </text>
    <text x="415" y="41" fill="#9ec5e8" font-size="10.5" font-weight="bold" letter-spacing="1">
      [NEURAL_SCAN: ON]
    </text>

    <!-- Corner Detection Brackets -->
    <path d="M 108 74 L 108 54 L 132 54" stroke="#f5b942" stroke-width="2.5" fill="none"/>
    <path d="M 512 74 L 512 54 L 488 54" stroke="#f5b942" stroke-width="2.5" fill="none"/>
    <path d="M 108 236 L 108 256 L 132 256" stroke="#f5b942" stroke-width="2.5" fill="none"/>
    <path d="M 512 236 L 512 256 L 488 256" stroke="#f5b942" stroke-width="2.5" fill="none"/>

    <!-- Fine coordinate crosshairs -->
    <line x1="65" y1="155" x2="555" y2="155" stroke="rgba(158, 197, 232, 0.25)" stroke-width="1" stroke-dasharray="4 4"/>
    <line x1="310" y1="55" x2="310" y2="255" stroke="rgba(158, 197, 232, 0.25)" stroke-width="1" stroke-dasharray="4 4"/>

    <!-- Outer & Inner Steel-Blue Almond Eye Contours -->
    <path d="M 92 155 Q 310 52 528 155 Q 310 258 92 155 Z"
          fill="rgba(13, 16, 40, 0.65)" stroke="#6fa3d2" stroke-width="1.6"/>
    <path d="M 116 155 Q 310 66 504 155 Q 310 244 116 155 Z"
          fill="none" stroke="#9ec5e8" stroke-width="2"/>

    <!-- NEURON DENDRITE FILAMENTS FORMING THE EYE STRUCTURE -->
    <g stroke="rgba(245, 185, 66, 0.55)" stroke-width="1.15" fill="none" filter="url(#glowFilter)">
      <!-- Upper neural mesh -->
      <polyline points="116,155 168,124 225,103 282,94 338,94 395,103 452,124 504,155"/>
      <polyline points="168,124 210,136 255,118 310,108 365,118 410,136 452,124"/>
      <line x1="225" y1="103" x2="210" y2="136"/>
      <line x1="282" y1="94"  x2="255" y2="118"/>
      <line x1="338" y1="94"  x2="365" y2="118"/>
      <line x1="395" y1="103" x2="410" y2="136"/>
      <!-- Lower neural mesh -->
      <polyline points="116,155 168,186 225,207 282,216 338,216 395,207 452,186 504,155"/>
      <polyline points="168,186 210,174 255,192 310,202 365,192 410,174 452,186"/>
      <line x1="225" y1="207" x2="210" y2="174"/>
      <line x1="282" y1="216" x2="255" y2="192"/>
      <line x1="338" y1="216" x2="365" y2="192"/>
      <line x1="395" y1="207" x2="410" y2="174"/>
      <!-- Synaptic connections linking eye corners to iris -->
      <line x1="168" y1="124" x2="168" y2="186"/>
      <line x1="210" y1="136" x2="210" y2="174"/>
      <line x1="410" y1="136" x2="410" y2="174"/>
      <line x1="452" y1="124" x2="452" y2="186"/>
    </g>

    <!-- FIRING NEURON SOMA NODES -->
    <g fill="#ffe082" filter="url(#glowFilter)">
      <circle class="neuron-node" cx="168" cy="124" r="3"/>
      <circle class="neuron-node n-delay-1" cx="225" cy="103" r="3"/>
      <circle class="neuron-node n-delay-2" cx="282" cy="94"  r="3"/>
      <circle class="neuron-node n-delay-3" cx="338" cy="94"  r="3"/>
      <circle class="neuron-node n-delay-1" cx="395" cy="103" r="3"/>
      <circle class="neuron-node n-delay-2" cx="452" cy="124" r="3"/>
      <circle class="neuron-node n-delay-3" cx="210" cy="136" r="2.6"/>
      <circle class="neuron-node" cx="410" cy="136" r="2.6"/>

      <circle class="neuron-node n-delay-2" cx="168" cy="186" r="3"/>
      <circle class="neuron-node n-delay-3" cx="225" cy="207" r="3"/>
      <circle class="neuron-node" cx="282" cy="216" r="3"/>
      <circle class="neuron-node n-delay-1" cx="338" cy="216" r="3"/>
      <circle class="neuron-node n-delay-2" cx="395" cy="207" r="3"/>
      <circle class="neuron-node n-delay-3" cx="452" cy="186" r="3"/>
      <circle class="neuron-node n-delay-1" cx="210" cy="174" r="2.6"/>
      <circle class="neuron-node" cx="410" cy="174" r="2.6"/>
    </g>

    <!-- Counter-Rotating Calibration Rings -->
    <circle class="ring-cw" cx="310" cy="155" r="76"
            fill="none" stroke="#f5b942" stroke-width="1.8" stroke-dasharray="10 7"/>
    <circle class="ring-ccw" cx="310" cy="155" r="61"
            fill="none" stroke="#9ec5e8" stroke-width="1.2" stroke-dasharray="4 6"/>

    <!-- Vigilant Scanning Iris & Luminous Specular Shine -->
    <g class="iris-group">
      <!-- Outer iris glow -->
      <circle cx="310" cy="155" r="46" fill="url(#luminousIris)" stroke="#ffe89e" stroke-width="2" filter="url(#glowFilter)"/>
      <!-- Neural radial striations inside iris -->
      <circle cx="310" cy="155" r="34" fill="none" stroke="rgba(255, 248, 220, 0.45)" stroke-width="1" stroke-dasharray="2 4"/>
      <!-- Dark Indigo Pupil Core -->
      <circle cx="310" cy="155" r="18" fill="#09081c" stroke="#f5b942" stroke-width="1.4"/>
      <!-- Crisp Specular Eye Shine Highlights -->
      <circle cx="301" cy="146" r="5.5" fill="#ffffff" opacity="0.96"/>
      <circle cx="319" cy="162" r="2.3" fill="#fff3c4" opacity="0.85"/>
    </g>

    <!-- Bottom Caption Bar -->
    <text x="310" y="286" text-anchor="middle" fill="#e2e8f0" font-size="13" font-weight="bold" letter-spacing="5.5">
      FOCUS · DETECT · INTERPRET
    </text>
  </svg>
</div>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# 3. EXACT INCLUSIVE JOURNEY SIMULATION CARD (MATCHING SCREENSHOT 4)
# ---------------------------------------------------------------------------
INCLUSIVE_JOURNEY_HTML = """
<!DOCTYPE html>
<html>
<head>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    background: transparent;
    font-family: 'Courier New', monospace;
    overflow: hidden;
  }
  .sim-wrapper {
    background: #f1f5fb;
    border-radius: 12px;
    padding: 14px;
    border: 1px solid #cbd5e1;
  }
  @keyframes moveAcross {
    0%   { transform: translateX(0px); }
    72%  { transform: translateX(225px); }
    88%  { transform: translateX(225px); }
    100% { transform: translateX(0px); }
  }
  @keyframes carAcross {
    0%   { transform: translateX(0px); }
    72%  { transform: translateX(255px); }
    88%  { transform: translateX(255px); }
    100% { transform: translateX(0px); }
  }
  @keyframes hurrahPop {
    0%, 62%  { opacity: 0; transform: scale(0.85); }
    72%, 88% { opacity: 1; transform: scale(1); }
    100%     { opacity: 0; transform: scale(0.85); }
  }
  .pedestrians-group { animation: moveAcross 7.5s ease-in-out infinite; }
  .car-group         { animation: carAcross 7.5s ease-in-out infinite; }
  .hurrah-badge      { transform-origin: 485px 115px; animation: hurrahPop 7.5s ease-in-out infinite; }
</style>
</head>
<body>
<div class="sim-wrapper">
  <svg viewBox="0 0 560 225" width="100%" height="auto" xmlns="http://www.w3.org/2000/svg">
    <!-- Upper Lane: Audited Tactile Footpath -->
    <rect x="10" y="14" width="540" height="82" rx="10" fill="#e8eef7" stroke="#b8c4d9" stroke-width="1.5"/>
    <text x="24" y="34" fill="#1e293b" font-size="11" font-weight="bold" letter-spacing="0.6">
      AUDITED TACTILE FOOTPATH (BARRIER-FREE)
    </text>
    <!-- Golden tactile paving dashes -->
    <line x1="24" y1="84" x2="435" y2="84" stroke="#f5b942" stroke-width="3" stroke-dasharray="10 8"/>

    <!-- Lower Lane: Verified Safe Roadway -->
    <rect x="10" y="112" width="540" height="86" rx="10" fill="#232838" stroke="#141136" stroke-width="1.5"/>
    <text x="24" y="133" fill="#f5b942" font-size="11" font-weight="bold" letter-spacing="0.6">
      VERIFIED SAFE ROADWAY
    </text>
    <!-- White lane dashes -->
    <line x1="24" y1="162" x2="435" y2="162" stroke="#ffffff" stroke-width="2.5" stroke-dasharray="14 12"/>

    <!-- Pedestrian Group on Tactile Footpath -->
    <g class="pedestrians-group">
      <!-- 1. Wheelchair User -->
      <g transform="translate(36, 44)">
        <circle cx="12" cy="8" r="5" fill="#141136"/>
        <path d="M 12 14 L 12 27 L 23 27 L 26 37" stroke="#141136" stroke-width="3" fill="none" stroke-linecap="round"/>
        <circle cx="11" cy="31" r="9" fill="none" stroke="#f5b942" stroke-width="3"/>
        <circle cx="24" cy="36" r="3" fill="#f5b942"/>
      </g>

      <!-- 2. Visually Impaired Traveler with White Cane -->
      <g transform="translate(92, 42)">
        <circle cx="10" cy="8" r="5" fill="#141136"/>
        <line x1="10" y1="14" x2="10" y2="29" stroke="#141136" stroke-width="3" stroke-linecap="round"/>
        <line x1="10" y1="29" x2="4"  y2="41" stroke="#141136" stroke-width="2.8" stroke-linecap="round"/>
        <line x1="10" y1="29" x2="16" y2="41" stroke="#141136" stroke-width="2.8" stroke-linecap="round"/>
        <line x1="10" y1="19" x2="28" y2="41" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round"/>
        <circle cx="28" cy="41" r="2.2" fill="#ef4444"/>
      </g>

      <!-- 3. Elder with Walking Stick -->
      <g transform="translate(146, 44)">
        <circle cx="11" cy="8" r="5" fill="#7a5347"/>
        <path d="M 11 14 Q 7 21 10 28" stroke="#7a5347" stroke-width="3" fill="none" stroke-linecap="round"/>
        <line x1="10" y1="28" x2="6"  y2="39" stroke="#7a5347" stroke-width="2.6" stroke-linecap="round"/>
        <line x1="10" y1="28" x2="14" y2="39" stroke="#7a5347" stroke-width="2.6" stroke-linecap="round"/>
        <line x1="17" y1="21" x2="17" y2="39" stroke="#141136" stroke-width="2.5" stroke-linecap="round"/>
      </g>

      <!-- 4. Standard Pedestrian -->
      <g transform="translate(194, 42)">
        <circle cx="10" cy="8" r="5" fill="#141136"/>
        <line x1="10" y1="14" x2="10" y2="29" stroke="#141136" stroke-width="3" stroke-linecap="round"/>
        <line x1="10" y1="29" x2="5"  y2="41" stroke="#141136" stroke-width="2.8" stroke-linecap="round"/>
        <line x1="10" y1="29" x2="15" y2="41" stroke="#141136" stroke-width="2.8" stroke-linecap="round"/>
      </g>
    </g>

    <!-- Golden Car on Verified Safe Roadway -->
    <g class="car-group" transform="translate(45, 134)">
      <path d="M 12 16 L 22 4 L 54 4 L 64 16 Z" fill="#9ec5e8" stroke="#141136" stroke-width="1.5"/>
      <rect x="4" y="15" width="68" height="19" rx="6" fill="#f5b942" stroke="#141136" stroke-width="1.5"/>
      <circle cx="19" cy="35" r="7" fill="#141136" stroke="#ffffff" stroke-width="2"/>
      <circle cx="57" cy="35" r="7" fill="#141136" stroke="#ffffff" stroke-width="2"/>
    </g>

    <!-- Green Safe Zone Destination Box (Matching Screenshot 4) -->
    <rect x="442" y="10" width="96" height="194" rx="12"
          fill="rgba(34, 197, 94, 0.22)" stroke="#16a34a" stroke-width="2.5"/>
    <text x="490" y="33" text-anchor="middle" fill="#15803d" font-size="11.5" font-weight="bold">
      SAFE ZONE
    </text>
    <text x="490" y="48" text-anchor="middle" fill="#15803d" font-size="10.5" font-weight="bold">
      DESTINATION
    </text>

    <!-- Celebratory Hurrah Badge upon Arrival -->
    <g class="hurrah-badge">
      <rect x="447" y="96" width="86" height="36" rx="8" fill="#16a34a" stroke="#ffffff" stroke-width="1.5"/>
      <text x="490" y="112" text-anchor="middle" fill="#ffffff" font-size="11" font-weight="bold">
        HURRAH!
      </text>
      <text x="490" y="125" text-anchor="middle" fill="#fef08a" font-size="8.5" font-weight="bold">
        SAFE FOR ALL
      </text>
    </g>
  </svg>
</div>
</body>
</html>
"""

# ---------------------------------------------------------------------------
# 4. SESSION STATE & HELPER FUNCTIONS
# ---------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_name" not in st.session_state:
    st.session_state.user_name = ""
if "mobility_profile" not in st.session_state:
    st.session_state.mobility_profile = "Pedestrian / Citizen Auditor"
if "last_report" not in st.session_state:
    st.session_state.last_report = None


def check_backend_health() -> bool:
    try:
        res = requests.get(f"{API_BASE_URL}/health", timeout=1.5)
        return res.status_code == 200
    except Exception:
        return False


def extract_gps_from_image(pil_img: Image.Image):
    try:
        exif = pil_img.getexif()
        if not exif:
            return None, None
        gps_info = {}
        for tag_id, val in exif.items():
            tag = ExifTags.TAGS.get(tag_id, tag_id)
            if tag == "GPSInfo":
                for t in val:
                    sub_tag = ExifTags.GPSTAGS.get(t, t)
                    gps_info[sub_tag] = val[t]
        if not gps_info:
            return None, None

        def _to_deg(value):
            d = float(value[0])
            m = float(value[1])
            s = float(value[2])
            return d + (m / 60.0) + (s / 3600.0)

        
        lat = _to_deg(gps_info["GPSLatitude"])
        if gps_info.get("GPSLatitudeRef") == "S":
            lat = -lat
        lon = _to_deg(gps_info["GPSLongitude"])
        if gps_info.get("GPSLongitudeRef") == "W":
            lon = -lon
        return round(lat, 6), round(lon, 6)
    except Exception:
        return None, None


# ---------------------------------------------------------------------------
# 5. HERO HEADER & NEURAL-MESH VIGILANCE EYE HUD
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div class="freedom-hero">
        <h1 class="freedom-title">FREEDOM</h1>
        <div class="freedom-sub-1">FREE TO DOMINATE: DETECT | OBJECT | ELIMINATE</div>
        <div class="freedom-sub-2">To All &bull; <span>Your Path | Your Journey | Your Way</span></div>
    </div>
    """,
    unsafe_allow_html=True,
)

components.html(NEURAL_EYE_HUD_HTML, height=330)

# ---------------------------------------------------------------------------
# 6. INCLUSIVE JOURNEY SIMULATION & SIGN-IN PORTAL
# ---------------------------------------------------------------------------
backend_online = check_backend_health()

if not st.session_state.authenticated:
    left_col, right_col = st.columns([1.25, 1], gap="large")

    with left_col:
        st.markdown(
            """
            <div class="journey-card">
                <div class="journey-card-title">INCLUSIVE JOURNEY SIMULATION :: SAFE ARRIVAL FOR ALL</div>
            """,
            unsafe_allow_html=True,
        )
        components.html(INCLUSIVE_JOURNEY_HTML, height=255)
        st.markdown("</div>", unsafe_allow_html=True)

    with right_col:
        status_badge = (
            '<span class="status-pill-online">FASTAPI + SQLITE :: ONLINE (PORT 8080)</span>'
            if backend_online
            else '<span class="status-pill-offline">LOCAL AI MODE :: START FASTAPI ON 8080</span>'
        )
        st.markdown(
            f"""
            <div class="signin-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                    <span style="font-family:'Orbitron',sans-serif; font-weight:800; font-size:1.05rem; color:#141136;">
                        ENTER VIGILANCE PORTAL
                    </span>
                    {status_badge}
                </div>
                <p style="font-size:0.9rem; color:#334155; margin-bottom:0.8rem;">
                    Sign in to audit footpaths & roads, check vehicle/wheelchair safety, and escalate hazards.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("freedom_signin_form"):
            name_input = st.text_input("Your Name / Citizen Handle", placeholder="e.g., Pallavi / RWA Sector-14")
            profile_input = st.selectbox(
                "Select Your Primary Journey Mode",
                [
                    "Pedestrian / Citizen Auditor",
                    "Wheelchair / Mobility Aid User",
                    "Elder Traveler",
                    "Visually Impaired (Voice-First Mode)",
                    "Two-Wheeler / Cycle Rider",
                    "Four-Wheeler Driver",
                ],
            )
            submitted = st.form_submit_button("Launch FreeDom Auditor", use_container_width=True)
            if submitted:
                st.session_state.authenticated = True
                st.session_state.user_name = name_input.strip() or "Vigilant Citizen"
                st.session_state.mobility_profile = profile_input
                st.rerun()

else:
    # -----------------------------------------------------------------------
    # 7. AUTHENTICATED PHONE + PC CAPTURE & AI HAZARD AUDIT WORKSPACE
    # -----------------------------------------------------------------------
    top_bar_1, top_bar_2 = st.columns([3, 1])
    with top_bar_1:
        st.markdown(
            f"### Welcome, **{st.session_state.user_name}** &nbsp;|&nbsp; Mode: `{st.session_state.mobility_profile}`"
        )
    with top_bar_2:
        if st.button("Sign Out / View Simulation", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

    st.info(
        "Use **Mobile Camera** or **PC File Upload** below to scan any footpath or road. "
        "Our Vision Auditor detects potholes, cracks, waterlogging, and blockages, generates bounding boxes, "
        "and routes severe issues to Municipalities or Citizen Quick-Fix teams."
    )

    tab_cam, tab_pc = st.tabs(["📱 Mobile Camera Capture", "💻 PC Drag-and-Drop Upload"])
    captured_bytes = None
    filename = "capture.jpg"

    with tab_cam:
        cam_file = st.camera_input("Point camera at footpath or road hazard")
        if cam_file is not None:
            captured_bytes = cam_file.getvalue()
            filename = cam_file.name or "mobile_audit.jpg"

    with tab_pc:
        up_file = st.file_uploader("Upload footpath or road photo (JPG, PNG, WEBP)", type=["jpg", "jpeg", "png", "webp"])
        if up_file is not None:
            captured_bytes = up_file.getvalue()
            filename = up_file.name

    if captured_bytes is not None:
        pil_image = Image.open(BytesIO(captured_bytes))
        auto_lat, auto_lon = extract_gps_from_image(pil_image)

        st.markdown("#### Confirm Location Coordinates & Run AI Audit")
        c1, c2, c3 = st.columns([1, 1, 1.4])
        with c1:
            lat = st.number_input("Latitude", value=auto_lat if auto_lat is not None else 28.613900, format="%.6f")
        with c2:
            lon = st.number_input("Longitude", value=auto_lon if auto_lon is not None else 77.209000, format="%.6f")
        with c3:
            notes = st.text_input("Landmark / Notes (Optional)", placeholder="Near Metro Gate 2, main market footpath")

        if st.button("🔍 Run YOLO Vigilance & Accessibility Audit", type="primary", use_container_width=True):
            with st.spinner("Scanning surface geometry, cracks, waterlogging, and accessibility clearance..."):
                if backend_online:
                    try:
                        files = {"file": (filename, captured_bytes, "image/jpeg")}
                        data = {
                            "reporter_name": st.session_state.user_name,
                            "mobility_profile": st.session_state.mobility_profile,
                            "latitude": str(lat),
                            "longitude": str(lon),
                            "notes": notes,
                        }
                        resp = requests.post(f"{API_BASE_URL}/api/audits/upload", files=files, data=data, timeout=20)
                        if resp.status_code == 200:
                            st.session_state.last_report = resp.json()
                        else:
                            st.error(f"Backend returned {resp.status_code}: {resp.text}")
                    except Exception as exc:
                        st.warning(f"Backend unreachable ({exc}); running local vision audit.")
                        st.session_state.last_report = analyze_footpath_image(pil_image)
                else:
                    st.session_state.last_report = analyze_footpath_image(pil_image)

    # Display Detailed AI Audit Results & Bounding Boxes
    report = st.session_state.last_report
    if report:
        st.divider()
        sev = report.get("severity_level", "YELLOW")
        ticket_id = report.get("ticket_id", "LOCAL-PREVIEW")

        if sev == "RED":
            st.error(f"🚨 **CRITICAL HAZARD DETECTED (RED)** — Ticket `{ticket_id}` | Score: `{report.get('severity_score', 0)}/100`")
        elif sev == "YELLOW":
            st.warning(f"⚠️ **MODERATE SURFACE ISSUE (YELLOW)** — Ticket `{ticket_id}` | Score: `{report.get('severity_score', 0)}/100`")
        else:
            st.success(f"✅ **BARRIER-FREE & SAFE (GREEN)** — Ticket `{ticket_id}` | Score: `{report.get('severity_score', 0)}/100`")

        img_col, detail_col = st.columns([1.1, 1], gap="large")
        with img_col:
            st.markdown("**AI Bounding-Box Detection Output**")
            if backend_online and ticket_id != "LOCAL-PREVIEW":
                st.image(f"{API_BASE_URL}/api/audits/{ticket_id}/image/annotated", use_container_width=True)
            elif "annotated_image" in report:
                st.image(report["annotated_image"], use_container_width=True)

        with detail_col:
            st.markdown("**Mobility & Vehicle Safety Advisories**")
            st.write(f"**♿ Wheelchair & Stroller:** {report.get('wheelchair_advisory', 'Check surface clearance.')}")
            st.write(f"**🦯 Elders & Visually Impaired:** {report.get('elder_advisory', 'Proceed with caution.')}")
            st.write(f"**🚗 Vehicle Compatibility:** {report.get('vehicle_advisory', 'Inspect lane width.')}")
            st.info(f"**🧭 Recommended Reroute:** {report.get('reroute_suggestion', 'Use adjacent smooth footpath.')}")
            st.success(f"**🏛️ Action Track:** {report.get('action_track', 'Citizen / Municipal Review')}")

            if backend_online and ticket_id != "LOCAL-PREVIEW" and sev == "RED":
                try:
                    pdf_res = requests.get(f"{API_BASE_URL}/api/audits/{ticket_id}/pdf", timeout=10)
                    if pdf_res.status_code == 200:
                        st.download_button(
                            label="📄 Download Official Municipal Grievance PDF",
                            data=pdf_res.content,
                            file_name=f"{ticket_id}_Municipal_Grievance.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                        )
                except Exception:
                    pass
