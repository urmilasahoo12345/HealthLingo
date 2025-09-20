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
st.set_page_config(page_title="HealthLingo", page_icon="💬")

# Title
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

# Display chat bubbles
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
# Floating input bar with mic
# ================================
voice_html = """
<div style="position:fixed; bottom:10px; width:100%; display:flex; justify-content:center; z-index:1000;">
    <div style="display:flex; width:95%; max-width:600px; background-color: rgba(0,0,0,0.7); border-radius:25px; padding:5px; align-items:center;">
        <input type="text" id="chat_input" placeholder="Ask about any disease..." 
               style="flex:1; border:none; background:transparent; color:white; padding:10px; font-size:16px; border-radius:20px;">
        <button id="micBtn" style="background:none; border:none; color:white; font-size:24px; margin-left:5px; cursor:pointer;">🎤</button>
    </div>
</div>

<script>
var recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
recognition.lang = "en-US";
recognition.interimResults = false;
recognition.maxAlternatives = 1;

document.getElementById("micBtn").onclick = function() {
    recognition.start();
};

recognition.onresult = function(event) {
    var transcript = event.results[0][0].transcript;
    const inputBox = document.getElementById("chat_input");
    inputBox.value = transcript;

    // Send transcript to Streamlit
    window.parent.postMessage({isStreamlitMessage:true, type:'VOICE_INPUT', text: transcript}, "*");
};

// Enter key triggers submit
document.getElementById("chat_input").addEventListener("keydown", function(e){
    if(e.key === "Enter"){
        window.parent.postMessage({isStreamlitMessage:true, type:'VOICE_INPUT', text: this.value}, "*");
        this.value = "";
    }
});
</script>
"""

components.html(voice_html, height=80)

# ================================
# Capture voice input from JS
# ================================
if "voice_input" not in st.session_state:
    st.session_state.voice_input = ""

components.html("""
<script>
window.addEventListener("message", (event) => {
    if(event.data?.type === "VOICE_INPUT"){
        const value = event.data.text;
        const inputBox = window.parent.document.querySelector("textarea");
        if(inputBox){
            inputBox.value = value;
            inputBox.dispatchEvent(new Event("input", { bubbles: true }));
        }
    }
});
</script>
""", height=0)


