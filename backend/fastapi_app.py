import io
import math
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np
from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import Base, HazardAudit, engine, get_db
from services.civic_escalator import generate_municipal_grievance_pdf
from services.vision_auditor import analyze_footpath_image


# ---------------------------------------------------------------------------
# PATHS AND DATABASE INITIALIZATION
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
UPLOADS_DIR = PROJECT_ROOT / "data" / "uploads"
REPORTS_DIR = PROJECT_ROOT / "data" / "reports"

UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# FASTAPI APPLICATION
# ---------------------------------------------------------------------------

app = FastAPI(
    title="FreeDom Accessibility Auditor API",
    description=(
        "Spatial backend for footpath and road hazard detection, "
        "accessibility safety, and civic escalation."
    ),
    version="1.5.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# REQUEST SCHEMAS
# ---------------------------------------------------------------------------

class ClaimRequest(BaseModel):
    volunteer_name: Optional[str] = None
    claimed_by: Optional[str] = None
    group_name: Optional[str] = "Local Citizen Vigilance"


class ResolveRequest(BaseModel):
    resolved_by: Optional[str] = "Community / Civic Team"
    resolution_notes: Optional[str] = "Repaired and verified clear."


# ---------------------------------------------------------------------------
# GENERAL HELPERS
# ---------------------------------------------------------------------------

def haversine_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    earth_radius_km = 6371.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1)
        * math.cos(phi2)
        * math.sin(delta_lambda / 2) ** 2
    )
    a = min(1.0, max(0.0, a))

    return 2 * earth_radius_km * math.atan2(
        math.sqrt(a),
        math.sqrt(1.0 - a),
    )


def serialize_audit(row: HazardAudit) -> dict[str, Any]:
    created_at = getattr(row, "created_at", None)

    return {
        "id": getattr(row, "id", None),
        "ticket_id": getattr(row, "ticket_id", ""),
        "reporter_name": getattr(row, "reporter_name", "Citizen Auditor"),
        "mobility_profile": getattr(row, "mobility_profile", "Pedestrian"),
        "latitude": getattr(row, "latitude", 28.6139),
        "longitude": getattr(row, "longitude", 77.2090),
        "severity_level": getattr(row, "severity_level", "YELLOW"),
        "accessibility_score": getattr(row, "accessibility_score", 50.0),
        "detected_hazards": getattr(row, "detected_hazards", None) or [],
        "wheelchair_safe": getattr(row, "wheelchair_safe", False),
        "elder_safe": getattr(row, "elder_safe", False),
        "vehicle_advisory": getattr(row, "vehicle_advisory", ""),
        "reroute_suggestion": getattr(row, "reroute_suggestion", ""),
        "voice_alert_text": getattr(row, "voice_alert_text", ""),
        "action_track": getattr(row, "action_track", ""),
        "ticket_status": getattr(row, "ticket_status", "OPEN"),
        "claimed_by": getattr(row, "claimed_by", None),
        "created_at": str(created_at) if created_at is not None else datetime.now(timezone.utc).isoformat(),
    }


def get_audit_or_404(ticket_id: str, db: Session) -> HazardAudit:
    audit = (
        db.query(HazardAudit)
        .filter(HazardAudit.ticket_id == ticket_id)
        .first()
    )

    if audit is None:
        raise HTTPException(
            status_code=404,
            detail=f"Ticket {ticket_id} not found.",
        )

    return audit


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def save_annotated_image(annotated_obj: Any, fallback_pil: Image.Image, target_path: Path) -> None:
    if isinstance(annotated_obj, Image.Image):
        annotated_obj.convert("RGB").save(target_path, format="JPEG", quality=92)
        return
    if isinstance(annotated_obj, (bytes, bytearray)):
        Image.open(io.BytesIO(annotated_obj)).convert("RGB").save(target_path, format="JPEG", quality=92)
        return
    if isinstance(annotated_obj, np.ndarray):
        arr = annotated_obj
        if arr.ndim == 3 and arr.shape[2] == 3:
            arr = arr[:, :, ::-1]
        Image.fromarray(arr.astype("uint8")).convert("RGB").save(target_path, format="JPEG", quality=92)
        return
    fallback_pil.save(target_path, format="JPEG", quality=92)


# ---------------------------------------------------------------------------
# HEALTH & ROOT ENDPOINTS
# ---------------------------------------------------------------------------

