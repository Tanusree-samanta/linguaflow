"""
frontend.py — Streamlit UI Layer
==================================
All UI code lives here. Calls the Flask backend API over HTTP.
No direct imports from backend.py or api.py.

Run with:  streamlit run frontend.py
(Flask backend must be running separately: python backend.py)
"""

import base64
import logging
import os
import requests
import streamlit as st
from dotenv import load_dotenv

# ── Load environment variables from .env file ──
load_dotenv()

logging.basicConfig(level=logging.INFO)

# ─────────────────────────────────────────────────────────
# FLASK BACKEND BASE URL
# Loaded from .env (BACKEND_URL) or defaults to localhost
# ─────────────────────────────────────────────────────────

BACKEND_URL = os.getenv("BACKEND_URL", "https://linguaflow-backend.onrender.com")


# ─────────────────────────────────────────────────────────
# HTTP CLIENT HELPERS
# ─────────────────────────────────────────────────────────

def _get(path: str) -> dict:
    """GET request to the Flask backend. Returns parsed JSON or an error dict."""
    try:
        r = requests.get(f"{BACKEND_URL}{path}", timeout=10)
        if not r.ok:
            return {
                "error": f"Backend returned HTTP {r.status_code}: {r.text[:200]}",
                "_http_status": r.status_code,
            }
        return r.json()
    except requests.ConnectionError as exc:
        return {"error": f"Cannot connect to backend at {BACKEND_URL}. Is it running?", "_connection_error": True}
    except requests.Timeout:
        return {"error": "Backend request timed out. The server may be overloaded.", "_timeout": True}
    except Exception as exc:
        return {"error": f"Unexpected error contacting backend: {exc}"}


def _post(path: str, payload: dict) -> dict:
    """POST JSON to the Flask backend. Returns parsed JSON or an error dict."""
    try:
        r = requests.post(f"{BACKEND_URL}{path}", json=payload, timeout=30)
        if not r.ok:
            return {
                "error": f"Backend returned HTTP {r.status_code}: {r.text[:200]}",
                "_http_status": r.status_code,
            }
        return r.json()
    except requests.ConnectionError as exc:
        return {"error": f"Cannot connect to backend at {BACKEND_URL}. Is it running?", "_connection_error": True}
    except requests.Timeout:
        return {"error": "Backend request timed out. The server may be overloaded.", "_timeout": True}
    except Exception as exc:
        return {"error": f"Unexpected error contacting backend: {exc}"}


# ─────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────

