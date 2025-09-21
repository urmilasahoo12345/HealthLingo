# app.py
import os
import json
import time
import streamlit as st
from google import genai
from deep_translator import GoogleTranslator
import streamlit.components.v1 as components

# Optional: try to import langdetect (better detection). If not present, we use heuristics.
try:
    from langdetect import detect as ld_detect
except Exception:
    ld_detect = None

# ================================
# Load Gemini API Key
# ================================
gemini_key = os.getenv("GEMINI_API_KEY")
if not gemini_key:
    st.error("⚠ GEMINI_API_KEY not found in environment / Streamlit secrets.")
    st.stop()

# Setup Gemini client
client = genai.Client(api_key=gemini_key)
PRIMARY_MODEL = "gemini-2.5-flash"
BACKUP_MODEL = "gemini-1.5-flash"

# ================================
# Load FAQs (local fallback knowledge)
# ================================
FAQ_PATH = "faqs.json"
if not os.path.exists(FAQ_PATH):
    faqs = {}
else:
    with open(FAQ_PATH, "r", encoding="utf-8") as f:
        faqs = json.load(f)


def find_answer_from_faqs(user_query: str):
    """Return faq info if any keyword matches (case-insensitive)."""
    q = user_query.lower()
    for disease, entry in faqs.items():
        keywords = entry.get("keywords", []) if isinstance(entry, dict) else []
        info = entry.get("info") if isinstance(entry, dict) else entry
        for kw in keywords:
            try:
                if kw.lower() in q:
                    return info
            except Exception:
                continue
    return None


# ================================
# Gemini Query with Retry
# ================================
def fetch_from_gemini(user_query: str, retries=2):
    prompt = f"""
You are a concise accurate health assistant. The user asked: {user_query}

Provide reliable, high-level information about causes, prevention, and remedies
(if disease-related), in clear English. If the question is not health-related,
politely say so.
"""
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=PRIMARY_MODEL,
                contents=prompt,
            )
            # The google genai response formats differ; we try to get a text payload
            # The code below expects a `.text` attribute (as in earlier code). If not, fallback to str(response).
            try:
                return response.text.strip()
            except Exception:
                return str(response).strip()
        except Exception as e:
            if "503" in str(e) and attempt < retries - 1:
                time.sleep(1.5)
                continue
            # Try backup model once
            try:
                response = client.models.generate_content(
                    model=BACKUP_MODEL,
                    contents=prompt,
                )
                try:
                    return response.text.strip()
                except Exception:
                    return str(response).strip()
            except Exception as e2:
                return f"⚠ Error fetching from Gemini: {str(e2)}"
    return "⚠ Could not fetch response from Gemini."


# ================================
# Language detection helpers
# ================================
def detect_language(text: str) -> str:
    """Detect language code (ISO 639-1) using langdetect if available,
    otherwise use Unicode-script heuristics for Indian languages and fallback to 'en'."""
    text = (text or "").strip()
    if not text:
        return "en"
    # 1) try langdetect
    if ld_detect:
        try:
            lang = ld_detect(text)
            if isinstance(lang, str) and len(lang) >= 2:
                return lang.lower()
        except Exception:
            pass

    # 2) heuristics based on Unicode script ranges
    for ch in text:
        o = ord(ch)
        # Devanagari (Hindi, Marathi, Nepali, Sanskrit)
        if 0x0900 <= o <= 0x097F:
            return "hi"
        # Bengali (Bengali / Assamese)
        if 0x0980 <= o <= 0x09FF:
            return "bn"
        # Oriya / Odia
        if 0x0B00 <= o <= 0x0B7F:
            return "or"
        # Gujarati
        if 0x0A80 <= o <= 0x0AFF:
            return "gu"
        # Tamil
        if 0x0B80 <= o <= 0x0BFF:
            return "ta"
        # Telugu
        if 0x0C00 <= o <= 0x0C7F:
            return "te"
        # Kannada
        if 0x0C80 <= o <= 0x0CFF:
            return "kn"
        # Malayalam
        if 0x0D00 <= o <= 0x0D7F:
            return "ml"
        # Arabic
        if 0x0600 <= o <= 0x06FF:
            return "ar"
        # Cyrillic (Russian, etc.)
        if 0x0400 <= o <= 0x04FF:
            return "ru"

    # 3) If majority ascii letters -> english
    ascii_letters = sum(1 for c in text if c.isascii() and c.isalpha())
    if ascii_letters >= len(text) / 2:
        return "en"

    # default fallback
    return "en"


def tts_locale_for(lang_code: str) -> str:
    """Map simple lang_code -> common speechSynthesis locale (best-effort)."""
    mapping = {
        "hi": "hi-IN",
        "or": "or-IN",  # Odia / Oriya
        "bn": "bn-IN",
        "te": "te-IN",
        "ta": "ta-IN",
        "kn": "kn-IN",
        "ml": "ml-IN",
        "gu": "gu-IN",
        "en": "en-US",
        "ar": "ar-SA",
        "ru": "ru-RU",
        "es": "es-ES",
    }
    return mapping.get(lang_code, lang_code)


# ================================
# Translation helper
# ================================
def translate_text(text: str, target_lang: str) -> str:
    """Translate text into target_lang using deep_translator.GoogleTranslator.
    If target_lang is 'en' or None, returns text unchanged."""
    if not text:
        return text
    target_lang = (target_lang or "en").lower()
    if target_lang in ("en", "eng", "english"):
        return text
    try:
        # use source='auto' to let Google detect source
        return GoogleTranslator(source="auto", target=target_lang).translate(text)
    except Exception:
        # fallback: try with source='en' if original is english
        try:
            return GoogleTranslator(source="en", target=target_lang).translate(text)
        except Exception:
            # last resort, return original English text
            return text


