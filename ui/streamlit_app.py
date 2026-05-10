"""
AskVineet — Streamlit Chat UI
Black background · Neon green text · Terminal/matrix aesthetic

Run: streamlit run ui/streamlit_app.py
"""

from __future__ import annotations

import time
import uuid
from typing import Optional

import httpx
import streamlit as st

import os

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="AskVineet",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# CSS Injection — black/neon-green terminal theme
# ---------------------------------------------------------------------------

DARK_GREEN_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

/* ── Design Tokens ── */
:root {
    --bg: #0d1117;
    --surface: #161b22;
    --primary: #00ff9c;
    --muted: #4b7060;
    --border: rgba(0, 255, 156, 0.15);
    --text: #b0e0c8;
    --font-mono: 'Courier New', monospace;
    --font-sans: 'Inter', sans-serif;
}

/* ── Global ── */
html, body, [class*="css"] {
    background-color: var(--bg) !important;
    color: var(--primary) !important;
    font-family: var(--font-mono) !important;
}

/* ── Main container — full width ── */
.main .block-container {
    background-color: var(--bg) !important;
    padding-top: 2rem !important;
    max-width: 100% !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
}

/* ── Expand app view to full width ── */
[data-testid="stAppViewBlockContainer"] {
    max-width: 100% !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
    padding-top: 2rem !important;
}

/* ── Remove Streamlit default top padding ── */
.main > div:first-child {
    padding-top: 0 !important;
}

/* ── Kill Streamlit's hidden top bar space ── */
[data-testid="stHeader"] {
    background: var(--bg) !important;
    height: 0 !important;
    min-height: 0 !important;
}
header[data-testid="stHeader"] {
    display: none !important;
}
[data-testid="stToolbar"] {
    display: none !important;
}
[data-testid="stDecoration"] {
    display: none !important;
}

/* ── Header / Title ── */
h1, h2, h3, h4, h5, h6 {
    color: #ffffff !important;
    font-family: var(--font-mono) !important;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background-color: var(--surface) !important;
    border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] * {
    color: var(--primary) !important;
}
section[data-testid="stSidebar"] .stMarkdown h2 {
    font-size: 1rem !important;
    letter-spacing: 0.05em;
}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background-color: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px;
    margin-bottom: 0.6rem;
    padding: 12px 16px !important;
}
[data-testid="stChatMessage"] p {
    color: var(--text) !important;
}

/* ── User message ── */
[data-testid="stChatMessage"][data-testid*="user"] {
    background-color: rgba(0, 255, 156, 0.04) !important;
    border-left: 3px solid var(--primary) !important;
    border-radius: 8px 8px 0 8px;
}

/* ── Assistant message ── */
[data-testid="stChatMessage"][data-testid*="assistant"] {
    border-left: 3px solid var(--muted) !important;
    border-radius: 8px 8px 8px 0;
}