@app.get("/")
def root() -> dict[str, str]:
    return {
        "app": "FreeDom Accessibility Auditor API",
        "status": "running",
        "version": "1.5.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health_check(db: Session = Depends(get_db)) -> dict[str, Any]:
    total = db.query(HazardAudit).count()
    return {
        "status": "ok",
        "database": "connected",
        "total_audits": total,
        "uploads_dir": str(UPLOADS_DIR),
    }


# ---------------------------------------------------------------------------
# AUDIT UPLOAD & SPATIAL QUERY ENDPOINTS
# ---------------------------------------------------------------------------

@app.post("/api/audits/upload")
async def upload_and_audit_image(
    file: UploadFile = File(...),
    latitude: float = Form(28.6139),
    longitude: float = Form(77.2090),
    reporter_name: str = Form("Citizen Auditor"),
    mobility_profile: str = Form("Pedestrian"),
    manual_severity_override: Optional[str] = Form(None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="Uploaded image file is empty.")

    ticket_id = f"FDM-{uuid.uuid4().hex[:8].upper()}"
    original_path = UPLOADS_DIR / f"{ticket_id}_original.jpg"
    annotated_path = UPLOADS_DIR / f"{ticket_id}_annotated.jpg"

    try:
        pil_orig = Image.open(io.BytesIO(raw_bytes)).convert("RGB")
        pil_orig.save(original_path, format="JPEG", quality=92)
    except UnidentifiedImageError as exc:
        raise HTTPException(status_code=400, detail=f"Unrecognized image format: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to read image: {exc}")

    vision_result = analyze_footpath_image(pil_orig)
    save_annotated_image(vision_result.get("annotated_image"), pil_orig, annotated_path)

    override_clean = (manual_severity_override or "").strip().upper()
    severity_level = (
        override_clean
        if override_clean in {"GREEN", "YELLOW", "RED"}
        else str(vision_result.get("severity_level", "YELLOW")).upper()
    )

    accessibility_score = safe_float(vision_result.get("accessibility_score"), 55.0) or 55.0
    detected_hazards = vision_result.get("detections") or vision_result.get("detected_hazards") or []
    wheelchair_advisory = str(
        vision_result.get("wheelchair_advisory", "Inspect path width and surface before proceeding.")
    )
    elder_advisory = str(
        vision_result.get("elder_advisory", "Watch for uneven surface transitions.")
    )
    vehicle_advisory = str(
        vision_result.get("vehicle_advisory", "Reduce speed and check lane clearance.")
    )
    reroute_suggestion = str(
        vision_result.get("reroute_suggestion", "Use adjacent audited footpath if available.")
    )
    voice_alert_text = str(
        vision_result.get(
            "voice_alert_text",
            f"Attention. {severity_level} level hazard detected ahead. {reroute_suggestion}",
        )
    )

    if severity_level == "RED":
        action_track = "Municipal Re-Construction Escalation"
    elif severity_level == "YELLOW":
        action_track = "Citizen / RWA Quick-Fix Vigilance"
    else:
        action_track = "Verified Clear — Routine Monitoring"

    pdf_path_str: Optional[str] = None
    if severity_level == "RED":
        pdf_path_str = generate_municipal_grievance_pdf(
            ticket_id=ticket_id,
            reporter_name=reporter_name,
            mobility_profile=mobility_profile,
            latitude=latitude,
            longitude=longitude,
            severity_level=severity_level,
            accessibility_score=accessibility_score,
            detected_hazards=detected_hazards,
            wheelchair_advisory=wheelchair_advisory,
            elder_advisory=elder_advisory,
            vehicle_advisory=vehicle_advisory,
            reroute_suggestion=reroute_suggestion,
            annotated_image_path=str(annotated_path),
            original_image_path=str(original_path),
            output_dir=str(REPORTS_DIR),
        )

    candidate_data = {
        "ticket_id": ticket_id,
        "reporter_name": reporter_name,
        "mobility_profile": mobility_profile,
        "latitude": latitude,
        "longitude": longitude,
        "severity_level": severity_level,
        "accessibility_score": accessibility_score,
        "detected_hazards": detected_hazards,
        "original_image_path": str(original_path),
        "annotated_image_path": str(annotated_path),
        "wheelchair_safe": bool(vision_result.get("wheelchair_safe", severity_level == "GREEN")),
        "elder_safe": bool(vision_result.get("elder_safe", severity_level != "RED")),
        "wheelchair_advisory": wheelchair_advisory,
        "elder_advisory": elder_advisory,
        "vehicle_advisory": vehicle_advisory,
        "reroute_suggestion": reroute_suggestion,
        "voice_alert_text": voice_alert_text,
        "action_track": action_track,
        "ticket_status": "OPEN",
        "municipal_pdf_path": pdf_path_str,
    }

    valid_cols = {c.name for c in HazardAudit.__table__.columns}
    filtered_data = {k: v for k, v in candidate_data.items() if k in valid_cols}

    audit_record = HazardAudit(**filtered_data)
    db.add(audit_record)
    db.commit()
    db.refresh(audit_record)

    return {
        "ticket_id": ticket_id,
        "severity_level": severity_level,
        "accessibility_score": accessibility_score,
        "detected_hazards": detected_hazards,
        "wheelchair_safe": candidate_data["wheelchair_safe"],
        "elder_safe": candidate_data["elder_safe"],
        "wheelchair_advisory": wheelchair_advisory,
        "elder_advisory": elder_advisory,
        "vehicle_advisory": vehicle_advisory,
        "reroute_suggestion": reroute_suggestion,
        "voice_alert_text": voice_alert_text,
        "action_track": action_track,
        "ticket_status": "OPEN",
        "municipal_pdf_generated": bool(pdf_path_str),
        "municipal_pdf_path": pdf_path_str,
    }


@app.get("/api/audits")
def list_audits(
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    radius_km: float = Query(5.0),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    rows = db.query(HazardAudit).order_by(HazardAudit.id.desc()).all()
    results = []

    for row in rows:
        item = serialize_audit(row)
        if severity and item["severity_level"] != severity.strip().upper():
            continue
        if status and item["ticket_status"] != status.strip().upper():
            continue
        if lat is not None and lon is not None:
            item_lat = safe_float(item.get("latitude"))
            item_lon = safe_float(item.get("longitude"))
            if item_lat is None or item_lon is None:
                continue
            dist = haversine_km(lat, lon, item_lat, item_lon)
            if dist > radius_km:
                continue
            item["distance_km"] = round(dist, 3)
        results.append(item)

    return {"count": len(results), "results": results, "audits": results}


@app.get("/api/audits/{ticket_id}")
def get_single_audit(ticket_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    audit = get_audit_or_404(ticket_id, db)
    return serialize_audit(audit)


# ---------------------------------------------------------------------------
# PDF REPORT, EVIDENCE IMAGE & CIVIC WORKFLOW ENDPOINTS
# ---------------------------------------------------------------------------

@app.get("/api/audits/{ticket_id}/pdf")
def download_municipal_pdf_get(ticket_id: str, db: Session = Depends(get_db)) -> FileResponse:
    audit = get_audit_or_404(ticket_id, db)

    pdf_path = getattr(audit, "municipal_pdf_path", None)
    if not pdf_path or not os.path.exists(pdf_path):
        pdf_path = generate_municipal_grievance_pdf(
            ticket_id=audit.ticket_id,
            reporter_name=getattr(audit, "reporter_name", "Citizen Auditor"),
            mobility_profile=getattr(audit, "mobility_profile", "Pedestrian"),
            latitude=safe_float(getattr(audit, "latitude", 28.6139), 28.6139) or 28.6139,
            longitude=safe_float(getattr(audit, "longitude", 77.2090), 77.2090) or 77.2090,
            severity_level=getattr(audit, "severity_level", "RED"),
            accessibility_score=safe_float(getattr(audit, "accessibility_score", 40.0), 40.0) or 40.0,
            detected_hazards=getattr(audit, "detected_hazards", None) or [],
            wheelchair_advisory="Unsafe for wheelchair passage; immediate detour required.",
            elder_advisory="High trip/slip risk for elders and visually impaired pedestrians.",
            vehicle_advisory=getattr(audit, "vehicle_advisory", "Proceed with caution."),
            reroute_suggestion=getattr(audit, "reroute_suggestion", "Use adjacent verified footpath."),
            annotated_image_path=getattr(audit, "annotated_image_path", None),
            original_image_path=getattr(audit, "original_image_path", None),
            output_dir=str(REPORTS_DIR),
        )
        if hasattr(audit, "municipal_pdf_path"):
            audit.municipal_pdf_path = pdf_path
            db.commit()

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"{ticket_id}_Municipal_Grievance.pdf",
    )


@app.post("/api/audits/{ticket_id}/generate-pdf")
def generate_and_download_pdf_post(ticket_id: str, db: Session = Depends(get_db)) -> FileResponse:
    return download_municipal_pdf_get(ticket_id=ticket_id, db=db)


@app.get("/api/audits/{ticket_id}/image/{kind}")
def get_audit_image(ticket_id: str, kind: str, db: Session = Depends(get_db)) -> FileResponse:
    audit = get_audit_or_404(ticket_id, db)

    if kind not in {"annotated", "original"}:
        raise HTTPException(status_code=400, detail="Image kind must be 'annotated' or 'original'.")

    path = (
        getattr(audit, "annotated_image_path", None)
        if kind == "annotated"
        else getattr(audit, "original_image_path", None)
    )
    if not path or not os.path.exists(path):
        path = str(UPLOADS_DIR / f"{ticket_id}_{kind}.jpg")

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Image file not found on server.")

    return FileResponse(path=path, media_type="image/jpeg")


@app.post("/api/audits/{ticket_id}/claim")
def claim_citizen_task(
    ticket_id: str,
    payload: ClaimRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    audit = get_audit_or_404(ticket_id, db)

    volunteer = payload.volunteer_name or payload.claimed_by or "Local Citizen Volunteer"
    if hasattr(audit, "claimed_by"):
        audit.claimed_by = volunteer
    if hasattr(audit, "ticket_status"):
        audit.ticket_status = "CLAIMED"
    db.commit()
    db.refresh(audit)

    return {"status": "claimed", "ticket_id": ticket_id, "claimed_by": volunteer}


@app.post("/api/audits/{ticket_id}/resolve")
def resolve_hazard_ticket(
    ticket_id: str,
    payload: ResolveRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    audit = get_audit_or_404(ticket_id, db)

    if hasattr(audit, "claimed_by") and not getattr(audit, "claimed_by", None):
        audit.claimed_by = payload.resolved_by
    if hasattr(audit, "ticket_status"):
        audit.ticket_status = "RESOLVED"
    db.commit()
    db.refresh(audit)

    return {"status": "resolved", "ticket_id": ticket_id, "resolved_by": payload.resolved_by}
