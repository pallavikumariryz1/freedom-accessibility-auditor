import os
import sys
import requests
import streamlit as st

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

BACKEND_URL = os.getenv("FREEDOM_BACKEND_URL", "http://127.0.0.1:8080")

st.set_page_config(
    page_title="Civic & Citizen Hub | FreeDom",
    page_icon="🏛️",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #d7dce8 0%, #c6cfe6 100%);
    }
    .hub-banner {
        background: linear-gradient(135deg, #141136 0%, #261c6e 60%, #4a396c 100%);
        color: #ffffff;
        padding: 1.4rem 1.8rem;
        border-radius: 14px;
        border-left: 6px solid #f5b942;
        margin-bottom: 1.2rem;
    }
    .hub-banner h1 {
        color: #f5b942 !important;
        margin: 0 0 0.3rem 0 !important;
        font-size: 1.9rem !important;
    }
    .ticket-card {
        background: rgba(255, 255, 255, 0.94);
        border-radius: 12px;
        padding: 1.1rem 1.3rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 14px rgba(20, 17, 54, 0.08);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hub-banner">
        <h1>🏛️ Civic Escalation & Citizen Vigilance Hub</h1>
        <p style="margin:0; color:#e2e8f0;">
            <strong>FreeDom Dual-Track Action:</strong> Escalate severe structural failures to Municipalities (RED) or mobilize local RWAs, youth groups, and neighbors for rapid community fixes (YELLOW).
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
    except Exception as e:
        st.error(f"Cannot reach FastAPI backend at {BACKEND_URL}: {e}")
    return []




audits = fetch_audits()

red_open = [a for a in audits if a.get("severity_level") == "RED" and a.get("ticket_status") != "RESOLVED"]
yellow_open = [a for a in audits if a.get("severity_level") == "YELLOW" and a.get("ticket_status") != "RESOLVED"]
claimed_items = [a for a in audits if a.get("ticket_status") == "CLAIMED"]
resolved_items = [a for a in audits if a.get("ticket_status") == "RESOLVED"]

c1, c2, c3, c4 = st.columns(4)
c1.metric("🚨 Municipal Escalations (RED)", len(red_open))
c2.metric("🛠️ Citizen Quick-Fixes (YELLOW)", len(yellow_open))
c3.metric("🤝 Claimed by Volunteers", len(claimed_items))
c4.metric("✅ Verified Resolved", len(resolved_items))

tab_muni, tab_citizen, tab_resolved = st.tabs([
    "🚨 Municipal Reconstruction Queue (RED)",
    "🤝 Citizen & RWA Quick-Fix Board (YELLOW)",
    "✅ Resolved Community Archive",
])

with tab_muni:
    st.subheader("Severe Structural Hazards Requiring Municipal Intervention")
    if not red_open:
        st.info("No open RED municipal hazards right now. Upload a severe road/footpath hazard on the Home page to test escalation.")
    for item in red_open:
        tid = item.get("ticket_id", "UNKNOWN")
        with st.container(border=True):
            col_img, col_info = st.columns([1, 2])
            with col_img:
                img_url = f"{BACKEND_URL}/api/audits/{tid}/image/annotated"
                st.image(img_url, caption=f"YOLO Bounding-Box Evidence ({tid})", use_container_width=True)
            with col_info:
                st.markdown(f"### Ticket `{tid}` — Severity: **RED ({item.get('severity_score', 'N/A')})**")
                st.write(f"**Coordinates:** `{item.get('latitude')}, {item.get('longitude')}` | **Status:** `{item.get('ticket_status')}`")
                st.warning(f"**Wheelchair & Elder Impact:** {item.get('reroute_suggestion', 'Immediate detour advised.')}")
                st.write(f"**Vehicle Advisory:** {item.get('vehicle_advisory', 'Avoid lane.')}")

                b1, b2 = st.columns(2)
                with b1:
                    if st.button(f"📄 Generate / Fetch Municipal PDF ({tid})", key=f"pdf_{tid}"):
                        r = requests.post(f"{BACKEND_URL}/api/audits/{tid}/generate-pdf", timeout=8)
                        if r.status_code == 200:
                            st.download_button(
                                label=f"⬇️ Download {tid}_Municipal_Grievance.pdf",
                                data=r.content,
                                file_name=f"{tid}_Municipal_Grievance.pdf",
                                mime="application/pdf",
                                key=f"dl_{tid}",
                            )
                        else:
                            st.error("Failed to generate PDF.")
                with b2:
                    if st.button(f"✅ Mark Municipal Repair Completed ({tid})", key=f"res_muni_{tid}"):
                        r = requests.post(
                            f"{BACKEND_URL}/api/audits/{tid}/resolve",
                            json={"resolved_by": "Municipal Works Dept"},
                            timeout=5,
                        )
                        if r.status_code == 200:
                            st.success(f"Ticket {tid} marked RESOLVED!")
                            st.rerun()

with tab_citizen:
    st.subheader("Neighborhood & RWA Actionable Repairs (Minor Cracks, Loose Pavers, Debris)")
    volunteer_name = st.text_input("Your Name / RWA / Volunteer Group", value="Local Vigilance Citizen Group")
    if not yellow_open:
        st.info("No open YELLOW quick-fix tasks currently. Any minor footpath damage audited on the Home page appears here automatically.")
    for item in yellow_open:
        tid = item.get("ticket_id", "UNKNOWN")
        with st.container(border=True):
            col_img, col_info = st.columns([1, 2])
            with col_img:
                img_url = f"{BACKEND_URL}/api/audits/{tid}/image/annotated"
                st.image(img_url, caption=f"Detected Minor Hazard ({tid})", use_container_width=True)
            with col_info:
                st.markdown(f"### Ticket `{tid}` — Status: **{item.get('ticket_status', 'OPEN')}**")
                st.write(f"**Coordinates:** `{item.get('latitude')}, {item.get('longitude')}`")
                if item.get("claimed_by"):
                    st.info(f"🙋 Claimed by: **{item.get('claimed_by')}**")
                st.write(f"**Action Needed:** {item.get('reroute_suggestion', 'Clear debris / level surface tiles.')}")

                c_btn1, c_btn2 = st.columns(2)
                with c_btn1:
                    if st.button(f"🙋 Claim This Quick-Fix ({tid})", key=f"claim_{tid}"):
                        r = requests.post(
                            f"{BACKEND_URL}/api/audits/{tid}/claim",
                            json={"volunteer_name": volunteer_name},
                            timeout=5,
                        )
                        if r.status_code == 200:
                            st.success(f"Claimed by {volunteer_name}!")
                            st.rerun()
                with c_btn2:
                    if st.button(f"🎉 Mark Repair Resolved ({tid})", key=f"resolve_{tid}"):
                        r = requests.post(
                            f"{BACKEND_URL}/api/audits/{tid}/resolve",
                            json={"resolved_by": volunteer_name},
                            timeout=5,
                        )
                        if r.status_code == 200:
                            st.success(f"Hurrah! Ticket {tid} resolved by {volunteer_name}!")
                            st.rerun()

with tab_resolved:
    st.subheader("Verified Safe & Restored Pathways")
    if not resolved_items:
        st.write("No resolved tickets logged yet.")
    for item in resolved_items:
        st.success(
            f"✅ **{item.get('ticket_id')}** at (`{item.get('latitude')}, {item.get('longitude')}`) — "
            f"Restored by **{item.get('claimed_by') or 'Community / Civic Team'}**"
        )
