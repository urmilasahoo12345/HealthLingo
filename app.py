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

def fetch_from_gemini(user_query: str, retries=3):
    prompt = f"You are a health assistant. The user asked: {user_query}\nRespond concisely."
    for attempt in range(retries):
        try:
            response = client.models.generate_content(model=PRIMARY_MODEL, contents=prompt)
            return response.text.strip()
        except Exception as e:
            if "503" in str(e) and attempt < retries - 1:
                time.sleep(2)
                continue
            try:
                response = client.models.generate_content(model=BACKUP_MODEL, contents=prompt)
                return response.text.strip()
            except:
                return "⚠️ Error fetching from Gemini."
    return "⚠️ Could not fetch response from Gemini."

def translate_to_language(text, lang_code):
    try:
        return GoogleTranslator(source="en", target=lang_code).translate(text)
    except:
        return text

# ================================
# Streamlit UI
# ================================
st.set_page_config(page_title="HealthLingo", page_icon="💬", layout="wide")

# Navbar
st.markdown("""
<div style="background: linear-gradient(90deg, #00b09b, #96c93d, #2193b0, #6dd5ed); padding:10px; border-radius:10px;">
    <span style="font-size:22px; font-weight:bold; color:white;">HealthLingo</span>
</div>
""", unsafe_allow_html=True)

# Title
st.markdown("<h2 style='text-align:center;'><span style='color:green;'>Health</span><span style='color:blue;'>Lingo</span> – Your AI Health Assistant</h2>", unsafe_allow_html=True)

# Clear chat
if st.button("🗑 Clear Chat"):
    st.session_state.messages = []

if "messages" not in st.session_state:
    st.session_state.messages = []

# Chat display
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f"<div style='display:flex; justify-content:flex-end; margin:5px;'>"
                    f"<div style='background-color:#003366; color:white; padding:10px; border-radius:20px; max-width:70%;'>🧑 {msg['content']}</div></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style='display:flex; justify-content:flex-start; align-items:center; margin:5px;'>
            <div style='background-color:#000; color:white; padding:10px; border-radius:20px; max-width:70%;'>🤖 {msg['content']}</div>
            <button onclick="var msg=new SpeechSynthesisUtterance(`{msg['content'].replace('`','')}`); window.speechSynthesis.speak(msg);" 
                style='margin-left:5px; cursor:pointer; background:#333; color:white; border:none; border-radius:5px; padding:5px;'>🔊</button>
        </div>
        """, unsafe_allow_html=True)

# ================================
# Sticky bottom input with submit
# ================================
st.markdown("""
<div style="position:fixed; bottom:0; width:100%; display:flex; justify-content:center; z-index:1000; background:#0d0d0d; padding:10px;">
    <form id="chatForm" style="display:flex; width:95%; max-width:600px;">
        <input name="user_input" type="text" placeholder="Ask about any disease..." 
            style="flex:1; border:none; border-radius:20px; padding:10px; font-size:16px;">
        <input type="submit" value="Send" style="margin-left:5px; padding:10px 15px; border:none; border-radius:20px; background:#003366; color:white; cursor:pointer;">
    </form>
</div>
""", unsafe_allow_html=True)

# ================================
# Capture input using Streamlit form submission
# ================================
def get_input():
    from streamlit_js_eval import streamlit_js_eval
    # get value from the input box
    js_code = """
    (() => {
        const input = document.querySelector('input[name="user_input"]');
        return input ? input.value : "";
    })()
    """
    value = streamlit_js_eval(js_code)
    return value

# Using st.form_submit_button alternative
user_input = st.text_input("", key="input_fixed")  # hidden but required for Streamlit rerun

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Check FAQs
    answer_en = find_answer_from_faqs(user_input)
    if not answer_en:
        answer_en = fetch_from_gemini(user_input)
    if not answer_en or "Error" in answer_en:
        answer_en = find_answer_from_faqs(user_input) or "Sorry, I cannot fetch this right now."

    # Translate
    answer_hi = translate_to_language(answer_en, "hi")

    bot_reply = f"**English:** {answer_en}\n\n🌍 **Hindi:** {answer_hi}"
    st.session_state.messages.append({"role": "bot", "content": bot_reply})

    # Text-to-speech
    components.html(f"""
    <script>
    var msg = new SpeechSynthesisUtterance("{answer_en.replace('"','\\"')}");
    window.speechSynthesis.speak(msg);
    </script>
    """, height=0)







