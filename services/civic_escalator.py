import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def generate_municipal_grievance_pdf(
    ticket_id: str,
    reporter_name: str,
    mobility_profile: str,
    latitude: float,
    longitude: float,
    severity_level: str,
    accessibility_score: float,
    detected_hazards: List[Dict[str, Any]],
    wheelchair_advisory: str,
    elder_advisory: str,
    vehicle_advisory: str,
    reroute_suggestion: str,
    annotated_image_path: Optional[str] = None,
    original_image_path: Optional[str] = None,
    output_dir: str = "data/reports",
) -> str:
    os.makedirs(output_dir, exist_ok=True)
    pdf_filename = f"{ticket_id}_Municipal_Grievance.pdf"
    pdf_path = os.path.abspath(os.path.join(output_dir, pdf_filename))

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        rightMargin=16 * mm,
        leftMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "FreeDomTitle",
        parent=styles["Heading1"],
        fontSize=18,
        textColor=colors.HexColor("#141136"),
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "FreeDomSubtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#8b5a2b"),
        spaceAfter=12,
    )
    section_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=colors.HexColor("#141136"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontSize=9.5,
        leading=13,
    )

    elements = []
    elements.append(Paragraph("FREEDOM ACCESSIBILITY & ROAD SAFETY GRIEVANCE REPORT", title_style))
    elements.append(
        Paragraph(
            "FreeDom (Free to Dominate: Detect | Object | Eliminate) — Municipal Civic Escalation Docket",
            subtitle_style,
        )
    )

    timestamp_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    meta_data = [
        ["Ticket ID:", ticket_id, "Severity Verdict:", severity_level],
        ["Date / Time:", timestamp_str, "Accessibility Score:", f"{accessibility_score:.1f} / 100"],
        ["GPS Coordinates:", f"{latitude:.6f}, {longitude:.6f}", "Reporter Profile:", f"{reporter_name} ({mobility_profile})"],
        ["Map Reference:", f"https://maps.google.com/?q={latitude:.6f},{longitude:.6f}", "Escalation Track:", "Municipal Re-Construction"],
    ]

    meta_table = Table(meta_data, colWidths=[34 * mm, 56 * mm, 36 * mm, 52 * mm])
    meta_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef1f8")),
                ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#eef1f8")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#141136")),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c5cde0")),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elements.append(meta_table)
    elements.append(Spacer(1, 8))

    # Safe image resolution with existence checks and fallback
    chosen_image = None
    for candidate in (annotated_image_path, original_image_path):
        if candidate and os.path.isfile(candidate) and os.path.getsize(candidate) > 0:
            chosen_image = candidate
            break

    elements.append(Paragraph("1. Computer Vision Bounding-Box Evidence", section_style))
    if chosen_image:
        try:
            img = RLImage(chosen_image, width=155 * mm, height=92 * mm, kind="proportional")
            elements.append(img)
        except Exception as img_err:
            elements.append(
                Paragraph(
                    f"<i>Visual evidence recorded on server ({os.path.basename(chosen_image)}). Preview note: {img_err}</i>",
                    body_style,
                )
            )
    else:
        elements.append(
            Paragraph(
                "<i>Image evidence logged in spatial database; local preview file unavailable at PDF render time.</i>",
                body_style,
            )
        )

    elements.append(Spacer(1, 8))
    elements.append(Paragraph("2. Detected Structural & Surface Hazards", section_style))

    hazard_rows = [["#", "Hazard Class", "Severity", "Confidence", "Bounding Box (x1, y1, x2, y2)"]]
    if detected_hazards:
        for idx, h in enumerate(detected_hazards, start=1):
            label = str(h.get("label", h.get("class_name", "Surface Defect")))
            sev = str(h.get("severity", severity_level))
            conf = f"{float(h.get('confidence', 0.85)) * 100:.1f}%"
            bbox = str(h.get("bbox", h.get("box", "N/A")))
            hazard_rows.append([str(idx), label, sev, conf, bbox])
    else:
        hazard_rows.append(["1", "Surface Irregularity / Manual Escalation", severity_level, "N/A", "Full Frame"])

    hazard_table = Table(hazard_rows, colWidths=[10 * mm, 56 * mm, 28 * mm, 26 * mm, 58 * mm])
    hazard_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#141136")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c5cde0")),
                ("PADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    elements.append(hazard_table)

    elements.append(Spacer(1, 8))
    elements.append(Paragraph("3. Mobility & Public Safety Impact Assessment", section_style))
    elements.append(Paragraph(f"<b>Wheelchair & Stroller Access:</b> {wheelchair_advisory}", body_style))
    elements.append(Spacer(1, 3))
    elements.append(Paragraph(f"<b>Elders & Visually Impaired Pedestrians:</b> {elder_advisory}", body_style))
    elements.append(Spacer(1, 3))
    elements.append(Paragraph(f"<b>Motorized Vehicle Safety:</b> {vehicle_advisory}", body_style))
    elements.append(Spacer(1, 3))
    elements.append(Paragraph(f"<b>Recommended Interim Reroute:</b> {reroute_suggestion}", body_style))

    elements.append(Spacer(1, 10))
    elements.append(
        Paragraph(
            "<i>Generated automatically by FreeDom Spatial Vigilance Engine for immediate municipal engineering review and Right-of-Way restoration.</i>",
            body_style,
        )
    )

    doc.build(elements)
    return pdf_path
