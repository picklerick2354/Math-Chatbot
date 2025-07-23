import streamlit as st
import re
import base64
from openai import OpenAI

client = OpenAI(api_key="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")

def convert_inline_latex(text: str) -> str:
    pattern = re.compile(r"\\\((.+?)\\\)", re.DOTALL)
    return pattern.sub(r'$$', text)

def call_openai_math_solver(prompt_text: str):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": prompt_text}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ OpenAI error: {str(e)}"

def call_openai_vision_solver(image_bytes):
    try:
        base64_img = base64.b64encode(image_bytes).decode()
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Solve the following equation step-by-step: given in the image. Use LaTeX formatting with $$...$$ where appropriate."},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Solve the following equation step-by-step: given in the image. Use display-style LaTeX formatting with $$...$$ where appropriate."},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_img}"}}
                    ]
                }
            ],
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Vision error: {str(e)}"

def response_formatter(content: str):
    # Fix for improperly wrapped LaTeX in brackets or parentheses
    content = re.sub(r"\[\s*([^\[\]]*\\[^\[\]]*)\s*\]", r"$$\1$$", content)  # Convert [ ... ] to $$ ... $$
    content = re.sub(r"\((x\s*=.*?)\)", r"$$\1$$", content)  # Convert (x = ...) to $$x = ...$$

    # Render LaTeX properly
    pattern = re.compile(r"(\$\$.*?\$\$|\$.*?\$)", re.DOTALL)
    parts = pattern.split(content)
    for part in parts:
        if part.startswith("$$") and part.endswith("$$"):
            st.latex(part[2:-2])
        elif part.startswith("$") and part.endswith("$"):
            st.latex(part[1:-1])
        else:
            st.markdown(part.strip())

st.set_page_config(page_title="Math Chat Solver", layout="centered", initial_sidebar_state="collapsed")

# === Custom Styling ===
st.markdown("""
    <style>
    .chat-container { background-color: #f1f2f6; border-radius: 12px; padding: 20px; margin-bottom: 15px; }
    .user-msg { background-color: #d1e8ff; color: #000; padding: 12px 16px; border-radius: 12px; margin-bottom: 10px; text-align: right; white-space: pre-wrap; }
    .bot-msg { background-color: #ffffff; color: #111; padding: 12px 16px; border-radius: 12px; margin-bottom: 10px; text-align: left; white-space: pre-wrap; }
    .centered { display: flex; justify-content: center; align-items: center; flex-direction: column; }

    section[data-testid="stFileUploader"] > div:first-child {
        display: none !important;
    }

    .file-upload-icon {
        font-size: 24px;
        background: #2c2f35;
        color: white;
        padding: 6px 10px;
        border-radius: 6px;
        cursor: pointer;
        text-align: center;
        transition: background 0.3s;
    }
    .file-upload-icon:hover {
        background: #444850;
    }
    </style>
""", unsafe_allow_html=True)

# === Header ===
st.markdown("<h1 class='centered'>🧮 Math Chat Solver</h1>", unsafe_allow_html=True)
st.markdown("<p class='centered'>Ask a math question or upload an image and I'll solve it step-by-step using AI.</p>", unsafe_allow_html=True)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# === Chat History Display ===
st.markdown("---")
st.markdown("### 💬 Chat History")
for msg in st.session_state.chat_history:
    bubble_class = "user-msg" if msg["role"] == "user" else "bot-msg"
    with st.container():
        st.markdown(f"<div class='{bubble_class}'>", unsafe_allow_html=True)
        if msg["role"] == "assistant":
            response_formatter(msg["content"])
        else:
            st.markdown(msg["content"])
        st.markdown("</div>", unsafe_allow_html=True)

# === Bottom Input Bar ===
with st.form("bottom_input_form", clear_on_submit=True):
    col1, col2, col3 = st.columns([0.1, 0.8, 0.1])

    with col1:
        file = st.file_uploader(
            label="Upload Image",
            type=["png", "jpg", "jpeg"],
            label_visibility="collapsed"
        )
        st.markdown("""
            <style>
                section[data-testid="stFileUploader"] > label {display: none;}
                section[data-testid="stFileUploader"] > div:first-child {display: none !important;}
                .custom-upload-icon {
                    font-size: 24px;
                    background: #2c2f35;
                    color: white;
                    padding: 6px 10px;
                    border-radius: 6px;
                    text-align: center;
                    cursor: pointer;
                    transition: background 0.3s;
                }
                .custom-upload-icon:hover {
                    background: #444850;
                }
            </style>
            <div class='custom-upload-icon'>📎</div>
        """, unsafe_allow_html=True)

    with col2:
        text_input = st.text_input(
            label="Math Question Input",
            placeholder="Type your math question...",
            label_visibility="collapsed"
        )

    with col3:
        submit = st.form_submit_button("⬆️")

# === Submit Logic ===
if submit:
    if text_input.strip():
        st.session_state.chat_history.append({"role": "user", "content": text_input})
        sanitized_expr = convert_inline_latex(text_input)
        result = call_openai_math_solver(
            f"Solve the following equation step-by-step:\n\n{sanitized_expr}\n\n"
            "Use LaTeX formatting with $$...$$ where appropriate."
        )
        st.session_state.chat_history.append({"role": "assistant", "content": result})
    elif file:
        st.session_state.chat_history.append({"role": "user", "content": "🖼 Uploaded image."})
        result = call_openai_vision_solver(file.read())
        st.session_state.chat_history.append({"role": "assistant", "content": result})
