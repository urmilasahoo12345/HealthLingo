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
# Gemini Query
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

# ================================
# Navbar with Hamburger Menu
# ================================
st.markdown("""
<style>
/* Navbar styling */
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

/* Logo */
.navbar img { height: 35px; margin-right: 10px; }
.logo-text { font-size: 20px; font-weight: bold; color: white; font-family: 'Segoe UI', sans-serif; }

/* Hamburger icon */
.menu-icon {
    font-size: 26px;
    cursor: pointer;
    color: white;
    transition: transform 0.3s ease;
}
.menu-icon:hover { transform: rotate(90deg); }

/* Dropdown menu */
.dropdown {
    display: none;
    position: absolute;
    right: 20px;
    top: 60px;
    background: white;
    border-radius: 8px;
    box-shadow: 0px 4px 10px rgba(0,0,0,0.2);
    padding: 10px;
}
.dropdown a {
    display: flex;
    align-items: center;
    padding: 8px;
    text-decoration: none;
    color: black;
    transition: background 0.3s;
}
.dropdown a:hover { background: #f0f0f0; border-radius: 6px; }

/* Chat bubble animation */
.chat-bubble {
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.chat-bubble:hover {
    transform: scale(1.02);
    box-shadow: 0px 4px 10px rgba(0,0,0,0.4);
}
</style>

<div class="navbar">
    <div style="display:flex; align-items:center;">
        <img src="https://img.icons8.com/color/96/medical-doctor.png" alt="HealthLingo Logo">
        <span class="logo-text">HealthLingo</span>
    </div>
    <div>
        <span class="menu-icon" onclick="toggleMenu()">☰</span>
        <div id="menuDropdown" class="dropdown">
            <a href="#"><img src="https://img.icons8.com/ios-filled/24/home.png"> Home</a>
            <a href="#"><img src="https://img.icons8.com/ios-filled/24/help.png"> FAQs</a>
            <a href="#"><img src="https://img.icons8.com/ios-filled/24/info.png"> About</a>
            <a href="#"><img src="https://img.icons8.com/ios-filled/24/contacts.png"> Contact</a>
        </div>
    </div>
</div>

<script>
function toggleMenu() {
    var menu = document.getElementById("menuDropdown");
    if (menu.style.display === "block") {
        menu.style.display = "none";
    } else {
        menu.style.display = "block";
    }
}
</script>
""", unsafe_allow_html=True)

# ================================
# Heading
# ================================
st.markdown(
    "<h2 style='text-align:center; margin-top:20px;'>"
    "<span style='color:green;'>Health</span>"
    "<span style='color:blue;'>Lingo</span> – Your AI Health Assistant</h2>",
    unsafe_allow_html=True
)

# ================================
# Clear Chat
# ================================
if st.button("🗑 Clear Chat"):
    st.session_state.messages = []

if "messages" not in st.session_state:
    st.session_state.messages = []

# ================================
# Container for chat messages
# ================================
chat_container = st.container()

# Display previous chat messages
with chat_container:
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(
                f"<div style='display:flex; justify-content:flex-end; margin:5px;'>"
                f"<div class='chat-bubble' style='background-color:#003366; color:white; padding:10px; border-radius:15px; max-width:70%; "
                f"white-space:pre-wrap;'>🧑 {msg['content']}</div></div>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<div style='display:flex; justify-content:flex-start; margin:5px;'>"
                f"<div class='chat-bubble' style='background-color:#000000; color:white; padding:10px; border-radius:15px; max-width:70%; "
                f"white-space:pre-wrap;'>🤖 {msg['content']}</div></div>",
                unsafe_allow_html=True,
            )

# ================================
# Input Box
# ================================
user_input = st.chat_input("Ask me about any disease, symptoms, or prevention...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with chat_container:
        st.markdown(
            f"<div style='display:flex; justify-content:flex-end; margin:5px;'>"
            f"<div class='chat-bubble' style='background-color:#003366; color:white; padding:10px; border-radius:15px; max-width:70%; "
            f"white-space:pre-wrap;'>🧑 {user_input}</div></div>",
            unsafe_allow_html=True,
        )

    answer_en = find_answer_from_faqs(user_input) or fetch_from_gemini(user_input)
    if not answer_en or "Error" in answer_en:
        answer_en = "Sorry, I cannot fetch this right now."
    answer_hi = translate_to_language(answer_en, "hi")
    bot_reply = f"*English:* {answer_en}\n\n🌍 *Hindi:* {answer_hi}"
    st.session_state.messages.append({"role": "bot", "content": bot_reply})

    with chat_container:
        st.markdown(
            f"<div style='display:flex; justify-content:flex-start; margin:5px;'>"
            f"<div class='chat-bubble' style='background-color:#000000; color:white; padding:10px; border-radius:15px; max-width:70%; "
            f"white-space:pre-wrap;'>🤖 {bot_reply}</div></div>",
            unsafe_allow_html=True,
        )

    components.html(f"""
        <script>
        var msg = new SpeechSynthesisUtterance(`{answer_en.replace('`','')}`);
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(msg);
        </script>
    """, height=0)
