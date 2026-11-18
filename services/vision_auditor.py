import io
import os
from typing import Any, Dict, List, Union
import cv2
import numpy as np
from PIL import Image

def estimate_hazard_depth_cm(img_bgr: np.ndarray, bbox: List[int], raw_class: str) -> Dict[str, Any]:
    h, w, _ = img_bgr.shape
    x1, y1, x2, y2 = [max(0, int(v)) for v in bbox]
    x2, y2 = min(w, x2), min(h, y2)

    if x2 <= x1 or y2 <= y1:
        return {"estimated_depth_cm": 3.5, "depth_category": "Moderate Crater (3–7 cm)"}

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    inner_roi = gray[y1:y2, x1:x2]
    inner_mean = float(np.mean(inner_roi)) if inner_roi.size > 0 else 110.0

    # Sample surrounding intact pavement rim for lighting calibration
    pad_x = max(8, int((x2 - x1) * 0.25))
    pad_y = max(8, int((y2 - y1) * 0.25))
    rx1, ry1 = max(0, x1 - pad_x), max(0, y1 - pad_y)
    rx2, ry2 = min(w, x2 + pad_x), min(h, y2 + pad_y)
    outer_roi = gray[ry1:ry2, rx1:rx2]
    outer_mean = float(np.mean(outer_roi)) if outer_roi.size > 0 else inner_mean + 15.0

    shadow_drop = max(0.0, outer_mean - inner_mean)
    box_area_ratio = ((x2 - x1) * (y2 - y1)) / float(max(1, w * h))
    vertical_perspective = ((y1 + y2) / 2.0) / float(max(1, h))

    raw_cm = 1.8 + (shadow_drop * 0.14) + (box_area_ratio * 28.0) + (vertical_perspective * 2.2)

    if "drain" in raw_class or "manhole" in raw_class:
        raw_cm = max(raw_cm, 18.0)
        category = "Critical Open Shaft (> 15 cm)"
    elif "water" in raw_class:
        raw_cm = max(raw_cm, 6.5)
        category = "Deep Waterlogged Pit (> 6 cm)"
    elif "crack" in raw_class or "tile" in raw_class:
        raw_cm = min(max(1.5, raw_cm * 0.55), 4.2)
        category = "Shallow Surface Break (< 4 cm)"
    else:
        raw_cm = min(max(2.0, raw_cm), 16.5)
        if raw_cm >= 7.0:
            category = "Deep Structural Crater (> 7 cm)"
        elif raw_cm >= 3.5:
            category = "Moderate Pothole (3.5–7 cm)"
        else:
            category = "Shallow Depression (< 3.5 cm)"

    return {
        "estimated_depth_cm": round(raw_cm, 1),
        "depth_category": category,
    }