# ================================
# Streamlit UI config
# ================================
st.set_page_config(page_title="HealthLingo", page_icon="💬", layout="wide")

# Navbar (icon menu)
st.markdown(
    """
    <style>
      .navbar {
        display:flex; justify-content:space-between; align-items:center;
        background: linear-gradient(90deg,#00b09b,#96c93d,#2193b0,#6dd5ed);
        padding:12px 20px; border-radius:10px; box-shadow:0 3px 6px rgba(0,0,0,0.2);
        position: sticky; top: 0; z-index: 1000;
      }
      .navbar-left { display:flex; align-items:center; }
      .navbar-left img { height:35px; margin-right:10px; }
      .logo-text { font-size:20px; font-weight:bold; color:blue; font-family:'Segoe UI',sans-serif; }
      .menu { position:relative; display:inline-block; }
      .menu-content { display:none; position:absolute; right:0; background:#fff; min-width:140px;
                      border-radius:8px; box-shadow:0 8px 16px rgba(0,0,0,0.2); padding:10px; z-index:1001; }
      .menu-content a { color:black; text-decoration:none; display:block; padding:8px; }
      .menu-content a:hover { background:#f1f1f1; }
      .menu:hover .menu-content { display:block; }
      /* chat bubble animation */
      .chat-bubble { transition: transform .12s ease, box-shadow .12s ease; }
      .chat-bubble:hover { transform: scale(1.02); box-shadow: 0 4px 12px rgba(0,0,0,0.25); }
    </style>
    <div class="navbar">
      <div class="navbar-left">
        <img src="https://img.icons8.com/color/96/medical-doctor.png" alt="logo">
        <span class="logo-text">HealthLingo</span>
      </div>
      <div class="menu">
        <img src="https://img.icons8.com/ios-filled/50/menu--v1.png" style="height:30px; cursor:pointer;">
        <div class="menu-content">
          <a href="#">🏠 Home</a>
          <a href="#">❓ FAQs</a>
          <a href="#">ℹ️ About</a>
          <a href="#">📞 Contact</a>
        </div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    "<h2 style='text-align:center; margin-top:18px;'>Your AI Health Assistant</h2>",
    unsafe_allow_html=True,
)

# Clear chat button
if st.button("🗑 Clear Chat"):
    st.session_state.messages = []

if "messages" not in st.session_state:
    st.session_state.messages = []

# ---------- Input ----------
user_input = st.chat_input("Ask me about any disease, symptoms, or prevention...")

# We'll keep the English bot answer (answer_en) for translation & TTS
bot_reply_text_for_tts = None
tts_lang_for_reply = "en-US"

if user_input:
    # 1) detect user language (fallbacks present)
    detected_lang = detect_language(user_input)

    # Immediately append the user's message so it shows now
    st.session_state.messages.append({"role": "user", "content": user_input})

    # 2) first check local FAQs
    answer_en = find_answer_from_faqs(user_input)

    # 3) else fetch from Gemini (English)
    if not answer_en:
        answer_en = fetch_from_gemini(user_input)

    # 4) fallback if Gemini fails
    if not answer_en or "Error" in answer_en:
        answer_en = find_answer_from_faqs(user_input) or "Sorry, I cannot fetch this right now."

    # 5) Translate answer into user's language if needed
    # If detected_lang is English, keep English
    translated_answer = (
        answer_en if detected_lang in ("en", "eng") else translate_text(answer_en, detected_lang)
    )

    # 6) compose displayed bot reply (we'll show translated text; you can optionally also show English)
    # If you want bilingual display, append English in parentheses or as a second line.
    display_bot = translated_answer

    # Save bot message and TTS parameters
    st.session_state.messages.append({"role": "bot", "content": display_bot})
    bot_reply_text_for_tts = translated_answer  # speak in user language
    tts_lang_for_reply = tts_locale_for(detected_lang)

# ---------- Render chat history ----------
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f"<div style='display:flex; justify-content:flex-end; margin:6px;'>"
            f"<div class='chat-bubble' style='background:#003366; color:#fff; padding:10px; border-radius:15px; "
            f"max-width:75%; box-shadow:0 1px 3px rgba(0,0,0,0.2); white-space:pre-wrap;'>🧑 {msg['content']}</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div style='display:flex; justify-content:flex-start; margin:6px;'>"
            f"<div class='chat-bubble' style='background:#000; color:#fff; padding:10px; border-radius:15px; "
            f"max-width:75%; box-shadow:0 1px 3px rgba(0,0,0,0.2); white-space:pre-wrap;'>🤖 {msg['content']}</div></div>",
            unsafe_allow_html=True,
        )

# ---------- Run TTS AFTER rendering (only for the latest reply in this run) ----------
if bot_reply_text_for_tts:
    # Use json.dumps to safely escape text into JS string
    import json as _json

    safe_text = _json.dumps(bot_reply_text_for_tts)
    safe_lang = tts_lang_for_reply.replace('"', "")  # just in case

    components.html(
        f"""
        <script>
        var text = {safe_text};
        var msg = new SpeechSynthesisUtterance(text);
        msg.lang = "{safe_lang}";
        try {{
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(msg);
        }} catch(e) {{
            console.warn("TTS error", e);
        }}
        </script>
        """,
        height=0,
    )

