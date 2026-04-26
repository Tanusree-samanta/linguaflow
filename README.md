# 🌐 LinguaFlow — Translation Suite

```
frontend.py  ──HTTP/JSON──►  backend.py  ──calls──►  api.py  ──►  Google Cloud / gTTS
  (Streamlit UI)               (Flask REST)           (API layer)
```

---

## Project Structure

```
lingua_pro/
├── frontend.py       ← Streamlit UI        (calls Flask backend over HTTP)
├── backend.py        ← Flask REST API      (validation, routing, business logic)
├── api.py            ← API call layer      (Google Cloud Translation + gTTS)
├── .env              ← Your secrets        (never commit this)
├── .env.example      ← Copy → .env and add your key
├── requirements.txt
└── README.md
```

---

## Flask API Endpoints

| Method | Endpoint      | Description                              |
|--------|---------------|------------------------------------------|
| GET    | `/health`     | Liveness check                           |
| GET    | `/languages`  | Returns all supported language codes     |
| POST   | `/translate`  | Translate text between languages         |
| POST   | `/speak`      | Convert text to speech (returns base64 MP3) |
| POST   | `/swap`       | Swap source ↔ target language + text     |

---

## 1. Get Your Google Cloud API Key

1. Go to → https://console.cloud.google.com/
2. Create a project (or select existing)
3. Go to **APIs & Services → Library**
4. Search **"Cloud Translation API"** → Enable it
5. Go to **APIs & Services → Credentials**
6. Click **"+ Create Credentials" → API Key**
7. Copy the key

---

## 2. Add Your API Key

```bash
# Copy the example file
cp .env.example .env

# Open .env and paste your key
GOOGLE_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

---

## 3. Install & Run

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

You need **two terminals** — the Flask backend and Streamlit frontend run as separate processes.

**Terminal 1 — Flask backend:**
```bash
python backend.py
# Running on http://localhost:5000
```

**Terminal 2 — Streamlit frontend:**
```bash
streamlit run frontend.py
# Opens at http://localhost:8501
```

---

## How the Files Connect

```
frontend.py
  │  HTTP POST → /translate   { text, source_lang, target_lang }
  │  HTTP POST → /speak       { text, lang }
  │  HTTP POST → /swap        { src_code, tgt_code, src_text, tgt_text }
  │  HTTP GET  → /languages
  ▼
backend.py  (Flask)
  │  validates inputs
  │  resolves language codes → labels
  │  calls:  call_translation_api(text, src, tgt)
  │           call_tts_api(text, lang)
  ▼
api.py
  │  reads:  GOOGLE_API_KEY from .env
  │  POST → https://translation.googleapis.com/language/translate/v2
  │  gTTS → Google TTS (no key needed)
  ▼
Google Cloud Translation API  +  gTTS
```

---

## Configuration

| Variable        | File      | Required | Default              | Description                          |
|-----------------|-----------|----------|----------------------|--------------------------------------|
| `GOOGLE_API_KEY`| `.env`    | ✅ Yes   | —                    | Google Cloud Translation API key     |
| `BACKEND_URL`   | `.env`    | No       | `http://localhost:5000` | Flask server URL (frontend uses this) |
| `FLASK_RUN_PORT`| `.env`    | No       | `5000`               | Port for Flask server                |
| `FLASK_DEBUG`   | `.env`    | No       | `false`              | Enable Flask debug mode              |

---

## Swapping the Translation Provider

All API logic lives in `api.py`. To replace Google Cloud with another provider, only edit `call_translation_api()` — `backend.py` and `frontend.py` stay unchanged.

```python
# Example: DeepL
import deepl
translator = deepl.Translator(os.getenv("DEEPL_API_KEY"))
result = translator.translate_text(text, target_lang=target_lang)

# Example: Azure Translator
# POST to https://api.cognitive.microsofttranslator.com/translate
```

---

## Requirements

```
streamlit==1.35.0
requests==2.32.3
python-dotenv==1.0.1
gTTS==2.5.1
flask==3.0.3
flask-cors==4.0.1
```