def analyze_footpath_image(
    image_input: Union[str, bytes, bytearray, Image.Image],
    confidence_threshold: float = 0.25,
) -> Dict[str, Any]:
    """
    Universal Footpath & Road Accessibility Vision Auditor.
    Accepts a PIL.Image, raw image bytes, or a file path string.
    Returns bounding-box annotated PIL Image, detected hazards, severity, and mobility advisories.
    """
    if isinstance(image_input, Image.Image):
        img_pil = image_input.convert("RGB")
    elif isinstance(image_input, (bytes, bytearray)):
        img_pil = Image.open(io.BytesIO(image_input)).convert("RGB")
    else:
        img_pil = Image.open(str(image_input)).convert("RGB")

    img_rgb = np.array(img_pil)
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    h, w, _ = img_bgr.shape

    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    edges = cv2.Canny(blurred, 45, 135)

    # Detect high-contrast cracks/potholes via morphological closing
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    hazards: List[Dict[str, Any]] = []
    annotated_bgr = img_bgr.copy()
    min_area = (w * h) * 0.008

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area or area > (w * h) * 0.75:
            continue

        x, y, bw, bh = cv2.boundingRect(cnt)
        roi_gray = gray[y : y + bh, x : x + bw]
        mean_intensity = float(np.mean(roi_gray)) if roi_gray.size > 0 else 128.0
        area_ratio = area / float(w * h)

        if area_ratio > 0.06 or mean_intensity < 75:
            label = "Severe Pothole / Structural Hazard"
            sev = "RED"
            color = (36, 36, 220)  # BGR Red
            conf = min(0.97, round(0.76 + area_ratio * 1.5, 2))
        else:
            label = "Surface Crack / Uneven Paving"
            sev = "YELLOW"
            color = (0, 175, 245)  # BGR Amber
            conf = min(0.92, round(0.68 + area_ratio * 2.0, 2))

        if conf < confidence_threshold:
            continue

        bbox = [int(x), int(y), int(x + bw), int(y + bh)]
        raw_cls = "pothole" if sev == "RED" else "crack"
        depth_info = estimate_hazard_depth_cm(img_bgr, bbox, raw_cls)
        depth_cm = depth_info["estimated_depth_cm"]
        depth_cat = depth_info["depth_category"]
        full_label = f"{label} [~{depth_cm} cm]"

        cv2.rectangle(annotated_bgr, (x, y), (x + bw, y + bh), color, 3)
        tag = f"{full_label} ({int(conf * 100)}%)"
        cv2.rectangle(annotated_bgr, (x, max(0, y - 24)), (min(w, x + len(tag) * 9), y), color, -1)
        cv2.putText(
            annotated_bgr,
            tag,
            (x + 4, max(16, y - 6)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            2,
        )

        hazards.append(
            {
                "label": full_label,
                "severity": sev,
                "confidence": conf,
                "estimated_depth_cm": depth_cm,
                "depth_category": depth_cat,
                "bbox": bbox,
            }
        )


    
    # Sort top 6 largest detections
    hazards = sorted(
        hazards,
        key=lambda d: (d["bbox"][2] - d["bbox"][0]) * (d["bbox"][3] - d["bbox"][1]),
        reverse=True,
    )[:6]

    red_count = sum(1 for item in hazards if item["severity"] == "RED")
    yellow_count = sum(1 for item in hazards if item["severity"] == "YELLOW")

    if red_count > 0:
        severity_level = "RED"
        accessibility_score = max(18, 52 - red_count * 12 - yellow_count * 4)
        wheelchair_safe = False
        elder_safe = False
        action_track = "Municipal Escalation Required (Structural Reconstruction)"
        vehicle_advisory = "UNSAFE for 2-Wheelers & Autos (rim/tipping risk). 4-Wheelers proceed slowly with caution."
        reroute_suggestion = "Avoid this segment; switch to adjacent audited footpath or parallel main road."
        voice_alert_text = (
            f"Caution! {red_count} severe structural hazard detected ahead. "
            "Unsafe for wheelchair and elder passage. Please reroute immediately."
        )
    elif yellow_count > 0:
        severity_level = "YELLOW"
        accessibility_score = max(55, 82 - yellow_count * 6)
        wheelchair_safe = False
        elder_safe = True
        action_track = "Citizen / RWA Quick-Fix Initiative"
        vehicle_advisory = "PASSABLE with caution for 2-Wheelers and 4-Wheelers; watch for loose gravel."
        reroute_suggestion = "Wheelchair users should use smooth curb-cut lane; elders proceed carefully."
        voice_alert_text = (
            f"Advisory: {yellow_count} minor surface cracks detected ahead. "
            "Proceed carefully and stay toward the inner edge."
        )
    else:
        severity_level = "GREEN"
        accessibility_score = 94
        wheelchair_safe = True
        elder_safe = True
        action_track = "Verified Safe — No Action Needed"
        vehicle_advisory = "SAFE for all vehicles (2-Wheelers, 3-Wheelers, and 4-Wheelers)."
        reroute_suggestion = "Direct route is clear and barrier-free for all travelers."
        voice_alert_text = "Path verified clear and safe for wheelchairs, elders, and pedestrians."

    annotated_rgb = cv2.cvtColor(annotated_bgr, cv2.COLOR_BGR2RGB)
    annotated_pil = Image.fromarray(annotated_rgb)

    return {
        "severity_level": severity_level,
        "accessibility_score": accessibility_score,
        "detected_hazards": hazards,
        "hazards": hazards,
        "annotated_image": annotated_pil,
        "annotated_pil": annotated_pil,
        "wheelchair_safe": wheelchair_safe,
        "elder_safe": elder_safe,
        "vehicle_advisory": vehicle_advisory,
        "reroute_suggestion": reroute_suggestion,
        "action_track": action_track,
        "voice_alert_text": voice_alert_text,
    }
