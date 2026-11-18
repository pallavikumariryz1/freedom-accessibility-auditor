import io
import math
from typing import Any, Dict, List

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def parse_voice_intent(transcript: str) -> Dict[str, str]:
    text = (transcript or "").strip().lower()
    if not text:
        return {"intent": "BRIEFING", "label": "Area Safety Briefing"}
    if any(k in text for k in ["sos", "emergency", "help", "stuck", "danger", "मदद", "आपातकाल", "खतरा"]):
        return {"intent": "SOS", "label": "Emergency SOS Broadcast"}
    if any(k in text for k in ["wheelchair", "elder", "ramp", "step", "cane", "blind", "व्हीलचेयर", "बुजुर्ग", "छड़ी"]):
        return {"intent": "ACCESSIBILITY_CHECK", "label": "Wheelchair & Elder Barrier Check"}
    if any(k in text for k in ["route", "navigate", "way", "go to", "path", "रास्ता", "मार्ग"]):
        return {"intent": "SAFE_ROUTE", "label": "Safe Barrier-Free Route Guidance"}
    if any(k in text for k in ["report", "pothole", "broken", "crack", "drain", "गड्ढा", "टूटा"]):
        return {"intent": "REPORT_PROMPT", "label": "Report New Footpath Hazard"}
    return {"intent": "BRIEFING", "label": "Area Safety Briefing"}


def build_spoken_safety_briefing(
    audits: List[Dict[str, Any]],
    lat: float,
    lon: float,
    radius_km: float = 1.5,
    mode: str = "BRIEFING",
) -> str:
    nearby = []
    for item in audits:
        if item.get("ticket_status") == "RESOLVED":
            continue
        ilat = item.get("latitude")
        ilon = item.get("longitude")
        if ilat is None or ilon is None:
            continue
        dist = haversine_km(lat, lon, float(ilat), float(ilon))
        if dist <= radius_km:
            nearby.append((dist, item))

    nearby.sort(key=lambda x: x[0])

    if mode == "SOS":
        return (
            f"Emergency SOS mode activated at latitude {lat:.4f}, longitude {lon:.4f}. "
            "Your live accessibility coordinates and nearest safe-zone markers are ready to share with family and local volunteers. "
            "Stay on a flat, clear surface while assistance is alerted."
        )

    if not nearby:
        return (
            f"Good news. No active footpath or road hazards were found within {radius_km} kilometers of your current position. "
            "The tactile footpath and crossings appear clear. Proceed safely."
        )

    red_items = [x for x in nearby if x[1].get("severity_level") == "RED"]
    yellow_items = [x for x in nearby if x[1].get("severity_level") == "YELLOW"]

    parts = [
        f"FreeDom Vigilance Alert. Found {len(nearby)} active hazards within {radius_km} kilometers. "
        f"There are {len(red_items)} severe municipal hazards and {len(yellow_items)} minor repair zones."
    ]

    for dist, item in nearby[:3]:
        meters = int(dist * 1000)
        sev = item.get("severity_level", "YELLOW")
        voice_note = item.get("voice_alert_text") or item.get("reroute_suggestion") or "Use caution and keep to the inner footpath edge."
        parts.append(
            f"At {meters} meters away, severity {sev}, ticket {item.get('ticket_id', '')}: {voice_note}"
        )

    if mode == "ACCESSIBILITY_CHECK":
        if red_items:
            parts.append("Wheelchair and elder advisory: Severe surface breaks detected ahead. Do not attempt unassisted crossing; take the alternate verified footpath.")
        else:
            parts.append("Wheelchair and elder advisory: Only minor surface wear reported. Proceed at moderate pace.")

    return " ".join(parts)


def text_to_speech_bytes(text: str, lang_code: str = "en") -> bytes | None:
    if not GTTS_AVAILABLE or not text.strip():
        return None
    try:
        tts = gTTS(text=text, lang=lang_code, slow=False)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        return buf.read()
    except Exception:
        try:
            tts = gTTS(text=text, lang="en", slow=False)
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            buf.seek(0)
            return buf.read()
        except Exception:
            return None


def transcribe_audio_bytes(audio_bytes: bytes) -> str:
    if not SR_AVAILABLE or not audio_bytes:
        return ""
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio_data = recognizer.record(source)
            return recognizer.recognize_google(audio_data)
    except Exception:
        return ""
