/**
 * AskVineet — Embeddable Chat Widget
 * Connects to FastAPI backend via REST (with WebSocket upgrade path).
 */

const API_BASE = "http://localhost:8000";
const WS_BASE = "ws://localhost:8000";
let sessionId = crypto.randomUUID();
let ws = null;
let isWaiting = false;

// ── DOM helpers ─────────────────────────────────────────────────────────────

const $messages = () => document.getElementById("av-messages");
const $input = () => document.getElementById("av-input");
const $btn = () => document.getElementById("av-send-btn");
const $status = () => document.getElementById("av-status");

function setStatus(text) {
  $status().textContent = text;
}

function setWaiting(waiting) {
  isWaiting = waiting;
  $btn().disabled = waiting;
  $input().disabled = waiting;
}

// ── Message rendering ────────────────────────────────────────────────────────

function appendMessage(role, content, sources = [], route = "") {
  const el = document.createElement("div");
  el.className = `av-msg av-msg--${role}`;

  if (role === "assistant") {
    el.innerHTML = `<span class="av-prefix">[AskVineet]</span>${escapeHtml(content)}`;

    if (sources && sources.length > 0) {
      const srcDiv = document.createElement("div");
      srcDiv.className = "av-sources";
      srcDiv.innerHTML = `📄 Sources (${sources.length}):`;
      sources.forEach((src) => {
        const item = document.createElement("div");
        item.className = "av-source-item";
        item.textContent = `${src.filename || src.source}${src.page ? " · p." + src.page : ""}: ${(src.excerpt || "").slice(0, 150)}…`;
        srcDiv.appendChild(item);
      });
      el.appendChild(srcDiv);
    }
  } else {
    el.innerHTML = `<span class="av-prefix">[You]</span>${escapeHtml(content)}`;
  }

  $messages().appendChild(el);
  $messages().scrollTop = $messages().scrollHeight;
  return el;
}

function appendTypingIndicator() {
  const el = document.createElement("div");
  el.className = "av-msg av-msg--assistant av-msg--typing";
  el.id = "av-typing";
  el.innerHTML = `<span class="av-prefix">[AskVineet]</span>thinking`;
  $messages().appendChild(el);
  $messages().scrollTop = $messages().scrollHeight;
  return el;
}

function removeTypingIndicator() {
  const el = document.getElementById("av-typing");
  if (el) el.remove();
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\n/g, "<br/>");
}

// ── Send message ─────────────────────────────────────────────────────────────

async function sendMessage() {
  const input = $input();
  const message = input.value.trim();
  if (!message || isWaiting) return;

  input.value = "";
  appendMessage("user", message);
  setWaiting(true);
  setStatus("thinking...");

  const typing = appendTypingIndicator();

  try {
    const resp = await fetch(`${API_BASE}/chat/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: sessionId }),
    });

    removeTypingIndicator();

    if (!resp.ok) {
      const err = await resp.text();
      appendMessage("assistant", `⚠️ API error (${resp.status}): ${err}`);
      setStatus("error");
    } else {
      const data = await resp.json();
      appendMessage(
        "assistant",
        data.answer,
        data.sources || [],
        data.route_used,
      );
      setStatus(
        `route: ${data.route_used} · session: ${sessionId.slice(0, 8)}`,
      );
    }
  } catch (err) {
    removeTypingIndicator();
    appendMessage(
      "assistant",
      "❌ Cannot reach AskVineet API. Is the backend running?\n" +
        "Start it with: uvicorn app.main:app --reload",
    );
    setStatus("disconnected");
    console.error("AskVineet API error:", err);
  } finally {
    setWaiting(false);
    input.focus();
  }
}

// ── Keyboard shortcut ────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  $input().addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  $input().focus();
  setStatus(`session: ${sessionId.slice(0, 8)} · ready`);
});