def _health_check() -> dict:
    """Check if the Flask backend is reachable."""
    try:
        r = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if r.status_code == 200:
            return {"ok": True, "status": r.json()}
        return {"ok": False, "error": f"HTTP {r.status_code}"}
    except requests.ConnectionError:
        return {"ok": False, "error": f"Cannot connect to {BACKEND_URL}"}
    except requests.Timeout:
        return {"ok": False, "error": "Health check timed out"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# ─────────────────────────────────────────────────────────
# LOAD LANGUAGE LISTS FROM BACKEND  (cached for the session)
# ─────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def _load_languages() -> dict:
    data = _get("/languages")
    if data.get("error"):
        # Return minimal defaults so the UI doesn't crash
        return {
            "source_codes": ["auto", "en"],
            "target_codes": ["en"],
            "source_labels": ["🔍 Detect Language", "English"],
            "target_labels": ["English"],
            "_fallback": True,
            "_error": data.get("error"),
        }
    data["_fallback"] = False
    return data


_lang_data    = _load_languages()
SOURCE_CODES  = _lang_data.get("source_codes",  ["auto", "en"])
TARGET_CODES  = _lang_data.get("target_codes",  ["en"])
SOURCE_LABELS = _lang_data.get("source_labels", ["🔍 Detect Language", "English"])
TARGET_LABELS = _lang_data.get("target_labels", ["English"])


# ─────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────

st.set_page_config(
    page_title="LinguaFlow — AI Translation",
    page_icon="🌐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────
# DESIGN SYSTEM — Figma Token Mapping
# ─────────────────────────────────────────────────────────

st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">

<style>
/* ════════════════════════════════════════════
   FIGMA DESIGN TOKENS — edit these variables
   ════════════════════════════════════════════ */
:root {
  --clr-bg:           #07090f;
  --clr-surface:      #0f1219;
  --clr-surface-2:    #161b27;
  --clr-surface-3:    #1d2235;
  --clr-border:       #1f2640;
  --clr-border-focus: #3d5af1;
  --clr-accent:       #3d5af1;
  --clr-accent-alt:   #8b5cf6;
  --clr-accent-glow:  rgba(61,90,241,0.22);
  --clr-success:      #10d9a0;
  --clr-warning:      #f59e0b;
  --clr-error:        #f43f5e;
  --clr-text:         #eef0f8;
  --clr-text-2:       #7e8aab;
  --clr-text-3:       #3f4a65;

  --font-ui:   'Outfit', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;

  --sp-xs:  4px;  --sp-sm:  8px;  --sp-md:  16px;
  --sp-lg:  24px; --sp-xl:  36px; --sp-2xl: 52px;

  --r-sm:  6px; --r-md:  12px; --r-lg:  18px;
  --r-xl:  26px; --r-2xl: 36px;

  --shadow-card:   0 8px 32px rgba(0,0,0,0.5);
  --shadow-glow:   0 0 48px rgba(61,90,241,0.12);
  --shadow-btn:    0 4px 20px rgba(61,90,241,0.35);
}

html, body,
[data-testid="stAppViewContainer"],
[data-testid="stApp"] {
  background-color: var(--clr-bg) !important;
  color: var(--clr-text) !important;
  font-family: var(--font-ui) !important;
}

[data-testid="stAppViewContainer"]::before {
  content: '';
  position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background:
    radial-gradient(ellipse 70% 45% at 10% 0%,  rgba(61,90,241,.08)  0%, transparent 65%),
    radial-gradient(ellipse 55% 40% at 90% 90%, rgba(139,92,246,.07) 0%, transparent 60%),
    radial-gradient(ellipse 40% 30% at 60% 40%, rgba(16,217,160,.03) 0%, transparent 55%);
}

#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"] { display: none !important; }

h1,h2,h3,h4 {
  font-family: var(--font-ui) !important;
  letter-spacing: -0.03em !important;
  color: var(--clr-text) !important;
}

textarea,
[data-testid="stTextArea"] textarea {
  background: var(--clr-surface-2) !important;
  border: 1.5px solid var(--clr-border) !important;
  border-radius: var(--r-lg) !important;
  color: var(--clr-text) !important;
  font-family: var(--font-ui) !important;
  font-size: .975rem !important;
  line-height: 1.7 !important;
  padding: var(--sp-md) !important;
  transition: border-color .2s ease, box-shadow .2s ease !important;
}
textarea:focus,
[data-testid="stTextArea"] textarea:focus {
  border-color: var(--clr-border-focus) !important;
  box-shadow: 0 0 0 3px var(--clr-accent-glow) !important;
  outline: none !important;
}

[data-testid="stSelectbox"] > div > div {
  background: var(--clr-surface-2) !important;
  border: 1.5px solid var(--clr-border) !important;
  border-radius: var(--r-md) !important;
  color: var(--clr-text) !important;
  font-family: var(--font-ui) !important;
  font-size: .9rem !important;
}
[data-testid="stSelectbox"] > div > div:focus-within {
  border-color: var(--clr-border-focus) !important;
  box-shadow: 0 0 0 3px var(--clr-accent-glow) !important;
}
[data-testid="stSelectbox"] svg { color: var(--clr-text-2) !important; }

.stButton > button {
  background: linear-gradient(135deg, var(--clr-accent) 0%, var(--clr-accent-alt) 100%) !important;
  color: #fff !important;
  border: none !important;
  border-radius: var(--r-md) !important;
  font-family: var(--font-ui) !important;
  font-weight: 600 !important;
  font-size: .9rem !important;
  letter-spacing: .01em !important;
  padding: .6rem 1.4rem !important;
  box-shadow: var(--shadow-btn) !important;
  transition: transform .15s ease, box-shadow .15s ease, opacity .15s !important;
  width: 100%;
}
.stButton > button:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 8px 30px rgba(61,90,241,.50) !important;
}
.stButton > button:active  { transform: translateY(0) !important; }
.stButton > button:disabled { opacity: .45 !important; transform: none !important; }

.lf-card {
  background: var(--clr-surface);
  border: 1px solid var(--clr-border);
  border-radius: var(--r-xl);
  padding: var(--sp-xl);
  box-shadow: var(--shadow-card), var(--shadow-glow);
  margin-bottom: var(--sp-md);
  position: relative;
  overflow: hidden;
}
.lf-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent, rgba(61,90,241,.4), transparent);
}

