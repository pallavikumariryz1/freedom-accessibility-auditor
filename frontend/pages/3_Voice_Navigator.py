import math
import os
import sys

import requests
import streamlit as st
from streamlit_js_eval import get_geolocation

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from services.nlp_translator import nlp_translate, render_language_selector
from services.voice_assistant import (
    build_spoken_safety_briefing,
    parse_voice_intent,
    text_to_speech_bytes,
    transcribe_audio_bytes,
)

BACKEND_URL = os.getenv("FREEDOM_BACKEND_URL", "http://127.0.0.1:8080")

st.set_page_config(
    page_title="Voice Navigator | FreeDom",
    page_icon="🎙️",
    layout="wide",
)

_, lang_code = render_language_selector()

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #0d0b26 0%, #1c1847 100%);
        color: #ffffff;
    }
    .voice-hero {
        background: rgba(255, 255, 255, 0.06);
        border: 2px solid #f5b942;
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.2rem;
    }
    .voice-hero h1 {
        color: #f5b942 !important;
        margin: 0 0 0.4rem 0 !important;
    }
    .stButton > button {
        width: 100%;
        min-height: 64px;
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        border-radius: 12px !important;
        border: 2px solid #f5b942 !important;
        background-color: #261c6e !important;
        color: #ffffff !important;
    }
    .stButton > button:hover {
        background-color: #f5b942 !important;
        color: #0d0b26 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

hero_title = nlp_translate("🎙️ FreeDom Voice-First Navigator (Blind & Low-Vision Assist)", lang_code)
hero_desc = nlp_translate(
    "Hands-free acoustic hazard guidance, wheelchair/elder barrier checks, and instant SOS alerts. "
    "Say commands like 'Check hazards near me', 'Wheelchair safe path', or 'Emergency help'.",
    lang_code,
)

st.markdown(
    f"""
    <div class="voice-hero">
        <h1>{hero_title}</h1>
        <p style="font-size:1.05rem; color:#e2e8f0; margin:0;">{hero_desc}</p>
    </div>
    """,
    unsafe_allow_html=True,
)


def fetch_audits():
    try:
        r = requests.get(f"{BACKEND_URL}/api/audits", timeout=5)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                return data
            return data.get("results") or data.get("audits") or data.get("items") or []
    except Exception as exc:
        st.warning(f"Backend unreachable at {BACKEND_URL}: {exc}")
    return []


traveler_lat, traveler_lon = 28.613900, 77.209000
with st.container(border=True):
    st.markdown(f"#### {nlp_translate('🧭 Your Live Walking Location (Traveler GPS)', lang_code)}")
    st.caption(
        nlp_translate(
            "Enable live GPS so Voice Navigator measures the exact distance and direction from "
            "where you are standing right now to any reported footpath hazards ahead.",
            lang_code,
        )
    )
    use_traveler_gps = st.toggle(
        nlp_translate("Use My Real-Time Walking Location", lang_code),
        value=True,
        key="voice_traveler_gps",
    )
    if use_traveler_gps:
        loc = get_geolocation(component_key="voice_nav_geo")
        if isinstance(loc, dict) and "coords" in loc:
            traveler_lat = float(loc["coords"]["latitude"])
            traveler_lon = float(loc["coords"]["longitude"])
            st.success(
                f"🛰️ {nlp_translate('Traveler Position Locked', lang_code)}: "
                f"{traveler_lat:.6f}, {traveler_lon:.6f}"
            )
        else:
            st.info(
                nlp_translate(
                    "📲 Tap Allow on your browser's location prompt to track your walking position...",
                    lang_code,
                )
            )


col_loc1, col_loc2, col_loc3 = st.columns(3)
with col_loc1:
    lat = st.number_input(nlp_translate("Current Latitude", lang_code), value=traveler_lat, format="%.6f")
with col_loc2:
    lon = st.number_input(nlp_translate("Current Longitude", lang_code), value=traveler_lon, format="%.6f")
with col_loc3:
    radius_km = st.slider(
        nlp_translate("Alert Scan Radius (km)", lang_code),
        min_value=0.5,
        max_value=5.0,
        value=1.5,
        step=0.5,
    )

st.subheader(nlp_translate("1. Quick-Touch Accessible Audio Triggers", lang_code))
b1, b2, b3 = st.columns(3)

spoken_output = ""
selected_mode = None

with b1:
    if st.button(nlp_translate("🔊 Speak Nearby Hazard Briefing", lang_code)):
        selected_mode = "BRIEFING"
with b2:
    if st.button(nlp_translate("♿ Wheelchair & Elder Safe Check", lang_code)):
        selected_mode = "ACCESSIBILITY_CHECK"
with b3:
    if st.button(nlp_translate("🆘 Broadcast SOS Location", lang_code)):
        selected_mode = "SOS"

st.subheader(nlp_translate("2. Speak or Type a Voice Command", lang_code))
mic_col, text_col = st.columns(2)

transcript = ""
with mic_col:
    audio_recording = st.audio_input(nlp_translate("Tap to Record Voice Command", lang_code))
    if audio_recording is not None:
        transcript = transcribe_audio_bytes(audio_recording.getvalue())
        if transcript:
            st.success(f"{nlp_translate('Heard Command', lang_code)}: **{transcript}**")
        else:
            st.warning(
                nlp_translate(
                    "Could not clearly transcribe audio. Try speaking closer to the mic or type below.",
                    lang_code,
                )
            )

with text_col:
    typed_cmd = st.text_input(
        nlp_translate("Or Enter Voice Command Text (Screen-Reader Compatible)", lang_code),
        placeholder=nlp_translate("e.g., Check hazards near me / Wheelchair safe route", lang_code),
    )
    if typed_cmd.strip():
        transcript = typed_cmd.strip()

if transcript and not selected_mode:
    parsed = parse_voice_intent(transcript)
    st.info(f"{nlp_translate('Detected Intent', lang_code)}: **{nlp_translate(parsed['label'], lang_code)}**")
    selected_mode = parsed["intent"]


def get_nearest_hazard_distance_and_dir(audits_list, user_lat: float, user_lon: float, max_km: float):
    nearest = None
    for a in audits_list:
        if a.get("ticket_status") == "RESOLVED":
            continue
        try:
            h_lat = float(a["latitude"])
            h_lon = float(a["longitude"])
            r = 6371000.0
            p1, p2 = math.radians(user_lat), math.radians(h_lat)
            dp, dl = math.radians(h_lat - user_lat), math.radians(h_lon - user_lon)
            x_val = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
            dist_m = int(round(2 * r * math.atan2(math.sqrt(x_val), math.sqrt(1 - x_val))))
            if dist_m <= max_km * 1000 and (nearest is None or dist_m < nearest[0]):
                y = math.sin(dl) * math.cos(p2)
                x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
                bearing = (math.degrees(math.atan2(y, x)) + 360) % 360
                dirs = ["North", "North-East", "East", "South-East", "South", "South-West", "West", "North-West"]
                compass = dirs[int((bearing + 22.5) // 45) % 8]
                nearest = (dist_m, compass, a.get("severity_level", "YELLOW"))
        except Exception:
            continue
    return nearest


if selected_mode:
    audits = fetch_audits()
    spoken_output = build_spoken_safety_briefing(
        audits=audits,
        lat=lat,
        lon=lon,
        radius_km=radius_km,
        mode=selected_mode,
    )
    nearest_info = get_nearest_hazard_distance_and_dir(audits, lat, lon, radius_km)
    if nearest_info:
        dist_m, compass, sev = nearest_info
        if dist_m <= 15:
            proximity_msg = (
                f"Immediate proximity alert! You are right next to a reported {sev} hazard "
                f"(within {dist_m} meters). "
            )
        else:
            proximity_msg = (
                f"Relative position update: Nearest reported {sev} hazard is {dist_m} meters {compass} "
                "from your current walking location. "
            )
        spoken_output = proximity_msg + spoken_output

    spoken_output = nlp_translate(spoken_output, lang_code)

    st.markdown(f"### {nlp_translate('🗣️ Spoken Guidance Readout', lang_code)}")
    st.success(spoken_output)

    mp3_bytes = text_to_speech_bytes(spoken_output, lang_code=lang_code)
    if mp3_bytes:
        st.audio(mp3_bytes, format="audio/mp3", autoplay=True)
    else:
        st.caption(
            nlp_translate(
                "Install gTTS (pip install gTTS) to enable automatic spoken MP3 playback.",
                lang_code,
            )
        )
