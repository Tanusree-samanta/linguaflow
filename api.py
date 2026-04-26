import io
import os
import logging
import requests
from dotenv import load_dotenv
from gtts import gTTS

load_dotenv()

logger = logging.getLogger(__name__)

TTS_SUPPORTED_LANGS = {
    "af", "ar", "bn", "bs", "ca", "cs", "cy", "da", "de", "el", "en",
    "eo", "es", "et", "fi", "fr", "gu", "hi", "hr", "hu", "hy", "id",
    "is", "it", "ja", "kn", "ko", "lv", "mk", "ml", "mr", "nl", "no",
    "pl", "pt", "ro", "ru", "si", "sk", "sq", "sr", "sv", "sw", "ta",
    "te", "th", "tl", "tr", "uk", "ur", "vi", "zh-cn", "zh-tw",
}

def call_translation_api(text: str, source_lang: str, target_lang: str) -> dict:
    effective_source = "en" if source_lang == "auto" else source_lang
    lang_pair = f"{effective_source}|{target_lang}"

    try:
        response = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": text, "langpair": lang_pair},
            timeout=10,
        )
        if response.status_code != 200:
            return {"translated_text": None, "detected_lang": None,
                    "error": f"MyMemory error {response.status_code}"}

        data = response.json()
        if data.get("responseStatus") != 200:
            return {"translated_text": None, "detected_lang": None,
                    "error": data.get("responseDetails", "Unknown MyMemory error")}

        translated = data["responseData"]["translatedText"]
        logger.info("[API] Translation OK: %d chars → %s", len(text), target_lang)
        return {"translated_text": translated, "detected_lang": None, "error": None}

    except requests.Timeout:
        return {"translated_text": None, "detected_lang": None,
                "error": "Request timed out. Check your internet connection."}
    except Exception as exc:
        return {"translated_text": None, "detected_lang": None, "error": str(exc)}


def call_tts_api(text: str, lang: str) -> dict:
    lang_used = lang if lang in TTS_SUPPORTED_LANGS else "en"
    if lang_used != lang:
        logger.warning("[API] TTS: '%s' unsupported, falling back to 'en'", lang)

    try:
        tts = gTTS(text=text, lang=lang_used, slow=False)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        buf.seek(0)
        logger.info("[API] TTS OK: lang=%s, chars=%d", lang_used, len(text))
        return {"audio_bytes": buf.read(), "lang_used": lang_used, "error": None}

    except Exception as exc:
        logger.error("[API] TTS failed: %s", exc)
        return {"audio_bytes": None, "lang_used": lang_used, "error": str(exc)}