.badge {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: .68rem; font-weight: 700; letter-spacing: .09em;
  text-transform: uppercase;
  color: var(--clr-accent);
  background: rgba(61,90,241,.1);
  border: 1px solid rgba(61,90,241,.22);
  padding: 3px 10px; border-radius: 100px;
}
.badge-success {
  color: var(--clr-success);
  background: rgba(16,217,160,.1);
  border-color: rgba(16,217,160,.25);
}
.badge-warn {
  color: var(--clr-warning);
  background: rgba(245,158,11,.1);
  border-color: rgba(245,158,11,.25);
}
.badge-error {
  color: var(--clr-error);
  background: rgba(244,63,94,.1);
  border-color: rgba(244,63,94,.25);
}

.alert {
  border-radius: var(--r-md);
  padding: .65rem 1rem;
  font-size: .875rem;
  font-weight: 500;
  margin-top: .5rem;
}
.alert-error   { background: rgba(244,63,94,.1);  border:1px solid rgba(244,63,94,.25);  color: var(--clr-error);   }
.alert-success { background: rgba(16,217,160,.1); border:1px solid rgba(16,217,160,.25); color: var(--clr-success); }
.alert-warn    { background: rgba(245,158,11,.1); border:1px solid rgba(245,158,11,.25); color: var(--clr-warning); }

.section-label {
  font-size: .68rem; font-weight: 700;
  letter-spacing: .1em; text-transform: uppercase;
  color: var(--clr-text-3); margin-bottom: 6px;
}

.char-count       { font-size: .74rem; color: var(--clr-text-3); text-align: right; margin-top:-8px; }
.char-count-warn  { color: var(--clr-warning) !important; }
.char-count-over  { color: var(--clr-error)   !important; }

hr { border-color: var(--clr-border) !important; margin: var(--sp-lg) 0 !important; }

audio {
  width: 100%; height: 36px;
  border-radius: var(--r-md);
  background: var(--clr-surface-2);
  margin-top: var(--sp-sm);
}

