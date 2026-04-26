"""
backend.py — Flask REST API Layer
====================================
Exposes business logic as HTTP endpoints.
Validates inputs, orchestrates api.py calls,
and returns JSON responses to the frontend.

Run with:
    python backend.py
    # or for production:
    flask --app backend run --port 5000

Endpoints:
    GET  /health                         → server health check
    GET  /languages                      → full language registry
    POST /translate                      → translate text
    POST /speak                          → text-to-speech (returns base64 MP3)
    POST /swap                           → swap language codes + texts
"""

import base64
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

from api import call_translation_api, call_tts_api

# ─────────────────────────────────────────────────────────
# APP SETUP
# ─────────────────────────────────────────────────────────

app = Flask(__name__)
CORS(app)  # allow Streamlit frontend (different port) to call this API

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────
# LANGUAGE REGISTRY
# ─────────────────────────────────────────────────────────

LANGUAGES: dict[str, str] = {
    "auto":    "🔍 Detect Language",
    "af": "Afrikaans",      "sq": "Albanian",       "am": "Amharic",
    "ar": "Arabic",         "hy": "Armenian",        "az": "Azerbaijani",
    "eu": "Basque",         "be": "Belarusian",      "bn": "Bengali",
    "bs": "Bosnian",        "bg": "Bulgarian",       "ca": "Catalan",
    "zh-cn": "Chinese (Simplified)",  "zh-tw": "Chinese (Traditional)",
    "hr": "Croatian",       "cs": "Czech",           "da": "Danish",
    "nl": "Dutch",          "en": "English",         "eo": "Esperanto",
    "et": "Estonian",       "tl": "Filipino",        "fi": "Finnish",
    "fr": "French",         "gl": "Galician",        "ka": "Georgian",
    "de": "German",         "el": "Greek",           "gu": "Gujarati",
    "ht": "Haitian Creole", "ha": "Hausa",           "he": "Hebrew",
    "hi": "Hindi",          "hu": "Hungarian",       "is": "Icelandic",
    "id": "Indonesian",     "ga": "Irish",           "it": "Italian",
    "ja": "Japanese",       "kn": "Kannada",         "kk": "Kazakh",
    "ko": "Korean",         "lv": "Latvian",         "lt": "Lithuanian",
    "mk": "Macedonian",     "ms": "Malay",           "ml": "Malayalam",
    "mt": "Maltese",        "mr": "Marathi",         "mn": "Mongolian",
    "ne": "Nepali",         "no": "Norwegian",       "fa": "Persian",
    "pl": "Polish",         "pt": "Portuguese",      "pa": "Punjabi",
    "ro": "Romanian",       "ru": "Russian",         "sr": "Serbian",
    "si": "Sinhala",        "sk": "Slovak",          "sl": "Slovenian",
    "so": "Somali",         "es": "Spanish",         "sw": "Swahili",
    "sv": "Swedish",        "ta": "Tamil",           "te": "Telugu",
    "th": "Thai",           "tr": "Turkish",         "uk": "Ukrainian",
    "ur": "Urdu",           "uz": "Uzbek",           "vi": "Vietnamese",
    "cy": "Welsh",          "xh": "Xhosa",           "yi": "Yiddish",
    "yo": "Yoruba",         "zu": "Zulu",
}

SOURCE_CODES  = list(LANGUAGES.keys())
TARGET_CODES  = [k for k in LANGUAGES if k != "auto"]
SOURCE_LABELS = [LANGUAGES[k] for k in SOURCE_CODES]
TARGET_LABELS = [LANGUAGES[k] for k in TARGET_CODES]

MAX_CHARS = 5000


# ─────────────────────────────────────────────────────────
# VALIDATION HELPERS
# ─────────────────────────────────────────────────────────

def _validate_translate_inputs(text: str, source_lang: str, target_lang: str) -> str | None:
    if not text.strip():
        return "Input text cannot be empty."
    if len(text) > MAX_CHARS:
        return f"Text exceeds {MAX_CHARS:,}-character limit ({len(text):,} entered)."
    if source_lang not in LANGUAGES:
        return f"Unknown source language code: '{source_lang}'."
    if target_lang not in TARGET_CODES:
        return f"Unknown or invalid target language code: '{target_lang}'."
    if source_lang == target_lang and source_lang != "auto":
        return "Source and target languages are the same."
    return None


