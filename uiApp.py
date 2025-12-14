import streamlit as st
import re
import base64
from openai import OpenAI

# === Admin Access Control ===
# Set your admin password securely in Streamlit secrets
IS_ADMIN = False
if "ADMIN_PASS" in st.secrets:
    password = st.text_input("🔒 Admin password (optional)", type="password", placeholder="Leave blank if not admin")
    if password == st.secrets["ADMIN_PASS"]:
        IS_ADMIN = True
        st.success("✅ Admin mode enabled")
    else:
        if password:
            st.error("❌ Incorrect password — running in user mode")

# Hide Streamlit system stats and footer for non-admins
if not IS_ADMIN:
    st.markdown(
        """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .stDeployButton {display: none;}
        .viewerBadge_link__qRIco {display: none !important;}
        </style>
        """,
        unsafe_allow_html=True
    )

# ✅ Load API key securely from Streamlit secrets
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def convert_inline_latex(text: str) -> str:
    pattern = re.compile(r"\\\((.+?)\\\)", re.DOTALL)
    return pattern.sub(r'$$', text)

def call_openai_math_solver(prompt_text: str):
    try:
        formatted_prompt = f"""
Solve the following math problem step by step:

{prompt_text}

Formatting rules you must follow:
- Wrap ALL mathematical expressions, equations, and fractions in display-style LaTeX using $$...$$ only.
- Do NOT use inline math ($...$), \\[...\\], or \\(...\\).
- Each equation should be on its own line inside $$...$$.
- Explanations must be plain text only (no LaTeX).
- Do not include code fences, markdown, or backticks.
"""
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": formatted_prompt}],
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
                {
                    "role": "system",
                    "content": (
                        "You are a math solver. Always solve equations step-by-step "
                        "and follow strict formatting rules:\n"
                        "- Use display-style LaTeX with $$...$$ for ALL math.\n"
                        "- Do NOT use inline math ($...$), \\[...\\], or \\(...\\).\n"
                        "- Each equation must be on its own line inside $$...$$.\n"
                        "- Explanations must be plain text only.\n"
                        "- Do not include code fences, markdown, or backticks."
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Solve the math problem in this image step by step."},
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
    content = re.sub(r"\[\s*([^\[\]]*\\[^\[\]]*)\s*\]", r"$$\1$$", content)
    content = re.sub(r"\((x\s*=.*?)\)", r"$$\1$$", content)
    pattern = re.compile(r"(\$\$.*?\$\$|\$.*?\$)", re.DOTALL)
    parts = pattern.split(content)
    for part in parts:
        if part.startswith("$$") and part.endswith("$$"):
            st.latex(part[2:-2])
        elif part.startswith("$") and part.endswith("$"):
            st.latex(part[1:-1])
        else:
            if part.strip():
                st.markdown(part.strip())

st.set_page_config(page_title="Math Chat Solver", layout="centered", initial_sidebar_state="collapsed")

# === Custom Styling ===
st.markdown("""
    <style>
    .chat-container { background-color: #f1f2f6; border-radius: 12px; padding: 20px; margin-bottom: 15px; }
    .user-msg { background-color: #d1e8ff; color: #000; padding: 12px 16px; border-radius: 12px; margin-bottom: 10px; text-align: right; white-space: pre-wrap; }
    .bot-msg { background-color: #ffffff; color: #111; padding: 12px 16px; border-radius: 12px; margin-bottom: 10px; text-align: left; white-space: pre-wrap; }
    .centered { display: flex; justify-content: center; align-items: center; flex-direction: column; }
    </style>
""", unsafe_allow_html=True)

# === Header ===
st.markdown("<h1 class='centered'>🧮 Snap2Solve</h1>", unsafe_allow_html=True)
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
            if msg.get("type") == "image" and msg.get("content") is not None:
                st.image(msg["content"], caption="Uploaded image", use_container_width=True)
            else:
                st.markdown(msg["content"])
        st.markdown("</div>", unsafe_allow_html=True)

# === Bottom Input Bar ===
with st.form("bottom_input_form", clear_on_submit=True):
    # Columns for text input + submit button
    col1, col2 = st.columns([1.65, 0.15])
    with col1:
        text_input = st.text_input(
            label="Math Question Input",
            placeholder="Type your math question...",
            label_visibility="collapsed"
        )
    with col2:
        submit = st.form_submit_button("⬆️")
    
    # File uploader below, full width
    file = st.file_uploader(
        "Upload an image (png/jpg/jpeg, max 200MB)",
        type=["png", "jpg", "jpeg"],
        label_visibility="collapsed"
    )

if file is not None:
    st.success(f"📎 File ready: {file.name} ({file.size} bytes)")

# === Submit Logic ===
if submit:
    if text_input.strip():
        st.session_state.chat_history.append({"role": "user", "content": text_input})
        sanitized_expr = convert_inline_latex(text_input)
        result = call_openai_math_solver(sanitized_expr)
        st.session_state.chat_history.append({"role": "assistant", "content": result})
        st.rerun()
    elif file:
        image_bytes = file.read()
        st.session_state.chat_history.append({
            "role": "user",
            "type": "image",
            "content": image_bytes
        })
        result = call_openai_vision_solver(image_bytes)
        st.session_state.chat_history.append({"role": "assistant", "content": result})
        st.rerun()
    else:
        st.warning("Please enter a math question or upload an image.")