/* ── Chat input ── */
[data-testid="stChatInput"] textarea,
[data-testid="stChatInputTextArea"] {
    background-color: var(--surface) !important;
    color: var(--primary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px;
    font-family: var(--font-mono) !important;
    caret-color: var(--primary);
    font-size: 0.9rem;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: rgba(0, 255, 156, 0.4) !important;
    box-shadow: 0 0 0 1px rgba(0, 255, 156, 0.1) !important;
}

/* ── Buttons ── */
.stButton > button {
    background-color: var(--surface) !important;
    color: var(--primary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px;
    font-family: var(--font-mono) !important;
    font-size: 0.82rem;
    transition: all 0.2s;
}
.stButton > button:hover {
    background-color: rgba(0, 255, 156, 0.08) !important;
    box-shadow: 0 0 12px rgba(0, 255, 156, 0.15);
    border-color: rgba(0, 255, 156, 0.4) !important;
}

/* ── Select boxes / dropdowns ── */
.stSelectbox > div > div {
    background-color: var(--surface) !important;
    color: var(--primary) !important;
    border: 1px solid var(--border) !important;
}

/* ── Expanders ── */
.streamlit-expanderHeader {
    background-color: var(--surface) !important;
    color: var(--muted) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px;
}

/* ── Text inputs ── */
input[type="text"], input[type="password"] {
    background-color: var(--surface) !important;
    color: var(--primary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px;
}

/* ── Info / success / warning boxes ── */
.stAlert {
    background-color: var(--surface) !important;
    border: 1px solid var(--border) !important;
    color: var(--primary) !important;
    border-radius: 6px;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background-color: var(--surface) !important;
    border: 1px dashed var(--border) !important;
    border-radius: 6px;
    padding: 8px !important;
}
[data-testid="stFileUploader"] .stBaseButton-secondary button,
[data-testid="stFileUploader"] button.st-emotion-cache-1lgf0gf {
    background-color: var(--primary) !important;
    color: var(--bg) !important;
    border: none !important;
    font-weight: 700 !important;
    font-family: var(--font-mono) !important;
    border-radius: 6px !important;
}
[data-testid="stFileUploader"] .stBaseButton-secondary button:hover,
[data-testid="stFileUploader"] button.st-emotion-cache-1lgf0gf:hover {
    background-color: #00cc7d !important;
}
[data-testid="stFileUploader"] small,
[data-testid="stFileUploader"] span,
[data-testid="stFileUploader"] p,
[data-testid="stFileUploader"] label,
[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] span,
[data-testid="stFileUploaderDropzone"] * {
    color: #000000 !important;
}
[data-testid="stFileUploaderDropzone"] {
    background-color: #ffffff !important;
    border: 1px dashed rgba(0, 255, 156, 0.4) !important;
    border-radius: 6px;
}

/* ── Checkbox ── */
.stCheckbox label span {
    color: var(--muted) !important;
    font-size: 0.82rem;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: rgba(0, 255, 156, 0.15); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: rgba(0, 255, 156, 0.3); }

/* ── Blinking cursor ── */
@keyframes blink {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0; }
}
.cursor {
    display: inline-block;
    width: 10px;
    height: 2px;
    background: var(--primary);
    animation: blink 1s step-end infinite;
    vertical-align: baseline;
    margin-left: 2px;
}

/* ── Logo header — full width ── */
.av-header {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 16px;
    padding: 1.5rem 1rem 1rem;
    width: 100%;
    box-sizing: border-box;
}
.av-header svg { flex-shrink: 0; }
.av-wordmark {
    display: flex;
    flex-direction: column;
}
.av-name {
    font-family: var(--font-mono);
    font-size: 1.6rem;
    font-weight: 700;
    color: #ffffff;
    line-height: 1.2;
    letter-spacing: 0.04em;
    white-space: nowrap;
}
.av-tagline {
    font-family: var(--font-sans);
    font-size: 0.68rem;
    color: rgba(255, 255, 255, 0.55);
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    line-height: 1.4;
    white-space: nowrap;
}
.av-subtitle {
    text-align: center;
    font-family: var(--font-mono);
    font-size: 0.78rem;
    color: var(--muted);
    margin-top: 4px;
    padding-bottom: 0.8rem;
    border-bottom: 1px solid var(--border);
    width: 100%;
}

/* ── Sidebar collapse button (inside expanded sidebar) ── */
[data-testid="stSidebarCollapseButton"] {
    position: relative;
}
[data-testid="stSidebarCollapseButton"] button {
    background-color: var(--primary) !important;
    color: var(--bg) !important;
    border-radius: 6px !important;
    border: none !important;
    padding: 6px 12px !important;
    min-width: 120px !important;
    min-height: 36px !important;
    font-family: var(--font-mono) !important;
    font-size: 0.75rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.04em;
    box-shadow: 0 0 10px rgba(0, 255, 156, 0.2);
    transition: all 0.2s;
}
[data-testid="stSidebarCollapseButton"] button:hover {
    background-color: #00cc7d !important;
    box-shadow: 0 0 18px rgba(0, 255, 156, 0.35);
}
[data-testid="stSidebarCollapseButton"] button::after {
    content: " Controls";
    font-family: var(--font-mono);
    font-size: 0.72rem;
}

/* ── Sidebar expand button (collapsed state — the ">" arrow) ── */
[data-testid="stSidebarCollapsedControl"] {
    position: fixed !important;
    top: 12px !important;
    left: 12px !important;
    z-index: 999999 !important;
}
[data-testid="stSidebarCollapsedControl"] button {
    background-color: var(--primary) !important;
    color: var(--bg) !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 8px 16px 8px 10px !important;
    min-width: 130px !important;
    min-height: 40px !important;
    font-family: var(--font-mono) !important;
    font-size: 0.78rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.03em;
    box-shadow: 0 2px 14px rgba(0, 255, 156, 0.25);
    transition: all 0.2s;
    display: flex !important;
    align-items: center !important;
    gap: 6px !important;
}
[data-testid="stSidebarCollapsedControl"] button:hover {
    background-color: #00cc7d !important;
    box-shadow: 0 2px 20px rgba(0, 255, 156, 0.4);
    transform: translateX(2px);
}
[data-testid="stSidebarCollapsedControl"] button::after {
    content: "Controls ▸";
    font-family: var(--font-mono);
    font-size: 0.74rem;
    font-weight: 700;
    color: var(--bg);
}

/* ── Source document accordion ── */
.source-box {
    background-color: var(--surface);
    border: 1px solid var(--border);
    border-left: 2px solid rgba(0, 255, 156, 0.25);
    border-radius: 4px;
    padding: 8px 12px;
    margin-top: 4px;
    font-size: 0.82em;
    color: var(--muted);
}

/* ── Divider ── */
hr {
    border-color: var(--border) !important;
}

/* ── Spinner / loading ── */
.stSpinner > div {
    border-top-color: var(--primary) !important;
}
</style>
"""

st.markdown(DARK_GREEN_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# On Render, RENDER_EXTERNAL_HOSTNAME is auto-set (e.g. "askvineet-ui.onrender.com")
# Derive the API URL from it if API_BASE_URL isn't explicitly set.
_default_api = "http://localhost:8000"
if os.environ.get("RENDER_EXTERNAL_HOSTNAME"):
    # Render convention: UI service name ends with -ui, API with -api
    _render_host = os.environ["RENDER_EXTERNAL_HOSTNAME"]
    _api_host = _render_host.replace("-ui", "-api")
    _default_api = f"https://{_api_host}"

# BACKEND_URL takes priority, then API_BASE_URL, then the auto-derived default
API_BASE = (
    os.environ.get("BACKEND_URL")
    or os.environ.get("API_BASE_URL")
    or _default_api
).rstrip("/")
DEFAULT_SESSION = str(uuid.uuid4())

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = DEFAULT_SESSION

if "agent_ready" not in st.session_state:
    st.session_state.agent_ready = False

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    """
<div class="av-header">
  <svg width="48" height="48" viewBox="0 0 52 52" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="52" height="52" rx="12" fill="#00FF9C" opacity="0.08"/>
    <rect width="52" height="52" rx="12" fill="none" stroke="#00FF9C" stroke-width="1" opacity="0.3"/>
    <path d="M14 14 L26 36 L38 14" fill="none" stroke="#00FF9C" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
    <circle cx="26" cy="38" r="2.5" fill="#00FF9C"/>
  </svg>
  <div class="av-wordmark">
    <span class="av-name">Vineet Kumar</span>
    <span class="av-tagline">VINEET AI AGENT</span>
  </div>
</div>
<div class="av-subtitle">Ask me anything · Upload docs · Get live data<span class="cursor"></span></div>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _api_post(endpoint: str, payload: dict) -> Optional[dict]:
    try:
        r = httpx.post(f"{API_BASE}{endpoint}", json=payload, timeout=60, follow_redirects=True)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return None


def _upload_document(file) -> Optional[dict]:
    try:
        r = httpx.post(
            f"{API_BASE}/documents/upload",
            files={"file": (file.name, file.getvalue(), file.type)},
            timeout=60,
            follow_redirects=True,
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _show_health() -> None:
    try:
        r = httpx.get(f"{API_BASE}/health", timeout=5, follow_redirects=True)
        if r.status_code == 200:
            st.sidebar.success("✅ API online")
        else:
            st.sidebar.warning(f"⚠️ API status: {r.status_code}")
    except Exception:
        st.sidebar.error("❌ API offline — start with `uvicorn app.main:app`")


# ---------------------------------------------------------------------------
# Sidebar controls
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## ⚙️ Controls")

    if st.button("🔄 New Conversation"):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

    st.markdown(f"**Session:** `{st.session_state.session_id[:8]}…`")
    st.markdown("---")

    show_sources = st.checkbox("Show source documents", value=True)
    show_route = st.checkbox("Show routing info", value=False)

    st.markdown("---")
    st.markdown("### 📁 Upload Document")
    uploaded = st.file_uploader(
        "Drop a PDF, TXT, DOCX, or MD file",
        type=["pdf", "txt", "docx", "md"],
        label_visibility="collapsed",
    )
    if uploaded:
        with st.spinner("Indexing document..."):
            resp = _upload_document(uploaded)
        if resp:
            st.success(f"✅ Indexed: {resp.get('filename')}")
        else:
            st.error("Upload failed — is the API running?")

    st.markdown("---")
    st.markdown("### 🩺 System Status")
    if st.button("Check API"):
        _show_health()


# ---------------------------------------------------------------------------
# Render conversation history
# ---------------------------------------------------------------------------

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        if msg["role"] == "assistant" and show_sources and msg.get("sources"):
            with st.expander(f"📄 Sources ({len(msg['sources'])})"):
                for src in msg["sources"]:
                    st.markdown(
                        f'<div class="source-box">'
                        f'<strong>{src.get("filename", "unknown")}</strong>'
                        f'{" · p." + str(src.get("page")) if src.get("page") else ""}'
                        f'<br/>{src.get("excerpt", "")[:300]}…'
                        f"</div>",
                        unsafe_allow_html=True,
                    )

        if msg["role"] == "assistant" and show_route and msg.get("route"):
            st.caption(f"Route: `{msg['route']}` · Tools: `{', '.join(msg.get('tools', [])) or 'none'}`")

# ---------------------------------------------------------------------------
# Chat input
# ---------------------------------------------------------------------------

if prompt := st.chat_input("Ask me anything..."):
    # Display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get response from API
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = _api_post(
                "/chat/",
                {"message": prompt, "session_id": st.session_state.session_id},
            )

        if response:
            answer = response.get("answer", "No response received.")
            sources = response.get("sources", [])
            route = response.get("route_used", "direct")
            tool_calls = response.get("tool_calls", [])

            st.markdown(answer)

            if show_sources and sources:
                with st.expander(f"📄 Sources ({len(sources)})"):
                    for src in sources:
                        st.markdown(
                            f'<div class="source-box">'
                            f'<strong>{src.get("filename", "unknown")}</strong>'
                            f'{" · p." + str(src.get("page")) if src.get("page") else ""}'
                            f'<br/>{src.get("excerpt", "")[:300]}…'
                            f"</div>",
                            unsafe_allow_html=True,
                        )

            if show_route:
                st.caption(
                    f"Route: `{route}` · Tools: `{', '.join(tool_calls) or 'none'}`"
                )

            # Save to session state
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": answer,
                    "sources": sources,
                    "route": route,
                    "tools": tool_calls,
                }
            )
        else:
            err_msg = (
                "❌ Could not connect to the AskVineet API. "
                "Start the backend with:\n```\nuvicorn app.main:app --reload\n```"
            )
            st.error(err_msg)
            st.session_state.messages.append(
                {"role": "assistant", "content": err_msg}
            )
