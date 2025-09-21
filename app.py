# app.py
import os
import json
import time
import streamlit as st
from google import genai
from deep_translator import GoogleTranslator
import streamlit.components.v1 as components

# Optional: try to import langdetect (better detection).
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
# Load FAQs
# ================================
FAQ_PATH = "faqs.json"
if not os.path.exists(FAQ_PATH):
    faqs = {}
else:
    with open(FAQ_PATH, "r", encoding="utf-8") as f:
        faqs = json.load(f)


def find_answer_from_faqs(user_query: str):
    q = user_query.lower()
    for disease, entry in faqs.items():
        keywords = entry.get("keywords", []) if isinstance(entry, dict) else []
        info = entry.get("info") if isinstance(entry, dict) else entry
        for kw in keywords:
            if kw.lower() in q:
                return info
    return None


# ================================
# Gemini Query
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
            return response.text.strip()
        except Exception as e:
            if "503" in str(e) and attempt < retries - 1:
                time.sleep(1.5)
                continue
            try:
                response = client.models.generate_content(
                    model=BACKUP_MODEL,
                    contents=prompt,
                )
                return response.text.strip()
            except Exception as e2:
                return f"⚠ Error fetching from Gemini: {str(e2)}"
    return "⚠ Could not fetch response from Gemini."


# ================================
# Language detection helpers
# ================================
def detect_language(text: str) -> str:
    """Detect language code (ISO 639-1).
    Fallback and default is always English."""
    text = (text or "").strip()
    if not text:
        return "en"

    # ✅ Force English if majority characters are ASCII
    ascii_letters = sum(1 for c in text if c.isascii() and c.isalpha())
    if ascii_letters >= len(text) / 2:
        return "en"

    # Try langdetect
    if ld_detect:
        try:
            lang = ld_detect(text).lower()
            if lang in ["en", "hi", "or", "bn", "gu", "ta", "te", "kn", "ml", "ar", "ru", "es"]:
                return lang
            return "en"
        except Exception:
            pass

    # Heuristics for Indian scripts
    for ch in text:
        o = ord(ch)
        if 0x0900 <= o <= 0x097F:  # Devanagari
            return "hi"
        if 0x0980 <= o <= 0x09FF:  # Bengali
            return "bn"
        if 0x0B00 <= o <= 0x0B7F:  # Odia
            return "or"
        if 0x0A80 <= o <= 0x0AFF:  # Gujarati
            return "gu"
        if 0x0B80 <= o <= 0x0BFF:  # Tamil
            return "ta"
        if 0x0C00 <= o <= 0x0C7F:  # Telugu
            return "te"
        if 0x0C80 <= o <= 0x0CFF:  # Kannada
            return "kn"
        if 0x0D00 <= o <= 0x0D7F:  # Malayalam
            return "ml"
        if 0x0600 <= o <= 0x06FF:  # Arabic
            return "ar"
        if 0x0400 <= o <= 0x04FF:  # Cyrillic
            return "ru"

    return "en"


def tts_locale_for(lang_code: str) -> str:
    mapping = {
        "hi": "hi-IN",
        "or": "or-IN",
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
    return mapping.get(lang_code, "en-US")


# ================================
# Translation helper
# ================================
def translate_text(text: str, target_lang: str) -> str:
    if not text:
        return text
    target_lang = (target_lang or "en").lower()
    if target_lang in ("en", "eng", "english"):
        return text
    try:
        return GoogleTranslator(source="auto", target=target_lang).translate(text)
    except Exception:
        try:
            return GoogleTranslator(source="en", target=target_lang).translate(text)
        except Exception:
            return text


# ================================
# Streamlit UI
# ================================
st.set_page_config(page_title="HealthLingo", page_icon="💬", layout="wide")

# Navbar
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

# Clear chat
if st.button("🗑 Clear Chat"):
    st.session_state.messages = []

if "messages" not in st.session_state:
    st.session_state.messages = []

# Input
user_input = st.chat_input("Ask me about any disease, symptoms, or prevention...")

bot_reply_text_for_tts = None
tts_lang_for_reply = "en-US"

if user_input:
    detected_lang = detect_language(user_input)

    st.session_state.messages.append({"role": "user", "content": user_input})

    answer_en = find_answer_from_faqs(user_input) or fetch_from_gemini(user_input)
    if not answer_en:
        answer_en = "Sorry, I cannot fetch this right now."

    # Translate only if NOT English
    translated_answer = (
        answer_en if detected_lang == "en" else translate_text(answer_en, detected_lang)
    )

    st.session_state.messages.append({"role": "bot", "content": translated_answer})
    bot_reply_text_for_tts = translated_answer
    tts_lang_for_reply = tts_locale_for(detected_lang)

# Render chat
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f"<div style='display:flex; justify-content:flex-end; margin:6px;'>"
            f"<div class='chat-bubble' style='background:#003366; color:#fff; padding:10px; border-radius:15px; "
            f"max-width:75%; white-space:pre-wrap;'>🧑 {msg['content']}</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div style='display:flex; justify-content:flex-start; margin:6px;'>"
            f"<div class='chat-bubble' style='background:#000; color:#fff; padding:10px; border-radius:15px; "
            f"max-width:75%; white-space:pre-wrap;'>🤖 {msg['content']}</div></div>",
            unsafe_allow_html=True,
        )

# TTS
if bot_reply_text_for_tts:
    import json as _json
    safe_text = _json.dumps(bot_reply_text_for_tts)
    safe_lang = tts_lang_for_reply.replace('"', "")
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

