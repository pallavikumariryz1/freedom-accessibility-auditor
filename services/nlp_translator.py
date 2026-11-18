import json
import time
from pathlib import Path
import streamlit as st

CACHE_FILE = Path(__file__).resolve().parent.parent / "data" / "translation_cache.json"

SUPPORTED_LANGUAGES = {
    "English": ("en", "en-GB"),
    "हिन्दी (Hindi)": ("hi", "hi-IN"),
    "বাংলা (Bengali)": ("bn", "bn-IN"),
    "मराठी (Marathi)": ("mr", "mr-IN"),
    "தமிழ் (Tamil)": ("ta", "ta-IN"),
    "తెలుగు (Telugu)": ("te", "te-IN"),
    "ગુજરાતી (Gujarati)": ("gu", "gu-IN"),
    "ಕನ್ನಡ (Kannada)": ("kn", "kn-IN"),
    "മലയാളം (Malayalam)": ("ml", "ml-IN"),
    "ਪੰਜਾਬੀ (Punjabi)": ("pa", "pa-IN"),
    "اردو (Urdu)": ("ur", "ur-PK"),
    "Español (Spanish)": ("es", "es-ES"),
    "Français (French)": ("fr", "fr-FR"),
}


def _load_disk_cache() -> dict:
    try:
        if CACHE_FILE.exists():
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_disk_cache(cache: dict) -> None:
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def nlp_translate(text: str, target_lang_code: str) -> str:
    if not text or not text.strip() or target_lang_code == "en":
        return text

    cache = _load_disk_cache()
    cache_key = f"{target_lang_code}::{text}"
    if cache_key in cache and cache[cache_key] != text:
        return cache[cache_key]

    # Find matching locale code for MyMemoryTranslator
    mymemory_locale = target_lang_code
    for _, (short_code, full_locale) in SUPPORTED_LANGUAGES.items():
        if short_code == target_lang_code:
            mymemory_locale = full_locale
            break

    translated = ""
    # Engine 1: MyMemory Neural Translator (No IP block on burst requests)
    try:
        from deep_translator import MyMemoryTranslator
        time.sleep(0.15)
        translated = MyMemoryTranslator(source="en-GB", target=mymemory_locale).translate(text)
    except Exception:
        pass

    # Engine 2: Google Translator fallback with rate-limit spacing
    if not translated or translated.strip() == text.strip():
        try:
            from deep_translator import GoogleTranslator
            time.sleep(0.35)
            translated = GoogleTranslator(source="en", target=target_lang_code).translate(text)
        except Exception:
            pass

    if translated and translated.strip() and translated.strip() != text.strip():
        cache[cache_key] = translated.strip()
        _save_disk_cache(cache)
        return translated.strip()

    return text


def render_language_selector() -> tuple[str, str]:
    choice = st.sidebar.selectbox(
        "🌐 Select Language / भाषा चुनें",
        list(SUPPORTED_LANGUAGES.keys()),
        index=0,
        key="global_nlp_lang_select",
    )
    short_code = SUPPORTED_LANGUAGES[choice][0]
    st.session_state["nlp_lang_code"] = short_code
    return choice, short_code