[data-testid="column"] { padding: 0 6px !important; }
.stSpinner > div { border-top-color: var(--clr-accent) !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# SESSION STATE INITIALISATION
# ─────────────────────────────────────────────────────────

_defaults = {
    "translated_text": "",
    "detected_lang":   "",
    "src_audio_html":  "",
    "tgt_audio_html":  "",
    "error_msg":       "",
    "success_msg":     "",
    "warn_msg":        "",
}
for _k, _v in _defaults.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ─────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────

def _audio_player_html(audio_b64: str) -> str:
    return f'<audio controls autoplay src="data:audio/mp3;base64,{audio_b64}"></audio>'


def _clear_messages():
    st.session_state.error_msg   = ""
    st.session_state.success_msg = ""
    st.session_state.warn_msg    = ""


# ─────────────────────────────────────────────────────────
# CONNECTION STATUS BANNER
# ─────────────────────────────────────────────────────────

_health = _health_check()
if _health["ok"]:
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:1rem;">
      <span style="width:10px;height:10px;border-radius:50%;background:#10d9a0;display:inline-block;box-shadow:0 0 8px #10d9a0;"></span>
      <span style="font-size:.78rem;color:#7e8aab;">Backend connected — <code>{BACKEND_URL}</code></span>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:1rem;">
      <span style="width:10px;height:10px;border-radius:50%;background:#f43f5e;display:inline-block;box-shadow:0 0 8px #f43f5e;"></span>
      <span style="font-size:.78rem;color:#f43f5e;font-weight:600;">Backend disconnected — {_health.get('error', 'Unknown error')}</span>
    </div>
    <div class="alert alert-error" style="margin-bottom:1.2rem;">
      ⚠ The frontend cannot reach the backend at <code>{BACKEND_URL}</code>.<br>
      Make sure Flask is running: &nbsp;<code>python backend.py</code>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# FALLBACK WARNING (if language list could not be loaded)
# ─────────────────────────────────────────────────────────

if _lang_data.get("_fallback"):
    st.markdown(f"""
    <div class="alert alert-warn" style="margin-bottom:1.2rem;">
      ⚡ Using fallback language list. {_lang_data.get('_error', '')}
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────

st.markdown("""
<div style="display:flex;align-items:center;justify-content:space-between;
            padding:1.4rem 0 2.2rem;">
  <div style="display:flex;align-items:center;gap:12px;">
    <div style="width:40px;height:40px;
                background:linear-gradient(135deg,#3d5af1,#8b5cf6);
                border-radius:12px;display:flex;align-items:center;
                justify-content:center;font-size:20px;
                box-shadow:0 4px 16px rgba(61,90,241,.4);">🌐</div>
    <div>
      <div style="font-size:1.45rem;font-weight:800;letter-spacing:-0.04em;
                  background:linear-gradient(90deg,#eef0f8 30%,#7e8aab);
                  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
                  line-height:1;">LinguaFlow</div>
      <div style="font-size:.7rem;color:#3f4a65;letter-spacing:.06em;
                  text-transform:uppercase;font-weight:600;">Translation Suite</div>
    </div>
  </div>
  <span class="badge">Google Cloud API · gTTS · Flask</span>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center;margin-bottom:2.8rem;">
  <h1 style="font-size:clamp(1.8rem,4.5vw,3rem);font-weight:800;line-height:1.1;margin-bottom:.7rem;">
    Break every language barrier,
    <span style="background:linear-gradient(135deg,#3d5af1,#8b5cf6);
                 -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
      instantly.
    </span>
  </h1>
  <p style="color:#7e8aab;font-size:1rem;font-weight:300;letter-spacing:.01em;">
    100+ languages &nbsp;·&nbsp; Auto-detection &nbsp;·&nbsp; Text-to-Speech
  </p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# LANGUAGE SELECTOR CARD
# ─────────────────────────────────────────────────────────

st.markdown('<div class="lf-card">', unsafe_allow_html=True)

col_src, col_mid, col_tgt = st.columns([10, 2, 10])

with col_src:
    st.markdown('<p class="section-label">Source Language</p>', unsafe_allow_html=True)
    src_label = st.selectbox("Source", SOURCE_LABELS, index=0,
                              label_visibility="collapsed", key="sel_src")
    src_code  = SOURCE_CODES[SOURCE_LABELS.index(src_label)]

with col_mid:
    st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)
    swap_clicked = st.button("⇄", key="btn_swap",
                              help="Swap source and target languages",
                              use_container_width=True)

with col_tgt:
    st.markdown('<p class="section-label">Target Language</p>', unsafe_allow_html=True)
    default_tgt  = TARGET_LABELS.index("Spanish") if "Spanish" in TARGET_LABELS else 0
    tgt_label    = st.selectbox("Target", TARGET_LABELS, index=default_tgt,
                                 label_visibility="collapsed", key="sel_tgt")
    tgt_code     = TARGET_CODES[TARGET_LABELS.index(tgt_label)]

st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# TRANSLATION PANELS CARD
# ─────────────────────────────────────────────────────────

st.markdown('<div class="lf-card">', unsafe_allow_html=True)

left_panel, right_panel = st.columns(2)

# ── LEFT — Input ──
with left_panel:
    st.markdown('<p class="section-label">Input Text</p>', unsafe_allow_html=True)

    source_text = st.text_area(
        "Input",
        value=st.session_state.get("src_text_val", ""),
        height=240,
        max_chars=5000,
        placeholder="Type or paste your text here…",
        label_visibility="collapsed",
        key="input_textarea",
    )

    char_len  = len(source_text)
    cnt_class = "char-count-over" if char_len > 5000 else ("char-count-warn" if char_len > 4500 else "")
    st.markdown(f'<p class="char-count {cnt_class}">{char_len:,} / 5,000</p>',
                unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        clear_clicked   = st.button("✕  Clear", key="btn_clear",   use_container_width=True)
    with c2:
        tts_src_clicked = st.button("🔊 Speak", key="btn_tts_src", use_container_width=True)

    if st.session_state.src_audio_html:
        st.markdown(st.session_state.src_audio_html, unsafe_allow_html=True)

# ── RIGHT — Output ──
with right_panel:
    detected = st.session_state.detected_lang
    lbl = '<p class="section-label">Translation</p>'
    if detected:
        lbl += f'<span class="badge badge-success" style="margin-bottom:6px;display:inline-flex;">🔍 {detected}</span>'
    st.markdown(lbl, unsafe_allow_html=True)

    st.text_area(
        "Output",
        value=st.session_state.translated_text,
        height=240,
        placeholder="Translation appears here…",
        label_visibility="collapsed",
        disabled=True,
    )
    o1, o2, _ = st.columns(3)
    with o1:
        copy_clicked    = st.button("📋 Copy",  key="btn_copy",     use_container_width=True)
    with o2:
        tts_tgt_clicked = st.button("🔊 Speak", key="btn_tts_tgt",  use_container_width=True)

    if st.session_state.tgt_audio_html:
        st.markdown(st.session_state.tgt_audio_html, unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# TRANSLATE BUTTON
# ─────────────────────────────────────────────────────────

st.markdown("""
<style>
.translate-bar .stButton > button {
  background: linear-gradient(135deg, #3d5af1 0%, #8b5cf6 100%) !important;
  font-size: 1.1rem !important;
  font-weight: 700 !important;
  letter-spacing: .05em !important;
  padding: 1rem 0 !important;
  border-radius: var(--r-lg) !important;
  box-shadow: 0 6px 32px rgba(61,90,241,.50), 0 0 0 1px rgba(61,90,241,.25) !important;
}
.translate-bar .stButton > button:hover {
  transform: translateY(-3px) !important;
  box-shadow: 0 14px 44px rgba(61,90,241,.65), 0 0 0 1px rgba(61,90,241,.35) !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="lf-card translate-bar" style="padding:1.4rem 2rem;">', unsafe_allow_html=True)
_, btn_col, _ = st.columns([2, 5, 2])
with btn_col:
    translate_clicked = st.button(
        "🌐  Translate Now",
        key="btn_translate",
        use_container_width=True,
        help="Translate the input text",
    )
st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# EVENT HANDLERS
# ─────────────────────────────────────────────────────────

# ── Translate ──
if translate_clicked:
    _clear_messages()
    st.session_state.detected_lang  = ""
    st.session_state.src_audio_html = ""
    st.session_state.tgt_audio_html = ""

    with st.spinner("Translating…"):
        result = _post("/translate", {
            "text": source_text,
            "source_lang": src_code,
            "target_lang": tgt_code,
        })

    if result.get("error"):
        st.session_state.error_msg = result["error"]
    else:
        translated = result.get("translated_text") or ""
        st.session_state.translated_text = translated
        st.session_state.detected_lang   = result.get("detected_lang") or ""
        st.session_state.success_msg     = "Translation complete ✓"
    st.rerun()

# ── Swap ──
if swap_clicked:
    _clear_messages()
    swap = _post("/swap", {
        "src_code": src_code,
        "tgt_code": tgt_code,
        "src_text": source_text,
        "tgt_text": st.session_state.translated_text,
    })
    if swap.get("swapped"):
        new_src_label = SOURCE_LABELS[SOURCE_CODES.index(swap["new_src_code"])]
        new_tgt_label = TARGET_LABELS[TARGET_CODES.index(swap["new_tgt_code"])]
        st.session_state["sel_src"]        = new_src_label
        st.session_state["sel_tgt"]        = new_tgt_label
        st.session_state["src_text_val"]   = swap["new_src_text"]
        st.session_state.translated_text   = swap["new_tgt_text"]
        st.session_state.detected_lang     = ""
        st.session_state.src_audio_html    = ""
        st.session_state.tgt_audio_html    = ""
    else:
        st.session_state.warn_msg = "Set source language (not 'Detect') before swapping."
    st.rerun()

# ── Clear ──
if clear_clicked:
    for key in ("translated_text","detected_lang","src_audio_html","tgt_audio_html","src_text_val"):
        st.session_state[key] = ""
    _clear_messages()
    st.rerun()

# ── Copy ──
if copy_clicked:
    if st.session_state.translated_text:
        b64 = base64.b64encode(st.session_state.translated_text.encode()).decode()
        st.markdown(f"""
        <script>
        (async()=>{{
          const t = atob("{b64}");
          await navigator.clipboard.writeText(t);
        }})();
        </script>""", unsafe_allow_html=True)
        st.session_state.success_msg = "Copied to clipboard ✓"
    else:
        st.session_state.warn_msg = "Nothing to copy — translate something first."
    st.rerun()

# ── TTS: Source ──
if tts_src_clicked:
    _clear_messages()
    if source_text.strip():
        lang = "en" if src_code == "auto" else src_code
        with st.spinner("Generating speech…"):
            res = _post("/speak", {"text": source_text, "lang": lang})
        if res.get("error"):
            st.session_state.error_msg = res["error"]
        else:
            st.session_state.src_audio_html = _audio_player_html(res["audio_b64"])
            st.session_state.tgt_audio_html = ""
            if res.get("tts_fallback"):
                st.session_state.warn_msg = f"TTS unavailable for that language — played in English."
    else:
        st.session_state.warn_msg = "Enter some text before using speech."
    st.rerun()

# ── TTS: Target ──
if tts_tgt_clicked:
    _clear_messages()
    if st.session_state.translated_text.strip():
        with st.spinner("Generating speech…"):
            res = _post("/speak", {"text": st.session_state.translated_text, "lang": tgt_code})
        if res.get("error"):
            st.session_state.error_msg = res["error"]
        else:
            st.session_state.tgt_audio_html = _audio_player_html(res["audio_b64"])
            st.session_state.src_audio_html = ""
            if res.get("tts_fallback"):
                st.session_state.warn_msg = f"TTS unavailable for that language — played in English."
    else:
        st.session_state.warn_msg = "Translate something first before using speech."
    st.rerun()


# ─────────────────────────────────────────────────────────
# STATUS MESSAGES
# ─────────────────────────────────────────────────────────

if st.session_state.error_msg:
    st.markdown(f'<div class="alert alert-error">⚠ {st.session_state.error_msg}</div>',
                unsafe_allow_html=True)

if st.session_state.warn_msg:
    st.markdown(f'<div class="alert alert-warn">⚡ {st.session_state.warn_msg}</div>',
                unsafe_allow_html=True)

if st.session_state.success_msg:
    st.markdown(f'<div class="alert alert-success">✓ {st.session_state.success_msg}</div>',
                unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────

st.markdown("""
<div style="text-align:center;margin-top:3rem;padding-top:1.5rem;
            border-top:1px solid #1f2640;color:#3f4a65;font-size:.78rem;">
  LinguaFlow &nbsp;·&nbsp; Python · Streamlit · Flask · Google Cloud Translation API · gTTS
</div>
""", unsafe_allow_html=True)