def _validate_tts_inputs(text: str, lang: str) -> str | None:
    if not text.strip():
        return "No text provided for speech synthesis."
    if lang not in TARGET_CODES and lang != "auto":
        return f"Unknown language code for TTS: '{lang}'."
    return None


# ─────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Quick liveness check."""
    return jsonify({"status": "ok"})


@app.get("/languages")
def get_languages():
    """
    Return the full language registry so the frontend
    never needs to hard-code language lists.

    Response
    --------
    {
        "languages":     { code: label, … },
        "source_codes":  […],
        "target_codes":  […],
        "source_labels": […],
        "target_labels": […],
    }
    """
    return jsonify({
        "languages":     LANGUAGES,
        "source_codes":  SOURCE_CODES,
        "target_codes":  TARGET_CODES,
        "source_labels": SOURCE_LABELS,
        "target_labels": TARGET_LABELS,
    })


@app.post("/translate")
def translate():
    """
    Translate text.

    Request body (JSON)
    -------------------
    { "text": str, "source_lang": str, "target_lang": str }

    Response (JSON)
    ---------------
    { "translated_text": str|null, "detected_lang": str|null, "error": str|null }
    """
    body = request.get_json(silent=True) or {}
    text        = body.get("text", "")
    source_lang = body.get("source_lang", "auto")
    target_lang = body.get("target_lang", "en")

    err = _validate_translate_inputs(text, source_lang, target_lang)
    if err:
        return jsonify({"translated_text": None, "detected_lang": None, "error": err}), 400

    result = call_translation_api(text.strip(), source_lang, target_lang)

    # Resolve raw detected language code → human-readable label
    if result.get("detected_lang"):
        raw_code = result["detected_lang"]
        result["detected_lang"] = LANGUAGES.get(raw_code, raw_code.upper())

    status = 200 if not result.get("error") else 502
    return jsonify(result), status


@app.post("/speak")
def speak():
    """
    Convert text to speech (MP3).

    Request body (JSON)
    -------------------
    { "text": str, "lang": str }

    Response (JSON)
    ---------------
    {
        "audio_b64":   str|null,   ← base64-encoded MP3
        "lang_used":   str,
        "tts_fallback": bool,
        "error":       str|null
    }
    """
    body = request.get_json(silent=True) or {}
    text = body.get("text", "")
    lang = body.get("lang", "en")

    # If source panel sent 'auto', default to English
    effective_lang = "en" if lang == "auto" else lang

    err = _validate_tts_inputs(text, effective_lang)
    if err:
        return jsonify({
            "audio_b64": None, "lang_used": effective_lang,
            "tts_fallback": False, "error": err
        }), 400

    result = call_tts_api(text.strip(), effective_lang)

    tts_fallback = result.get("lang_used") != effective_lang
    audio_b64    = None
    if result.get("audio_bytes"):
        audio_b64 = base64.b64encode(result["audio_bytes"]).decode()

    response_body = {
        "audio_b64":    audio_b64,
        "lang_used":    result.get("lang_used", effective_lang),
        "tts_fallback": tts_fallback,
        "error":        result.get("error"),
    }

    status = 200 if not result.get("error") else 502
    return jsonify(response_body), status


@app.post("/swap")
def swap():
    """
    Swap source ↔ target language codes and their texts.
    Blocked when source is 'auto'.

    Request body (JSON)
    -------------------
    { "src_code": str, "tgt_code": str, "src_text": str, "tgt_text": str }

    Response (JSON)
    ---------------
    {
        "new_src_code": str, "new_tgt_code": str,
        "new_src_text": str, "new_tgt_text": str,
        "swapped": bool
    }
    """
    body     = request.get_json(silent=True) or {}
    src_code = body.get("src_code", "auto")
    tgt_code = body.get("tgt_code", "en")
    src_text = body.get("src_text", "")
    tgt_text = body.get("tgt_text", "")

    if src_code == "auto":
        return jsonify({
            "new_src_code": src_code, "new_tgt_code": tgt_code,
            "new_src_text": src_text, "new_tgt_text": tgt_text,
            "swapped": False,
        })

    return jsonify({
        "new_src_code": tgt_code, "new_tgt_code": src_code,
        "new_src_text": tgt_text, "new_tgt_text": src_text,
        "swapped": True,
    })
print("Correct 1")

# ─────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
print("Correct")