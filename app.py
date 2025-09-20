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
            f"<div style='background-color:#003366; color:white; padding:10px; border-radius:20px; max-width:70%;'>🧑 {msg['content']}</div></div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"<div style='display:flex; justify-content:flex-start; align-items:center; margin:5px;'>"
            f"<div style='background-color:#000; color:white; padding:10px; border-radius:20px; max-width:70%;'>🤖 {msg['content']}</div>"
            f"<button onclick=\"var msg=new SpeechSynthesisUtterance(`{msg['content'].replace('`','')}`); window.speechSynthesis.speak(msg);\" "
            f"style='margin-left:5px; cursor:pointer; background:#333; color:white; border:none; border-radius:5px; padding:5px;'>🔊</button>"
            f"</div>",
            unsafe_allow_html=True
        )

# ================================
# Bottom input form
# ================================
with st.form(key="chat_form", clear_on_submit=True):
    user_input = st.text_input("Type your message here...", key="user_input")
    submit_button = st.form_submit_button("Send")

    if submit_button and user_input:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": user_input})

        # Get bot response
        answer_en = find_answer_from_faqs(user_input)
        if not answer_en:
            answer_en = fetch_from_gemini(user_input)
        if not answer_en or "Error" in answer_en:
            answer_en = find_answer_from_faqs(user_input) or "Sorry, I cannot fetch this right now."

        answer_hi = translate_to_language(answer_en, "hi")
        bot_reply = f"**English:** {answer_en}\n\n🌍 **Hindi:** {answer_hi}"
        st.session_state.messages.append({"role": "bot", "content": bot_reply})

        # Speak automatically
        components.html(f"""
        <script>
        var msg = new SpeechSynthesisUtterance("{answer_en.replace('"','\\"')}");
        window.speechSynthesis.speak(msg);
        </script>
        """, height=0)

        st.experimental_rerun()









