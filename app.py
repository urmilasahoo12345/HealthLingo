import os
import json
import time
import streamlit as st
from google import genai
from deep_translator import GoogleTranslator
import streamlit.components.v1 as components

# ================================
# Load Gemini API Key
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
                contents=prompt,
            )
            return response.text.strip()
        except Exception as e:
            if "503" in str(e) and attempt < retries - 1:
                time.sleep(2)
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
# Translator
# ================================
def translate_to_language(text, lang_code):
    try:
        return GoogleTranslator(source="en", target=lang_code).translate(text)
    except:
        return text


# ================================
# Streamlit Page Config
# ================================
st.set_page_config(page_title="HealthLingo", page_icon="💬", layout="wide")

# ================================
# Navbar with dropdown menu
# ================================
st.markdown(
    """
    <style>
        .navbar {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: linear-gradient(90deg, #00b09b, #96c93d, #2193b0, #6dd5ed);
            padding: 12px 20px;
            border-radius: 10px;
            box-shadow: 0px 3px 6px rgba(0,0,0,0.2);
            position: sticky;
            top: 0;
            z-index: 1000;
        }
        .navbar-left {
            display: flex;
            align-items: center;
        }
        .navbar-left img { height: 35px; margin-right: 10px; }
        .navbar-left .logo-text {
            font-size: 20px;
            font-weight: bold;
            color: white;
            font-family: 'Segoe UI', sans-serif;
        }
        .menu {
            position: relative;
            display: inline-block;
        }
        .menu-content {
            display: none;
            position: absolute;
            right: 0;
            background-color: white;
            min-width: 140px;
            border-radius: 8px;
            box-shadow: 0px 8px 16px rgba(0,0,0,0.2);
            padding: 10px;
            z-index: 1001;
        }
        .menu-content a {
            color: black;
            text-decoration: none;
            display: block;
            padding: 8px;
        }
        .menu-content a:hover {
            background-color: #f1f1f1;
        }
        .menu:hover .menu-content {
            display: block;
        }
    </style>

    <div class="navbar">
        <div class="navbar-left">
            <img src="https://img.icons8.com/color/96/medical-doctor.png" alt="HealthLingo Logo">
            <span class="logo-text">HealthLingo</span>
        </div>
        <div class="menu">
            <img src="https://img.icons8.com/ios-filled/50/menu--v1.png" alt="Menu" style="height:30px; cursor:pointer;">
            <div class="menu-content">
                <a href="#" title="Home">🏠 Home</a>
                <a href="#" title="FAQs">❓ FAQs</a>
                <a href="#" title="About">ℹ️ About</a>
                <a href="#" title="Contact">📞 Contact</a>
            </div>
        </div>
    </div>
""",
    unsafe_allow_html=True,
)

# Heading
st.markdown(
    "<h2 style='text-align:center; margin-top:20px;'>"
    "<span style='color:green;'>Health</span>"
    "<span style='color:blue;'>Lingo</span> – Your AI Health Assistant</h2>",
    unsafe_allow_html=True,
)

# ================================
# Clear Chat Button
# ================================
if st.button("🗑 Clear Chat"):
    st.session_state.messages = []

if "messages" not in st.session_state:
    st.session_state.messages = []

# ================================
# Input box
# ================================
user_input = st.chat_input("Ask me about any disease, symptoms, or prevention...")

bot_reply_text = None  # store latest bot reply (English only for TTS)

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    # 1. Check FAQs
    answer_en = find_answer_from_faqs(user_input)

    # 2. If not found, use Gemini
    if not answer_en:
        answer_en = fetch_from_gemini(user_input)

    # 3. Fallback if Gemini fails
    if not answer_en or "Error" in answer_en:
        answer_en = (
            find_answer_from_faqs(user_input) or "Sorry, I cannot fetch this right now."
        )

    # 4. Translate to Hindi
    answer_hi = translate_to_language(answer_en, "hi")

    # Final bot reply
    bot_reply_text = answer_en  # save for TTS
    bot_reply = f"*English:* {answer_en}\n\n🌍 *Hindi:* {answer_hi}"
    st.session_state.messages.append({"role": "bot", "content": bot_reply})

# ================================
# Display Chat Messages
# ================================
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f"<div style='display:flex; justify-content:flex-end; margin:5px; animation: fadeIn 0.5s;'>"
            f"<div style='background-color:#003366; color:white; padding:10px; border-radius:15px; max-width:70%; "
            f"box-shadow:0px 1px 3px rgba(0,0,0,0.3); white-space:pre-wrap;'>🧑 {msg['content']}</div></div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div style='display:flex; justify-content:flex-start; margin:5px; animation: fadeIn 0.5s;'>"
            f"<div style='background-color:#000000; color:white; padding:10px; border-radius:15px; max-width:70%; "
            f"box-shadow:0px 1px 3px rgba(0,0,0,0.3); white-space:pre-wrap;'>🤖 {msg['content']}</div></div>",
            unsafe_allow_html=True,
        )

# ================================
# Automatic TTS AFTER messages are displayed
# ================================
if bot_reply_text:
    components.html(
        f"""
        <script>
        var msg = new SpeechSynthesisUtterance(`{bot_reply_text.replace('`','')}`);
        window.speechSynthesis.cancel(); 
        window.speechSynthesis.speak(msg);
        </script>
    """,
        height=0,
    )
