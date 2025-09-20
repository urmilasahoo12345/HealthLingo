import os
import json
import time
import streamlit as st
from google import genai
from deep_translator import GoogleTranslator
import streamlit.components.v1 as components

# ================================
# Load Gemini API Key from Streamlit secrets
# ================================
gemini_key = os.getenv("GEMINI_API_KEY")

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

# Navbar
st.markdown("""
    <style>
        .navbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: linear-gradient(90deg, #00b09b, #96c93d, #2193b0, #6dd5ed);
            padding: 12px 20px;
            border-radius: 10px;
            box-shadow: 0px 3px 6px rgba(0,0,0,0.2);
            position: sticky;
            top: 0;
            z-index: 1000;
        }
        .navbar img {height: 40px; margin-right: 10px;}
        .navbar .logo-text {font-size: 22px; font-weight: bold; color: white; font-family: 'Segoe UI', sans-serif;}
        .navbar-links a {
            margin: 0 8px;
            text-decoration: none;
            font-size: 14px;
            font-weight: 500;
            color: white;
            transition: 0.3s;
        }
        .navbar-links a:hover {color: yellow;}
        @media(max-width:600px){
            .navbar-links {display:flex; flex-wrap:wrap;}
            .navbar-links a {margin:4px;}
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

# Clear chat
if st.button("🗑 Clear Chat"):
    st.session_state.messages = []

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history with WhatsApp-style bubbles
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
# Voice + Text input
# ================================
st.markdown("""
    <style>
        .mic-container {display:flex; align-items:center; justify-content:center;}
        .mic-button {
            background-color:#2193b0;
            color:white;
            border:none;
            border-radius:50%;
            width:40px;
            height:40px;
            font-size:18px;
            margin-left:10px;
            cursor:pointer;
            box-shadow:0 0 8px #00f5ff;
        }
        .mic-button:hover {background-color:#1a7c94;}
    </style>
""", unsafe_allow_html=True)

col1, col2 = st.columns([9,1])
with col1:
    user_input = st.chat_input("Ask me about any disease, symptoms, or prevention...")

with col2:
    mic_html = """
    <div class="mic-container">
        <button id="micBtn" class="mic-button">🎤</button>
    </div>
    <script>
        var recognition = new(window.SpeechRecognition || window.webkitSpeechRecognition)();
        recognition.lang = "en-US";
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;

        document.getElementById("micBtn").onclick = function() {
            recognition.start();
        };

        recognition.onresult = function(event) {
            var transcript = event.results[0][0].transcript;
            const streamlitDoc = window.parent.document;
            const input = streamlitDoc.querySelector('textarea');
            if (input) {
                input.value = transcript;
                input.dispatchEvent(new Event('input', { bubbles: true }));
                const enterEvent = new KeyboardEvent("keydown", {bubbles: true, cancelable: true, keyCode: 13});
                input.dispatchEvent(enterEvent);
            }
        };
    </script>
    """
    components.html(mic_html, height=60)

# ================================
# Process user input + voice reply
# ================================
if user_input:
    st.session_state.messages.append({"role":"user","content":user_input})

    # FAQs first
    answer_en = find_answer_from_faqs(user_input)
    if not answer_en:
        answer_en = fetch_from_gemini(user_input)
    if not answer_en or "Error" in answer_en:
        answer_en = find_answer_from_faqs(user_input) or "Sorry, I cannot fetch this right now."

    # Translate to Hindi
    answer_hi = translate_to_language(answer_en, "hi")

    bot_reply = f"**English:** {answer_en}\n\n🌍 **Hindi:** {answer_hi}"
    st.session_state.messages.append({"role":"bot","content":bot_reply})

    # ================================
    # Voice reply
    # ================================
    tts_html = f"""
    <script>
        var msg = new SpeechSynthesisUtterance();
        msg.text = `{answer_en}`;
        msg.lang = 'en-US';
        window.speechSynthesis.speak(msg);
    </script>
    """
    components.html(tts_html, height=0)

    st.rerun()



