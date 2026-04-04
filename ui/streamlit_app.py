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
/* ── Global ── */
html, body, [class*="css"] {
    background-color: #000000 !important;
    color: #00FF41 !important;
    font-family: 'Courier New', Courier, monospace !important;
}

/* ── Main container ── */
.main .block-container {
    background-color: #000000 !important;
    padding-top: 1rem;
}

/* ── Header / Title ── */
h1, h2, h3, h4, h5, h6 {
    color: #00FF41 !important;
    font-family: 'Courier New', Courier, monospace !important;
    text-shadow: 0 0 10px #00FF41, 0 0 20px #00FF41;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background-color: #0a0a0a !important;
    border-right: 1px solid #00FF41;
}
section[data-testid="stSidebar"] * {
    color: #00FF41 !important;
}

/* ── Chat messages ── */
[data-testid="stChatMessage"] {
    background-color: #0a0a0a !important;
    border: 1px solid #003300 !important;
    border-radius: 4px;
    margin-bottom: 0.5rem;
}

/* ── User message ── */
[data-testid="stChatMessage"][data-testid*="user"] {
    border-left: 3px solid #00FF41 !important;
}

/* ── Assistant message ── */
[data-testid="stChatMessage"][data-testid*="assistant"] {
    border-left: 3px solid #008F11 !important;
}

/* ── Chat input ── */
[data-testid="stChatInput"] textarea,
[data-testid="stChatInputTextArea"] {
    background-color: #0a0a0a !important;
    color: #00FF41 !important;
    border: 1px solid #00FF41 !important;
    border-radius: 4px;
    font-family: 'Courier New', Courier, monospace !important;
    caret-color: #00FF41;
}

/* ── Buttons ── */
.stButton > button {
    background-color: #000000 !important;
    color: #00FF41 !important;
    border: 1px solid #00FF41 !important;
    border-radius: 4px;
    font-family: 'Courier New', Courier, monospace !important;
    transition: all 0.2s;
}
.stButton > button:hover {
    background-color: #003300 !important;
    box-shadow: 0 0 8px #00FF41;
}

/* ── Select boxes / dropdowns ── */
.stSelectbox > div > div {
    background-color: #0a0a0a !important;
    color: #00FF41 !important;
    border: 1px solid #00FF41 !important;
}

/* ── Expanders ── */
.streamlit-expanderHeader {
    background-color: #0a0a0a !important;
    color: #008F11 !important;
    border: 1px solid #003300 !important;
}

/* ── Text inputs ── */
input[type="text"], input[type="password"] {
    background-color: #0a0a0a !important;
    color: #00FF41 !important;
    border: 1px solid #00FF41 !important;
}

/* ── Info / success / warning boxes ── */
.stAlert {
    background-color: #0a0a0a !important;
    border: 1px solid #00FF41 !important;
    color: #00FF41 !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #000000; }
::-webkit-scrollbar-thumb { background: #003300; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #00FF41; }

/* ── Blinking cursor animation on agent name ── */
@keyframes blink {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0; }
}
.cursor {
    display: inline-block;
    width: 12px;
    animation: blink 1s step-end infinite;
    color: #00FF41;
}

/* ── Source document accordion ── */
.source-box {
    background-color: #050505;
    border: 1px solid #003300;
    border-radius: 4px;
    padding: 8px 12px;
    margin-top: 4px;
    font-size: 0.85em;
    color: #008F11;
}

/* ── Divider ── */
hr {
    border-color: #003300 !important;
}
</style>
"""

st.markdown(DARK_GREEN_CSS, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
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
<div style="text-align:center; padding: 1.5rem 0 0.5rem;">
  <h1 style="font-size: 3rem; letter-spacing: 0.2rem; margin-bottom:0;">
    &gt; AskVineet<span class="cursor">_</span>
  </h1>
  <p style="color:#008F11; font-size:0.9rem; margin-top:0.3rem;">
    AI Agent &nbsp;·&nbsp; Built by Vineet Kumar &nbsp;·&nbsp; vineetkr.com
  </p>
</div>
<hr/>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _api_post(endpoint: str, payload: dict) -> Optional[dict]:
    try:
        r = httpx.post(f"{API_BASE}{endpoint}", json=payload, timeout=60)
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
        )
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _show_health() -> None:
    try:
        r = httpx.get(f"{API_BASE}/health", timeout=5)
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
