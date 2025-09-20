import os
import json
import time
import streamlit as st
import streamlit.components.v1 as components
from google import genai
from deep_translator import GoogleTranslator
from gtts import gTTS

# ================================
# Load Gemini API Key from Streamlit secrets
# ================================
gemini_key = st.secrets.get("GEMINI_API_KEY", None)

if not gemini_key:
    st.error("⚠ GEMINI_API_KEY not found in Streamlit secrets.")
    st.stop()

# Setup Gemini client
client = genai.Client(api_key=gemini_key)
PRIMARY_MODEL = "gemini-2.5-flash"
BACKUP_MODEL = "gemini-1.5-flash"

# ================================
# Load FAQs
# ================================
with open("faqs.json", "r", encoding="utf-8") as f:
    faqs = json.load(f)

def find_answer_from_faqs(user_query: str):
    user_query = user_query.lower()
    for disease, entry in faqs.items():
        for keyword in entry.get("keywords", []):
            if keyword in user_query:
                return entry["info"]
    return None

# ================================
# Gemini Query with Retry
# ================================
def fetch_from_gemini(user_query: str, retries=3):
    prompt = f"""
You are a health assistant. The user asked: {user_query}

Respond in clear, concise English with reliable health info 
about causes, prevention, and remedies if it's disease-related. 
If it's not health-related, politely say so.
"""
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model=PRIMARY_MODEL,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            if "503" in str(e) and attempt < retries - 1:
                time.sleep(2)
                continue
            try:
                response = client.models.generate_content(
                    model=BACKUP_MODEL,
                    contents=prompt
                )
                return response.text.strip()
            except Exception as e2:
                return f"⚠ Error fetching from Gemini: {str(e2)}"
    return "⚠ Could not fetch response from Gemini."

# ================================
# Translator
# ================================
def translate_to_language(text, lang_code):
    try:
        return GoogleTranslator(source="en", target=lang_code).translate(text)
    except:
        return text

# ================================
# Streamlit UI
# ================================
st.set_page_config(page_title="HealthLingo", page_icon="💬")

# Global styles
st.markdown("""
    <style>
        body {
            background-color: #0d0d0d;
        }
        .stApp {
            background-color: #0d0d0d;
        }
        .navbar {
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            justify-content: space-between;
            background: linear-gradient(90deg, #00b09b, #2193b0);
            padding: 12px 20px;
            border-radius: 10px;
            box-shadow: 0px 3px 6px rgba(0,0,0,0.3);
            position: sticky;
            top: 0;
            z-index: 1000;
        }
        .navbar img {
            height: 40px;
            margin-right: 10px;
        }
        .navbar .logo-text {
            font-size: 22px;
            font-weight: bold;
            color: white;
            text-shadow: 0 0 8px #00ffcc;
        }
        .navbar-links {
            display: flex;
            flex-wrap: wrap;
        }
        .navbar-links a {
            margin: 4px 8px;
            text-decoration: none;
            font-size: 16px;
            font-weight: 500;
            color: white;
            transition: 0.3s;
        }
        .navbar-links a:hover {
            color: yellow;
        }
    </style>

    <div class="navbar">
        <div style="display:flex; align-items:center;">
            <img src="https://img.icons8.com/color/96/medical-doctor.png" alt="HealthLingo Logo">
            <span class="logo-text">HealthLingo</span>
        </div>
        <div class="navbar-links">
            <a href="#">Home</a>
            <a href="#">FAQs</a>
            <a href="#">About</a>
            <a href="#">Contact</a>
        </div>
    </div>
""", unsafe_allow_html=True)

# Heading
st.markdown(
    "<h2 style='text-align:center; margin-top:20px;'>"
    "<span style='color:green;'>Health</span>"
    "<span style='color:blue;'>Lingo</span> – Your AI Health Assistant</h2>",
    unsafe_allow_html=True
)

# Clear chat button
if st.button("🗑 Clear Chat"):
    st.session_state.messages = []

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f"<div style='display:flex; justify-content:flex-end; margin:5px;'>"
            f"<div style='background-color:#003366; color:white; padding:10px; border-radius:15px; max-width:70%; "
            f"box-shadow:0px 1px 3px rgba(0,0,0,0.3); white-space:pre-wrap;'>🧑 {msg['content']}</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div style='display:flex; justify-content:flex-start; margin:5px;'>"
            f"<div style='background-color:#000000; color:white; padding:10px; border-radius:15px; max-width:70%; "
            f"box-shadow:0px 1px 3px rgba(0,0,0,0.3); white-space:pre-wrap;'>🤖 {msg['content']}</div></div>",
            unsafe_allow_html=True,
        )

# ================================
# Voice Input (Web Speech API)
# ================================
st.markdown("### 🎤 Voice Input")
components.html("""
    <button id="start-btn">🎤 Speak</button>
    <p id="result"></p>
    <script>
        var recognition = new(window.SpeechRecognition || window.webkitSpeechRecognition)();
        recognition.lang = "en-US";
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        document.getElementById("start-btn").onclick = function() {
            recognition.start();
        };

        recognition.onresult = function(event) {
            var transcript = event.results[0][0].transcript;
            var resultElement = document.getElementById("result");
            resultElement.innerHTML = "You said: " + transcript;

            // Send transcript back to Streamlit input
            const streamlitDoc = window.parent.document;
            const textarea = streamlitDoc.querySelector('textarea');
            if (textarea) {
                textarea.value = transcript;
                textarea.dispatchEvent(new Event('input', { bubbles: true }));
            }
        };
    </script>
""", height=120)

# ================================
# Text Input
# ================================
user_input = st.chat_input("Ask me about any disease, symptoms, or prevention...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    # 1. Check FAQs
    answer_en = find_answer_from_faqs(user_input)

    # 2. If not found, use Gemini
    if not answer_en:
        answer_en = fetch_from_gemini(user_input)

    # 3. Fallback if Gemini fails
    if not answer_en or "Error" in answer_en:
        answer_en = find_answer_from_faqs(user_input) or "Sorry, I cannot fetch this right now."

    # 4. Translate to Hindi
    answer_hi = translate_to_language(answer_en, "hi")

    # Final bot reply
    bot_reply = f"*English:* {answer_en}\n\n🌍 *Hindi:* {answer_hi}"
    st.session_state.messages.append({"role": "bot", "content": bot_reply})

    # 5. Voice reply with gTTS
    try:
        tts = gTTS(answer_en)
        tts.save("reply.mp3")
        audio_file = open("reply.mp3", "rb")
        st.audio(audio_file.read(), format="audio/mp3")
    except Exception as e:
        st.warning(f"Audio reply failed: {e}")

    st.rerun()


