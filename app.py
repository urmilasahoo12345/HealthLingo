import os
import json
import time
import streamlit as st
from dotenv import load_dotenv
from google import genai
from deep_translator import GoogleTranslator

# ================================
# Load environment variables
# ================================
load_dotenv()
gemini_key = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_KEY_HERE")

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

# ---- Global CSS ----
st.markdown(
    """
    <style>
    /* Bright glowing title */
    .glow-title {
        text-align: center;
        font-size: 32px;
        font-weight: bold;
        color: white;
        text-shadow: 0px 0px 10px #00ff00, 0px 0px 15px #00ccff, 0px 0px 20px #ffffff;
        margin-bottom: 20px;
    }

    /* Glow effect for Clear Chat button */
    div[data-testid="stButton"] > button {
        background-color: #111111;
        color: white;
        border-radius: 10px;
        border: 1px solid #00ffcc;
        box-shadow: 0px 0px 12px #00ffcc;
        transition: 0.3s;
    }
    div[data-testid="stButton"] > button:hover {
        background-color: #00ffcc;
        color: black;
        box-shadow: 0px 0px 22px #00ffcc;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---- Title ----
st.markdown(
    "<h2 class='glow-title'>"
    "<span style='color:lime;'>Health</span>"
    "<span style='color:cyan;'>Lingo</span> – Your AI Health Assistant</h2>",
    unsafe_allow_html=True
)

# --- Clear Chat Button ---
if st.button("🗑️ Clear Chat"):
    st.session_state.messages = []

if "messages" not in st.session_state:
    st.session_state.messages = []

# ================================
# Display chat history
# ================================
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(
            f"""
            <div style='display:flex; justify-content:flex-end; margin:5px;'>
                <div style='background-color:#003366; color:white; padding:10px; border-radius:15px; max-width:70%;
                            box-shadow:0px 1px 3px rgba(0,0,0,0.3); white-space:pre-wrap;'>
                    🧑 {msg['content']}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""
            <div style='display:flex; justify-content:flex-start; margin:5px;'>
                <div style='background-color:#000000; color:white; padding:10px; border-radius:15px; max-width:70%;
                            box-shadow:0px 1px 3px rgba(0,0,0,0.3); white-space:pre-wrap;'>
                    🤖 {msg['content']}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ================================
# Input box
# ================================
user_input = st.chat_input("Ask me about any disease, symptoms, or prevention...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    answer_en = find_answer_from_faqs(user_input)
    if not answer_en:
        answer_en = fetch_from_gemini(user_input)
    if not answer_en or "Error" in answer_en:
        answer_en = find_answer_from_faqs(user_input) or "Sorry, I cannot fetch this right now."
    answer_hi = translate_to_language(answer_en, "hi")
    bot_reply = f"**English:** {answer_en}\n\n🌍 **Hindi:** {answer_hi}"
    st.session_state.messages.append({"role": "bot", "content": bot_reply})
    st.rerun()



