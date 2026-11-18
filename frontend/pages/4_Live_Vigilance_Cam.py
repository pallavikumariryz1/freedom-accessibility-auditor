import os
import sys
import tempfile
import time
from io import BytesIO
from pathlib import Path

import cv2
import numpy as np
import requests
import streamlit as st
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from services.vision_auditor import analyze_footpath_image
from services.voice_assistant import text_to_speech_bytes

BACKEND_URL = os.getenv("FREEDOM_BACKEND_URL", "http://127.0.0.1:8080")

st.set_page_config(
    page_title="Live Vigilance Cam | FreeDom",
    page_icon="📹",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #0d0b26 0%, #1c1847 100%);
        color: #ffffff;
    }
    .cam-banner {
        background: rgba(255, 255, 255, 0.06);
        border: 2px solid #f5b942;
        border-radius: 14px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1.2rem;
    }
    .cam-banner h1 {
        color: #f5b942 !important;
        margin: 0 0 0.3rem 0 !important;
        font-size: 1.8rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="cam-banner">
        <h1>📹 FreeDom Real-Time Vigilance Cam & Dashcam Auditor</h1>
        <p style="margin:0; color:#e2e8f0;">
            Continuous real-time YOLOv8 inference (<code>models/yolov8n.pt</code>) with live bounding-box telemetry,
            acoustic hazard warnings, and one-click civic ticket logging.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

col_cfg1, col_cfg2, col_cfg3, col_cfg4 = st.columns(4)
with col_cfg1:
    source_mode = st.selectbox("Video Input Source", ["Dashcam / Footpath Video File", "Live PC Webcam (Device 0)"])
with col_cfg2:
    conf_thresh = st.slider("YOLOv8 Confidence Threshold", 0.15, 0.85, 0.30, 0.05)
with col_cfg3:
    live_lat = st.number_input("Current GPS Latitude", value=28.6139, format="%.6f")
with col_cfg4:
    live_lon = st.number_input("Current GPS Longitude", value=77.2090, format="%.6f")

enable_voice = st.checkbox("🔊 Enable Automatic Spoken Audio Alerts on RED Hazards", value=True)


def push_frame_to_backend(pil_img: Image.Image, lat: float, lon: float) -> str:
    buf = BytesIO()
    pil_img.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/audits/upload",
            files={"file": ("live_vigilance_capture.jpg", buf.getvalue(), "image/jpeg")},
            data={
                "latitude": str(lat),
                "longitude": str(lon),
                "reporter_name": "FreeDom Live Vigilance Cam",
                "mobility_profile": "Live Patrol / Dashcam",
            },
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("ticket_id", "LOGGED")
    except Exception:
        pass
    return ""


if source_mode == "Dashcam / Footpath Video File":
    uploaded_vid = st.file_uploader("Upload Road or Footpath Walk-Through Video", type=["mp4", "avi", "mov", "mkv"])
    if uploaded_vid is not None:
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        tfile.write(uploaded_vid.read())
        tfile.flush()

        c_run, c_stop = st.columns([1, 4])
        start_vid = c_run.button("▶️ Start Real-Time YOLOv8 Video Scan", type="primary")

        if start_vid:
            cap = cv2.VideoCapture(tfile.name)
            frame_slot = st.empty()
            telemetry_slot = st.empty()
            audio_slot = st.empty()

            last_alert_time = 0.0
            frame_idx = 0
            best_red_frame = None

            while cap.isOpened():
                ret, frame_bgr = cap.read()
                if not ret:
                    break
                frame_idx += 1
                if frame_idx % 4 != 0:
                    continue

                rgb_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
                pil_frame = Image.fromarray(rgb_frame)
                result = analyze_footpath_image(pil_frame, confidence_threshold=conf_thresh)

                annotated_pil = result["annotated_image"]
                sev = result["severity_level"]
                engine = result.get("engine_used", "YOLOv8")
                dets = result.get("detections", [])

                frame_slot.image(
                    annotated_pil,
                    caption=f"Frame #{frame_idx} | Engine: {engine} | Status: {sev} | Detections: {len(dets)}",
                    use_container_width=True,
                )

                if sev == "RED":
                    best_red_frame = pil_frame
                    telemetry_slot.error(
                        f"🚨 CRITICAL HAZARD DETECTED ({len(dets)} objects) — {result['voice_alert_text']}"
                    )
                    if enable_voice and (time.time() - last_alert_time > 8.0):
                        mp3 = text_to_speech_bytes(result["voice_alert_text"])
                        if mp3:
                            audio_slot.audio(mp3, format="audio/mp3", autoplay=True)
                        last_alert_time = time.time()
                elif sev == "YELLOW":
                    telemetry_slot.warning(f"⚠️ CAUTION ({len(dets)} minor hazards) — {result['reroute_suggestion']}")
                else:
                    telemetry_slot.success("✅ CLEAR CORRIDOR — Barrier-free path verified.")

            cap.release()
            st.success("Video scan complete!")
            if best_red_frame is not None:
                ticket = push_frame_to_backend(best_red_frame, live_lat, live_lon)
                if ticket:
                    st.info(f"📌 Worst detected RED hazard automatically logged to SQLite & Civic Hub under **Ticket `{ticket}`**!")

else:
    st.info("Click **Start Live Webcam Stream** below to scan in real time using your PC or USB dashcam.")
    cam_col1, cam_col2 = st.columns(2)
    run_cam = cam_col1.checkbox("🟢 Active Live Webcam Feed", value=False)
    capture_now = cam_col2.button("📸 Capture & Log Current Hazard to Civic Hub")

    if run_cam:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            st.error("Could not access Webcam Device 0. Close any other camera app or use the Video File mode.")
        else:
            st_frame = st.empty()
            st_status = st.empty()
            st_audio = st.empty()
            last_spoken = 0.0

            while run_cam:
                ok, frame_bgr = cap.read()
                if not ok:
                    st.warning("Lost camera frame.")
                    break

                pil_cam = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
                res = analyze_footpath_image(pil_cam, confidence_threshold=conf_thresh)
                st_frame.image(res["annotated_image"], caption=f"Live HUD | {res['engine_used']}", use_container_width=True)

                if res["severity_level"] == "RED":
                    st_status.error(f"🚨 RED HAZARD: {res['voice_alert_text']}")
                    if enable_voice and (time.time() - last_spoken > 8.0):
                        mp3 = text_to_speech_bytes(res["voice_alert_text"])
                        if mp3:
                            st_audio.audio(mp3, format="audio/mp3", autoplay=True)
                        last_spoken = time.time()
                elif res["severity_level"] == "YELLOW":
                    st_status.warning(f"⚠️ YELLOW CAUTION: {res['reroute_suggestion']}")
                else:
                    st_status.success("✅ GREEN: Footpath Clear")

                if capture_now:
                    tid = push_frame_to_backend(pil_cam, live_lat, live_lon)
                    if tid:
                        st.toast(f"Logged Ticket {tid} to FastAPI & Civic Hub!")
                    capture_now = False

            cap.release()
