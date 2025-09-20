import os
import json
import time
import streamlit as st
from dotenv import load_dotenv
from google import genai
from deep_translator import GoogleTranslator
import streamlit.components.v1 as components

# ================================
# Load environment variables
# ================================
load_dotenv()
gemini_key = os.getenv("GEMINI_API_KEY")

if not gemini_key:
    st.error("⚠️ GEMINI_API_KEY not found in .env file or Streamlit secrets.")
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
                return f"⚠️ Error fetching from Gemini: {str(e2)}"
    return "⚠️ Could not fetch response from Gemini."

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
st.set_page_config(page_title="HealthLingo", page_icon="💬", layout="wide")

# ================================
# Navbar
# ================================
st.markdown("""
<style>
.navbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    background: linear-gradient(90deg, #00b09b, #96c93d, #2193b0, #6dd5ed);
    padding: 10px 15px;
    border-radius: 10px;
    box-shadow: 0px 3px 6px rgba(0,0,0,0.2);
    position: sticky;
    top: 0;
    z-index: 1000;
}
.navbar img { height: 40px; margin-right: 10px; }
.navbar .logo-text { font-size: 22px; font-weight: bold; color: white; font-family: 'Segoe UI', sans-serif; }
.navbar-links { display: flex; flex-wrap: wrap; margin-top: 5px; }
.navbar-links a { margin: 5px 8px; text-decoration: none; font-size: 16px; font-weight: 500; color: white; transition: 0.3s; }
.navbar-links a:hover { color: yellow; }
@media (max-width: 600px){ .navbar-links { width: 100%; justify-content: center; } }
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

# Title below navbar
st.markdown(
    "<h2 style='text-align:center; margin-top:10px;'>"
    "<span style='color:green;'>Health</span>"
    "<span style='color:blue;'>Lingo</span> – Your AI Health Assistant</h2>",
    unsafe_allow_html=True
)

# Clear chat
if st.button("🗑 Clear Chat"):
    st.session_state.messages = []

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat bubbles with speaker button for bot replies
for idx, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        st.markdown(
            f"<div style='display:flex; justify-content:flex-end; margin:5px;'>"
            f"<div style='background-color:#003366; color:white; padding:10px; border-radius:20px; max-width:70%; "
            f"box-shadow:0px 1px 3px rgba(0,0,0,0.3); white-space:pre-wrap;'>🧑 {msg['content']}</div></div>",
            unsafe_allow_html=True,
        )
    else:
        # Add speaker button next to bot message
        st.markdown(
            f"""
            <div style='display:flex; justify-content:flex-start; align-items:center; margin:5px;'>
                <div style='background-color:#000000; color:white; padding:10px; border-radius:20px; max-width:70%;
                            box-shadow:0px 1px 3px rgba(0,0,0,0.3); white-space:pre-wrap;'>🤖 {msg['content']}</div>
                <button onclick="var msg=new SpeechSynthesisUtterance(`{msg['content'].replace('`','')}`); window.speechSynthesis.speak(msg);" 
                        style='margin-left:5px; cursor:pointer; background:#333; color:white; border:none; border-radius:5px; padding:5px;'>🔊</button>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ================================
# Fixed bottom input
# ================================
st.markdown("""
<style>
.stChatInput {position: fixed; bottom: 0; width: 100%; max-width: 600px; left: 50%; transform: translateX(-50%);}
</style>
""", unsafe_allow_html=True)

user_input = st.text_input("Type your message...", key="input_bar")

if user_input:
    # Append user input and process bot reply
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Check FAQs
    answer_en = find_answer_from_faqs(user_input)

    # Use Gemini if not found
    if not answer_en:
        answer_en = fetch_from_gemini(user_input)

    if not answer_en or "Error" in answer_en:
        answer_en = find_answer_from_faqs(user_input) or "Sorry, I cannot fetch this right now."

    # Translate to Hindi
    answer_hi = translate_to_language(answer_en, "hi")

    # Bot reply
    bot_reply = f"**English:** {answer_en}\n\n🌍 **Hindi:** {answer_hi}"
    st.session_state.messages.append({"role": "bot", "content": bot_reply})

    # Text-to-speech
    bot_reply_js = f"""
    <script>
    var msg = new SpeechSynthesisUtterance("{answer_en.replace('"','\\"')}");
    window.speechSynthesis.speak(msg);
    </script>
    """
    components.html(bot_reply_js, height=0)
    st.experimental_rerun()





