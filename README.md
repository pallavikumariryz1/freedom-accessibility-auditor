# 👁️ FreeDom — AI-Powered Footpath & Road Accessibility Auditor
**Free to Dominate: Detect | Object | Eliminate — To All**

FreeDom is a full-stack spatial AI platform designed to identify, evaluate, and escalate footpath and road hazards for **wheelchair users, elders, visually impaired pedestrians, and daily commuters**.

---

## 🚀 Key Features
* **Custom YOLOv8 + Monocular Depth Vision Engine:** Detects 6 hazard classes (`pothole`, `broken_footpath_tile`, `open_drain_manhole`, `waterlogging`, `footpath_encroachment`, `missing_curb_ramp`) and estimates crater depth in centimeters (`cm`) using interior-vs-rim luminance contrast.
* **Privacy-First Geolocation:** Supports live browser GPS tracking (`streamlit-js-eval`), automatic smartphone photo EXIF GPS extraction, and anonymous landmark reporting.
* **Smart Map & Barrier-Aware Detour Routing:** Visualizes audited danger zones on **OpenStreetMap** and calculates safe pedestrian/vehicle detours bypassing `RED` hazards.
* **Dual-Track Civic Escalation Hub:**
  * **Track A (`RED` Critical Hazards):** Auto-generates official **Municipal Grievance PDFs** (`ReportLab`) with GPS coordinates and bounding-box photographic proof.
  * **Track B (`YELLOW` Minor Hazards):** Mobilizes local RWAs and citizen volunteers to claim and verify quick-fix repairs.
* **Multilingual NLP & Voice Navigator:** Supports 13 languages (`English`, `Hindi`, `Bengali`, `Tamil`, `Telugu`, `Marathi`, etc.) with persistent disk caching (`data/translation_cache.json`), spoken `gTTS` audio briefings, and real-time Haversine distance + compass bearing alerts.

---

## 🛠️ Tech Stack
* **Frontend:** Streamlit (`frontend/streamlit_app_3.py` + Multi-Page UI)
* **AI & Computer Vision:** Ultralytics YOLOv8 (`models/yolov8n.pt`, 50 epochs), OpenCV, Pillow
* **Backend & Database:** FastAPI (`port 8080`), SQLAlchemy, SQLite (`freedom_auditor.db`)
* **Spatial & Civic Tools:** Folium, NetworkX, OSMnx, ReportLab, `deep-translator`, `gTTS`

---

## ⚙️ Quick Start (Local Setup)

1. **Clone the repository:**
   ```bash
   git clone https://github.com
   cd freedom-accessibility-auditor
   ```
2. **Install dependencies:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
3. **Launch both Backend & Frontend:**
   ```bash
   python run_freedom.py
   ```
   * **Frontend UI:** `http://localhost:8501`
   * **FastAPI Docs:** `http://127.0.0`
